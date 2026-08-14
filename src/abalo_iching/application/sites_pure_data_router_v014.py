"""Offline-only pure-data Router outcome orchestration for Direct Reading V2."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, model_validator

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingOptionalContext,
    DirectReadingProviderFailure,
    DirectReadingPreparedRequest,
    DirectReadingProviderResult,
    DirectReadingRequest,
    DirectReadingUsage,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)


CONTRACT_VERSION = "DRV2_PURE_DATA_ROUTER_OUTCOME_V014_OFFLINE"
_FIXED_PROMPTS = {
    "SUBJECT": "你这次所问的主体具体是哪一个？",
    "DECISION_AXIS": "你希望比较的两个互斥选择分别是什么？",
    "JUDGMENT_OBJECT": "你这次希望判断的具体对象是哪一个？",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Ambiguity(StrictModel):
    kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"]
    description: str = Field(min_length=1, max_length=160)


class OfflineRequest(StrictModel):
    question_text: str
    numbers: list[int] = Field(min_length=3, max_length=3)
    optional_context: DirectReadingOptionalContext | None = None
    user_confirmed: StrictBool = False
    skip_router: StrictBool = False
    critical_ambiguity: Ambiguity | None = None


class RouterOutcome(StrictModel):
    status: Literal["PASS", "ASK_ONCE", "FAILED"]
    ambiguity_kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"] | None = None
    failure_code: Literal["UNAVAILABLE", "TIMEOUT", "INVALID_OUTPUT"] | None = None

    @model_validator(mode="after")
    def exact_shape(self) -> RouterOutcome:
        if self.status == "PASS" and (self.ambiguity_kind is not None or self.failure_code is not None):
            raise ValueError("PASS has no additional fields")
        if self.status == "ASK_ONCE" and (self.ambiguity_kind is None or self.failure_code is not None):
            raise ValueError("ASK_ONCE requires only ambiguity_kind")
        if self.status == "FAILED" and (self.failure_code is None or self.ambiguity_kind is not None):
            raise ValueError("FAILED requires only failure_code")
        return self


class FixtureProviderData(StrictModel):
    output_text: str
    api_status: str | None = "completed"
    incomplete_details: object | None = None
    response_id: str | None = "fixture-response"
    model: str = "gpt-5.6-sol"
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    failure_code: Literal["PROVIDER_UNAVAILABLE"] | None = None


class WaitingEnvelope(StrictModel):
    contract_version: Literal[CONTRACT_VERSION]
    status: Literal["WAITING_FOR_ONE_ANSWER"]
    request_payload: dict[str, Any]
    request_sha256: str
    original_question_text: str
    original_question_sha256: str
    ambiguity_kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"]
    clarification_prompt: str
    outcome_status: Literal["ASK_ONCE"]
    router_outcomes_consumed: Literal[1]
    router_callback_executions: Literal[0]
    router_cast_count: Literal[0]
    prepare_calls: Literal[0]
    deterministic_cast_count: Literal[0]
    provider_calls: Literal[0]
    high_attempts: Literal[0]
    high_status: None
    automatic_retries: Literal[0]
    deployment: Literal[False]
    production: Literal[False]
    default_replacement: Literal[False]


def _plain_json_copy(
    value: object,
    *,
    active_ids: set[int] | None = None,
    depth: int = 0,
) -> object:
    if depth > 20:
        raise ValueError("JSON tree is too deep")
    active = active_ids if active_ids is not None else set()
    kind = type(value)
    if value is None or kind in {str, bool, int, float}:
        return value
    if kind is list:
        identity = id(value)
        if identity in active:
            raise ValueError("cyclic JSON tree")
        active.add(identity)
        try:
            return [
                _plain_json_copy(item, active_ids=active, depth=depth + 1)
                for item in value  # type: ignore[union-attr]
            ]
        finally:
            active.remove(identity)
    if kind is dict:
        identity = id(value)
        if identity in active:
            raise ValueError("cyclic JSON tree")
        active.add(identity)
        copied: dict[str, object] = {}
        try:
            for key, item in dict.items(value):  # type: ignore[arg-type]
                if type(key) is not str:
                    raise ValueError("JSON object keys must be builtin strings")
                copied[key] = _plain_json_copy(
                    item, active_ids=active, depth=depth + 1
                )
            return copied
        finally:
            active.remove(identity)
    raise ValueError("value is not a plain JSON tree")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _request_models(request_payload: object) -> tuple[OfflineRequest, DirectReadingRequest, dict[str, Any]]:
    plain = _plain_json_copy(request_payload)
    if type(plain) is not dict:
        raise ValueError("request must be a plain JSON object")
    offline = OfflineRequest.model_validate(plain)
    direct = DirectReadingRequest.model_validate(
        {
            "question_text": offline.question_text,
            "numbers": offline.numbers,
            "optional_context": offline.optional_context,
        }
    )
    normalized = offline.model_dump(mode="json", exclude_none=True)
    return offline, direct, normalized


def _outcome(value: object) -> tuple[RouterOutcome | None, str | None, bool]:
    if value is None:
        return None, "OUTCOME_MISSING", False
    try:
        plain = _plain_json_copy(value)
        if type(plain) is not dict:
            raise ValueError("outcome must be object")
        round_trip = json.loads(_canonical(plain))
        return RouterOutcome.model_validate(round_trip), None, True
    except (ValidationError, ValueError, TypeError, OverflowError):
        return None, "INVALID_ROUTER_OUTCOME", False


class _FixtureProvider:
    def __init__(self, data: FixtureProviderData) -> None:
        self.data = data
        self.calls = 0

    def generate(self, **_: object) -> DirectReadingProviderResult:
        self.calls += 1
        if self.data.failure_code is not None:
            raise DirectReadingProviderFailure(self.data.failure_code)
        return DirectReadingProviderResult(
            output_text=self.data.output_text,
            api_status=self.data.api_status,
            incomplete_details=self.data.incomplete_details,
            response_id=self.data.response_id,
            model=self.data.model,
            usage=DirectReadingUsage(
                input_tokens=self.data.input_tokens,
                output_tokens=self.data.output_tokens,
                total_tokens=self.data.input_tokens + self.data.output_tokens,
            ),
            latency_ms=self.data.latency_ms,
        )


def _base(direct: DirectReadingRequest, normalized: dict[str, Any]) -> dict[str, Any]:
    question = direct.question_text
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "ROUTING",
        "original_question_text": question,
        "original_question_sha_before": _sha(question),
        "original_question_sha_after": _sha(question),
        "original_question_preserved": True,
        "request_sha256": _sha(_canonical(normalized)),
        "router_outcome_present": False,
        "router_outcome_status": None,
        "router_outcome_validation_code": None,
        "router_outcomes_consumed": 0,
        "router_callback_executions": 0,
        "router_cast_count": 0,
        "prepare_calls": 0,
        "deterministic_cast_count": 0,
        "provider_calls": 0,
        "high_attempts": 0,
        "high_status": None,
        "automatic_retries": 0,
        "high_response": None,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def _fixture_data(value: object) -> FixtureProviderData:
    plain = _plain_json_copy(value)
    if type(plain) is not dict:
        raise ValueError("fixture provider data must be object")
    return FixtureProviderData.model_validate(json.loads(_canonical(plain)))


def _run_high(
    result: dict[str, Any],
    direct: DirectReadingRequest,
    fixture_provider_result: object,
) -> dict[str, Any]:
    result["high_attempts"] = 1
    result["prepare_calls"] = 1
    try:
        prepared = prepare_direct_reading_v2_request(
            direct.model_dump(mode="json", exclude_none=True)
        )
    except Exception:
        result.update(
            {
                "status": "HIGH_COMPLETE",
                "high_status": "ENGINE_ERROR",
                "high_response": None,
            }
        )
        return result
    if not isinstance(prepared, DirectReadingPreparedRequest):
        result.update({"status": "HIGH_COMPLETE", "high_status": prepared.get("status"), "high_response": prepared})
        return result
    result["deterministic_cast_count"] = 1
    try:
        provider = _FixtureProvider(_fixture_data(fixture_provider_result))
    except (ValidationError, ValueError, TypeError, OverflowError):
        result.update({"status": "HIGH_COMPLETE", "high_status": "UNAVAILABLE", "high_response": None})
        return result
    response = process_prepared_direct_reading_v2_request(prepared, provider=provider)
    result.update(
        {
            "status": "HIGH_COMPLETE",
            "provider_calls": provider.calls,
            "high_status": response.get("status"),
            "high_response": response,
            "original_question_sha_after": _sha(direct.question_text),
            "original_question_preserved": result["original_question_text"] == direct.question_text,
        }
    )
    return result


def begin_pure_data_direct_reading(
    request_payload: object,
    *,
    router_outcome: object = None,
    fixture_provider_result: object = None,
) -> dict[str, Any]:
    try:
        offline, direct, normalized = _request_models(request_payload)
    except (ValidationError, ValueError, TypeError, OverflowError):
        return {
            "contract_version": CONTRACT_VERSION,
            "status": "INVALID_REQUEST",
            "router_callback_executions": 0,
            "router_cast_count": 0,
            "prepare_calls": 0,
            "deterministic_cast_count": 0,
            "provider_calls": 0,
            "high_attempts": 0,
            "automatic_retries": 0,
        }
    result = _base(direct, normalized)
    if offline.skip_router:
        result.update({"clarity_result": "SKIPPED", "route": "DIRECT_HIGH"})
        return _run_high(result, direct, fixture_provider_result)
    if offline.user_confirmed:
        result.update({"clarity_result": "CONFIRMED", "route": "DIRECT_HIGH"})
        return _run_high(result, direct, fixture_provider_result)
    if offline.critical_ambiguity is None:
        result.update({"clarity_result": "CLEAR", "route": "DIRECT_HIGH"})
        return _run_high(result, direct, fixture_provider_result)
    parsed, error, present = _outcome(router_outcome)
    result.update(
        {
            "clarity_result": "CRITICAL_AMBIGUITY",
            "route": "PURE_DATA_OUTCOME_THEN_HIGH",
            "router_outcome_present": router_outcome is not None,
            "router_outcome_validation_code": error,
            "router_outcomes_consumed": 1 if present else 0,
            "router_outcome_status": parsed.status if parsed else None,
        }
    )
    if parsed is None or parsed.status == "FAILED":
        if parsed is not None:
            result["router_outcome_validation_code"] = parsed.failure_code
        return _run_high(result, direct, fixture_provider_result)
    if parsed.status == "PASS":
        return _run_high(result, direct, fixture_provider_result)
    if parsed.ambiguity_kind != offline.critical_ambiguity.kind:
        result.update({"router_outcome_validation_code": "AMBIGUITY_KIND_MISMATCH", "router_outcomes_consumed": 0})
        return _run_high(result, direct, fixture_provider_result)
    return WaitingEnvelope(
        contract_version=CONTRACT_VERSION,
        status="WAITING_FOR_ONE_ANSWER",
        request_payload=normalized,
        request_sha256=result["request_sha256"],
        original_question_text=direct.question_text,
        original_question_sha256=result["original_question_sha_before"],
        ambiguity_kind=offline.critical_ambiguity.kind,
        clarification_prompt=_FIXED_PROMPTS[offline.critical_ambiguity.kind],
        outcome_status="ASK_ONCE",
        router_outcomes_consumed=1,
        router_callback_executions=0,
        router_cast_count=0,
        prepare_calls=0,
        deterministic_cast_count=0,
        provider_calls=0,
        high_attempts=0,
        high_status=None,
        automatic_retries=0,
        deployment=False,
        production=False,
        default_replacement=False,
    ).model_dump(mode="json")


def resume_pure_data_direct_reading(
    request_payload: object,
    waiting_payload: object,
    *,
    user_answer: object | None = None,
    skip_answer: bool = False,
    fixture_provider_result: object = None,
) -> dict[str, Any]:
    try:
        waiting_plain = _plain_json_copy(waiting_payload)
        if type(waiting_plain) is not dict:
            raise ValueError("waiting must be object")
        waiting = WaitingEnvelope.model_validate(json.loads(_canonical(waiting_plain)))
        offline, direct, normalized = _request_models(request_payload)
    except (ValidationError, ValueError, TypeError, OverflowError):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_RESUME", "high_attempts": 0}
    if (
        _sha(_canonical(normalized)) != waiting.request_sha256
        or waiting.request_payload != normalized
        or direct.question_text != waiting.original_question_text
        or _sha(direct.question_text) != waiting.original_question_sha256
        or offline.critical_ambiguity is None
        or offline.critical_ambiguity.kind != waiting.ambiguity_kind
        or waiting.clarification_prompt != _FIXED_PROMPTS[waiting.ambiguity_kind]
    ):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_RESUME", "high_attempts": 0}
    context = direct.optional_context
    if not skip_answer and type(user_answer) is str:
        answer = unicodedata.normalize("NFC", user_answer).strip()
        if answer and len(answer) <= 400 and not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in answer):
            note = f"[用户一次澄清原话] {answer}"
            existing = context.discernment_note if context else None
            merged = f"{existing}\n{note}" if existing else note
            if len(merged) <= 400:
                context = DirectReadingOptionalContext(
                    discernment_note=merged,
                    framed_question=context.framed_question if context else None,
                )
    direct = DirectReadingRequest(
        question_text=direct.question_text,
        numbers=direct.numbers,
        optional_context=context,
    )
    result = _base(direct, normalized)
    result.update(
        {
            "clarity_result": "CRITICAL_AMBIGUITY",
            "route": "PURE_DATA_OUTCOME_THEN_HIGH",
            "router_outcome_present": True,
            "router_outcome_status": "ASK_ONCE",
            "router_outcomes_consumed": 1,
        }
    )
    return _run_high(result, direct, fixture_provider_result)


__all__ = [
    "CONTRACT_VERSION",
    "RouterOutcome",
    "begin_pure_data_direct_reading",
    "resume_pure_data_direct_reading",
]
