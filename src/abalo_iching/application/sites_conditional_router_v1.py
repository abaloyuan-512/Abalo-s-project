"""Isolated, fail-open conditional Router for Direct Reading V2.

The Router is not a generation prerequisite and never receives casting
numbers or chart facts.  A caller must supply one concrete critical ambiguity;
otherwise the original question goes directly to the frozen high service.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Callable
from typing import Any, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
)

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingOptionalContext,
    DirectReadingRequest,
)


CONTRACT_VERSION = "DRV2_CONDITIONAL_ROUTER_OFFLINE_V1"
_FORBIDDEN_ROUTER_FIELDS = {
    "question_text",
    "framed_question",
    "numbers",
    "chart",
    "chart_facts",
    "reading",
    "judgment",
    "facts",
    "optional_context",
}
_CLARIFICATION_PROMPTS = {
    "SUBJECT": "你这次所问的主体具体是哪一个？",
    "DECISION_AXIS": "你希望比较的两个互斥选择分别是什么？",
    "JUDGMENT_OBJECT": "你这次希望判断的具体对象是哪一个？",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _normalized_bounded_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} length is out of range")
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in normalized):
        raise ValueError(f"{field} contains unsafe characters")
    return normalized


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


class CriticalAmbiguity(StrictModel):
    kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"]
    description: str = Field(max_length=160)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: object) -> str:
        return _normalized_bounded_text(value, field="critical_ambiguity", maximum=160)


class ConditionalRouterRequest(StrictModel):
    question_text: str
    numbers: tuple[StrictInt, StrictInt, StrictInt]
    optional_context: DirectReadingOptionalContext | None = None
    user_confirmed: StrictBool = False
    skip_router: StrictBool = False
    critical_ambiguity: CriticalAmbiguity | None = None


class LightRouterDecision(StrictModel):
    action: Literal["PASS", "ASK_ONCE"]


class OfflineRouterReceipt(StrictModel):
    """Fixture-only proof returned by an offline Router double."""

    provider_kind: Literal["FIXTURE"]
    real_provider_instantiated: Literal[False]
    decision: object


class OfflineHighReceipt(StrictModel):
    """Fixture-only proof returned by an offline fixed-high double."""

    provider_kind: Literal["FIXTURE"]
    real_provider_instantiated: Literal[False]
    cast_count: Literal[1]
    response: dict[str, Any]


class LightRouter(Protocol):
    def route(
        self,
        *,
        original_question: str,
        critical_ambiguity_kind: str,
        critical_ambiguity_description: str,
    ) -> object: ...


HighInvoker = Callable[[dict[str, Any]], object]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _high_payload(request: DirectReadingRequest) -> dict[str, Any]:
    return request.model_dump(mode="json", exclude_none=True)


def _high_payload_sha(request: DirectReadingRequest) -> str:
    return _sha_text(_canonical_json(_high_payload(request)))


def _base_result(
    *,
    request: DirectReadingRequest,
    routing_request_sha256: str,
    route: Literal["DIRECT_HIGH", "LIGHT_ROUTER_THEN_HIGH"],
    clarity_result: Literal["CONFIRMED", "SKIPPED", "CLEAR", "CRITICAL_AMBIGUITY"],
    clarity_reason: str,
) -> dict[str, Any]:
    original = request.question_text
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "ROUTING",
        "route": route,
        "original_question_text": original,
        "original_question_sha_before": _sha_text(original),
        "original_question_sha_after": _sha_text(original),
        "original_question_preserved": True,
        "high_payload_sha256": _high_payload_sha(request),
        "routing_request_sha256": routing_request_sha256,
        "clarity_result": clarity_result,
        "clarity_reason": clarity_reason,
        "input_user_confirmed": False,
        "input_skip_router": False,
        "critical_ambiguity_present": clarity_result == "CRITICAL_AMBIGUITY",
        "router_attempts": 0,
        "router_status": "NOT_ATTEMPTED",
        "router_failure_code": None,
        "clarification_prompt": None,
        "high_attempts": 0,
        "high_status": None,
        "cast_count": None,
        "automatic_retries": 0,
        "optional_context_applied": request.optional_context is not None,
        "high_response": None,
        "router_provider_kind": None,
        "router_real_provider_instantiated": None,
        "high_provider_kind": None,
        "high_real_provider_instantiated": None,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def _invoke_high(
    result: dict[str, Any],
    request: DirectReadingRequest,
    high_invoker: HighInvoker,
    *,
    answer_context: str | None = None,
) -> dict[str, Any]:
    optional_context = request.optional_context
    if answer_context is not None:
        answer_note = f"[用户一次澄清原话] {answer_context}"
        existing_note = optional_context.discernment_note if optional_context is not None else None
        merged_note = f"{existing_note}\n{answer_note}" if existing_note else answer_note
        if len(merged_note) <= 400:
            optional_context = DirectReadingOptionalContext(
                discernment_note=merged_note,
                framed_question=(optional_context.framed_question if optional_context else None),
            )
        result["user_answer_context_applied"] = len(merged_note) <= 400
    payload: dict[str, Any] = {
        "question_text": request.question_text,
        "numbers": list(request.numbers),
    }
    if optional_context is not None:
        payload["optional_context"] = optional_context.model_dump(mode="json", exclude_none=True)
    result["high_attempts"] = 1
    try:
        receipt = OfflineHighReceipt.model_validate(high_invoker(payload))
        high_response = receipt.response
        result["cast_count"] = receipt.cast_count
        result["high_provider_kind"] = receipt.provider_kind
        result["high_real_provider_instantiated"] = receipt.real_provider_instantiated
    except Exception:
        high_response = {
            "status": "UNAVAILABLE",
            "direct_reading": None,
            "error_code": "HIGH_UNAVAILABLE",
            "retryable": False,
        }
    high_status = str(high_response.get("status", "UNAVAILABLE"))
    result.update(
        {
            "status": "HIGH_COMPLETE",
            "high_status": high_status,
            "high_response": high_response,
            "optional_context_applied": optional_context is not None,
            "original_question_sha_after": _sha_text(request.question_text),
            "original_question_preserved": (
                result["original_question_text"] == request.question_text
                and result["original_question_sha_before"] == _sha_text(request.question_text)
            ),
        }
    )
    return result


def _router_decision(value: object) -> tuple[LightRouterDecision | None, str | None, OfflineRouterReceipt | None]:
    if value is None or value == "":
        return None, "ROUTER_EMPTY", None
    try:
        receipt = OfflineRouterReceipt.model_validate(value)
    except (ValidationError, ValueError, TypeError):
        return None, "ROUTER_RECEIPT_INVALID", None
    if receipt.decision is None or receipt.decision == "":
        return None, "ROUTER_EMPTY", receipt
    if isinstance(receipt.decision, dict) and _FORBIDDEN_ROUTER_FIELDS.intersection(receipt.decision):
        return None, "ROUTER_FORBIDDEN_FIELD", receipt
    try:
        decision = LightRouterDecision.model_validate(receipt.decision)
    except (ValidationError, ValueError, TypeError):
        return None, "ROUTER_SCHEMA_INVALID", receipt
    return decision, None, receipt


def begin_conditional_direct_reading(
    request_payload: object,
    *,
    high_invoker: HighInvoker,
    router: LightRouter | None = None,
) -> dict[str, Any]:
    """Route once or invoke high directly; never cast before the high call."""
    try:
        conditional = ConditionalRouterRequest.model_validate(request_payload)
        request = DirectReadingRequest.model_validate(
            {
                "question_text": conditional.question_text,
                "numbers": conditional.numbers,
                "optional_context": conditional.optional_context,
            }
        )
    except (ValidationError, ValueError, TypeError):
        return {
            "contract_version": CONTRACT_VERSION,
            "status": "INVALID_REQUEST",
            "router_attempts": 0,
            "high_attempts": 0,
            "cast_count": None,
            "automatic_retries": 0,
            "deployment": False,
            "production": False,
            "default_replacement": False,
        }
    routing_request_sha256 = _sha_text(
        _canonical_json(conditional.model_dump(mode="json", exclude_none=True))
    )

    if conditional.skip_router:
        result = _base_result(
            request=request,
            routing_request_sha256=routing_request_sha256,
            route="DIRECT_HIGH",
            clarity_result="SKIPPED",
            clarity_reason="USER_SKIPPED_ROUTER",
        )
        result["input_skip_router"] = True
        return _invoke_high(result, request, high_invoker)
    if conditional.user_confirmed:
        result = _base_result(
            request=request,
            routing_request_sha256=routing_request_sha256,
            route="DIRECT_HIGH",
            clarity_result="CONFIRMED",
            clarity_reason="USER_CONFIRMED_ORIGINAL_QUESTION",
        )
        result["input_user_confirmed"] = True
        return _invoke_high(result, request, high_invoker)
    if conditional.critical_ambiguity is None:
        result = _base_result(
            request=request,
            routing_request_sha256=routing_request_sha256,
            route="DIRECT_HIGH",
            clarity_result="CLEAR",
            clarity_reason="NO_PREEXISTING_CRITICAL_AMBIGUITY",
        )
        return _invoke_high(result, request, high_invoker)

    result = _base_result(
        request=request,
        routing_request_sha256=routing_request_sha256,
        route="LIGHT_ROUTER_THEN_HIGH",
        clarity_result="CRITICAL_AMBIGUITY",
        clarity_reason="PREEXISTING_CRITICAL_AMBIGUITY_SIGNAL",
    )
    if router is None:
        result.update({"router_status": "FAILED_OPEN", "router_failure_code": "ROUTER_UNAVAILABLE"})
        return _invoke_high(result, request, high_invoker)
    result["router_attempts"] = 1
    try:
        raw_decision = router.route(
            original_question=request.question_text,
            critical_ambiguity_kind=conditional.critical_ambiguity.kind,
            critical_ambiguity_description=conditional.critical_ambiguity.description,
        )
    except Exception:
        result.update({"router_status": "FAILED_OPEN", "router_failure_code": "ROUTER_UNAVAILABLE"})
        return _invoke_high(result, request, high_invoker)
    decision, failure_code, receipt = _router_decision(raw_decision)
    if receipt is not None:
        result["router_provider_kind"] = receipt.provider_kind
        result["router_real_provider_instantiated"] = receipt.real_provider_instantiated
    if decision is None:
        result.update({"router_status": "FAILED_OPEN", "router_failure_code": failure_code})
        return _invoke_high(result, request, high_invoker)
    if decision.action == "PASS":
        result["router_status"] = "PASSED"
        return _invoke_high(result, request, high_invoker)
    result.update(
        {
            "status": "WAITING_FOR_ONE_ANSWER",
            "router_status": "ASKED_ONCE",
            "clarification_prompt": _CLARIFICATION_PROMPTS[conditional.critical_ambiguity.kind],
        }
    )
    return result


class WaitingEnvelope(StrictModel):
    contract_version: Literal[CONTRACT_VERSION]
    status: Literal["WAITING_FOR_ONE_ANSWER"]
    route: Literal["LIGHT_ROUTER_THEN_HIGH"]
    original_question_text: str
    original_question_sha_before: str
    original_question_sha_after: str
    original_question_preserved: Literal[True]
    high_payload_sha256: str
    routing_request_sha256: str
    clarity_result: Literal["CRITICAL_AMBIGUITY"]
    clarity_reason: Literal["PREEXISTING_CRITICAL_AMBIGUITY_SIGNAL"]
    input_user_confirmed: Literal[False]
    input_skip_router: Literal[False]
    critical_ambiguity_present: Literal[True]
    router_attempts: Literal[1]
    router_status: Literal["ASKED_ONCE"]
    router_failure_code: None
    clarification_prompt: Literal[
        "你这次所问的主体具体是哪一个？",
        "你希望比较的两个互斥选择分别是什么？",
        "你这次希望判断的具体对象是哪一个？",
    ]
    high_attempts: Literal[0]
    high_status: None
    cast_count: None
    automatic_retries: Literal[0]
    optional_context_applied: StrictBool
    high_response: None
    router_provider_kind: Literal["FIXTURE"]
    router_real_provider_instantiated: Literal[False]
    high_provider_kind: None
    high_real_provider_instantiated: None
    deployment: Literal[False]
    production: Literal[False]
    default_replacement: Literal[False]


def resume_conditional_direct_reading(
    request_payload: object,
    waiting_result: object,
    *,
    high_invoker: HighInvoker,
    user_answer: object | None = None,
    skip_answer: bool = False,
) -> dict[str, Any]:
    """Resume one ASK_ONCE result without permitting another Router attempt."""
    try:
        conditional = ConditionalRouterRequest.model_validate(request_payload)
        request = DirectReadingRequest.model_validate(
            {
                "question_text": conditional.question_text,
                "numbers": conditional.numbers,
                "optional_context": conditional.optional_context,
            }
        )
    except (ValidationError, ValueError, TypeError):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_REQUEST"}
    routing_request_sha256 = _sha_text(
        _canonical_json(conditional.model_dump(mode="json", exclude_none=True))
    )
    try:
        waiting = WaitingEnvelope.model_validate(waiting_result)
    except (ValidationError, ValueError, TypeError):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_RESUME"}
    expected_sha = _sha_text(request.question_text)
    if (
        waiting.original_question_sha_before != expected_sha
        or waiting.original_question_sha_after != expected_sha
        or waiting.original_question_text != request.question_text
        or waiting.high_payload_sha256 != _high_payload_sha(request)
        or waiting.routing_request_sha256 != routing_request_sha256
    ):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_RESUME"}
    answer_context = None
    if not skip_answer and user_answer is not None:
        try:
            answer_context = _normalized_bounded_text(
                user_answer, field="user_answer", maximum=400
            )
        except ValueError:
            answer_context = None
    result = waiting.model_dump(mode="json")
    result["clarification_prompt"] = None
    result["resume_mode"] = "USER_ANSWER" if answer_context is not None else "SKIP_OR_INVALID_ANSWER"
    return _invoke_high(result, request, high_invoker, answer_context=answer_context)


__all__ = [
    "CONTRACT_VERSION",
    "ConditionalRouterRequest",
    "CriticalAmbiguity",
    "LightRouterDecision",
    "OfflineHighReceipt",
    "OfflineRouterReceipt",
    "LightRouter",
    "begin_conditional_direct_reading",
    "resume_conditional_direct_reading",
]
