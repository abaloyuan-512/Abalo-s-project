"""Receipt provenance for a future light-Router call; fixture-only in V016.

This module does not repair or reinterpret the V015 live ledger.  It defines a
strict, non-sensitive projection that a future call can extract atomically from
one Responses API object: response ID, provider model/status, usage, and the
structured decision digest.  Full response bodies and prompts are never stored.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_UP
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, field_validator, model_validator

from abalo_iching.application.sites_light_router_adapter_v015 import LightRouterRequest


CONTRACT_VERSION = "DRV2_LIGHT_ROUTER_RECEIPT_PROVENANCE_V016_OFFLINE"
RECEIPT_PROJECTION_VERSION = "DRV2_LIGHT_ROUTER_RECEIPT_PROJECTION_V1"
RATE_SNAPSHOT = {
    "version": "V016_INTERNAL_CONSERVATIVE_RATE_V1",
    "input_usd_per_million": "1.00",
    "output_usd_per_million": "6.00",
    "source": "INTERNAL_CONSERVATIVE_ESTIMATE_NOT_API_INVOICE",
    "rounding": "ROUND_UP",
    "precision_usd": "0.000000000001",
}
RATE_SNAPSHOT_SHA256 = hashlib.sha256(
    json.dumps(RATE_SNAPSHOT, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest().upper()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ReceiptUsage(StrictModel):
    input_tokens: StrictInt = Field(ge=0)
    output_tokens: StrictInt = Field(ge=0)
    total_tokens: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def exact_total(self) -> ReceiptUsage:
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("usage total must equal input plus output")
        return self


class ReceiptDecision(StrictModel):
    status: Literal["PASS", "ASK_ONCE"]
    ambiguity_kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"] | None = None

    @model_validator(mode="after")
    def exact_shape(self) -> ReceiptDecision:
        if self.status == "PASS" and self.ambiguity_kind is not None:
            raise ValueError("PASS cannot carry ambiguity_kind")
        if self.status == "ASK_ONCE" and self.ambiguity_kind is None:
            raise ValueError("ASK_ONCE requires ambiguity_kind")
        return self


class ProviderReceipt(StrictModel):
    response_id: str = Field(min_length=1, max_length=160)
    model: str = Field(min_length=1, max_length=120)
    provider_status: Literal["completed"]
    usage: ReceiptUsage
    decision: ReceiptDecision

    @field_validator("response_id", "model")
    @classmethod
    def no_control_characters(cls, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("receipt identifiers contain control characters")
        return value


class ReceiptAudit(StrictModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    terminal_status: Literal["RECEIPT_COMPLETE", "RECEIPT_INCOMPLETE", "INVALID_REQUEST"]
    failure_code: Literal["INVALID_REQUEST", "RECEIPT_INCOMPLETE", "TRANSPORT_ERROR"] | None
    question_sha_before: str | None
    question_sha_sent: str | None
    question_sha_after: str | None
    original_question_preserved: bool
    provider_kind: Literal["FIXTURE"]
    provider_attempts: Literal[0, 1]
    fixture_transport_calls: Literal[0, 1]
    receipt_observed: bool
    response_id: str | None
    provider_model: str | None
    provider_status: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    raw_decision_payload_sha256: str | None
    normalized_decision_sha256: str | None
    normalized_decision_status: Literal["PASS", "ASK_ONCE"] | None
    normalized_ambiguity_kind: Literal["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"] | None
    raw_receipt_sha256: str | None
    receipt_projection_version: Literal[RECEIPT_PROJECTION_VERSION]
    canonical_round_trip: bool
    actual_cost_estimate_usd: str | None
    cost_estimate_mode: Literal["ALL_INPUT_UNCACHED", "UNAVAILABLE"]
    input_usd_per_million: str | None
    output_usd_per_million: str | None
    rate_snapshot_sha256: str | None
    rate_source: str | None
    cost_rounding: str | None
    cost_precision_usd: str | None
    router_live_calls: Literal[0] = 0
    real_provider_instantiated: Literal[False] = False
    router_prepare_calls: Literal[0] = 0
    router_cast_count: Literal[0] = 0
    router_process_calls: Literal[0] = 0
    router_high_calls: Literal[0] = 0
    automatic_retries: Literal[0] = 0
    deployment: Literal[False] = False
    production: Literal[False] = False
    default_replacement: Literal[False] = False


class FixtureSDKResponse:
    """Exact immutable SDK-shaped response returned by one fixture transport."""

    __slots__ = ("_payload_bytes", "_consumed")

    def __init__(self, payload: dict[str, object], *, identity: str) -> None:
        copied = _plain_copy(payload)
        if type(copied) is not dict or type(identity) is not str or not identity:
            raise ValueError("invalid fixture SDK response")
        envelope = {"identity": identity, "payload": copied}
        self._payload_bytes = _canonical(envelope).encode("utf-8")
        self._consumed = False

    def extract_once(self) -> dict[str, object]:
        if self._consumed:
            raise RuntimeError("fixture SDK response already consumed")
        self._consumed = True
        envelope = json.loads(self._payload_bytes.decode("utf-8"))
        return envelope["payload"]


class _FixtureTransport:
    def __init__(self, response: FixtureSDKResponse | None, *, fail: bool) -> None:
        self._response = response
        self._fail = fail
        self.calls = 0

    def fetch(self) -> FixtureSDKResponse:
        self.calls += 1
        if self._fail or self._response is None:
            raise RuntimeError("fixture transport failure detail must not escape")
        return self._response


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _plain_copy(value: object, *, active: set[int] | None = None, depth: int = 0) -> object:
    if depth > 20:
        raise ValueError("JSON tree is too deep")
    seen = active if active is not None else set()
    kind = type(value)
    if value is None or kind in {str, bool, int}:
        return value
    if kind is float:
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("non-finite number")
        return value
    if kind is list:
        identity = id(value)
        if identity in seen:
            raise ValueError("cyclic JSON tree")
        seen.add(identity)
        try:
            return [_plain_copy(item, active=seen, depth=depth + 1) for item in value]  # type: ignore[union-attr]
        finally:
            seen.remove(identity)
    if kind is dict:
        identity = id(value)
        if identity in seen:
            raise ValueError("cyclic JSON tree")
        seen.add(identity)
        copied: dict[str, object] = {}
        try:
            for key, item in dict.items(value):  # type: ignore[arg-type]
                if type(key) is not str:
                    raise ValueError("JSON keys must be builtin strings")
                copied[key] = _plain_copy(item, active=seen, depth=depth + 1)
            return copied
        finally:
            seen.remove(identity)
    raise ValueError("not a plain JSON tree")


def _strict_request(value: object) -> LightRouterRequest:
    plain = _plain_copy(value)
    if type(plain) is not dict:
        raise ValueError("request must be plain object")
    return LightRouterRequest.model_validate(json.loads(_canonical(plain)))


def estimate_usage_cost_usd(
    usage: ReceiptUsage,
    *,
    input_usd_per_million: Decimal,
    output_usd_per_million: Decimal,
) -> str:
    if input_usd_per_million < 0 or output_usd_per_million < 0:
        raise ValueError("rates must be non-negative")
    cost = (
        Decimal(usage.input_tokens) * input_usd_per_million
        + Decimal(usage.output_tokens) * output_usd_per_million
    ) / Decimal(1_000_000)
    return str(cost.quantize(Decimal("0.000000000001"), rounding=ROUND_UP))


def _empty_audit(
    *,
    terminal_status: Literal["RECEIPT_INCOMPLETE", "INVALID_REQUEST"],
    failure_code: Literal["INVALID_REQUEST", "RECEIPT_INCOMPLETE", "TRANSPORT_ERROR"],
    question_sha: str | None,
    attempted: bool,
) -> ReceiptAudit:
    return ReceiptAudit(
        terminal_status=terminal_status,
        failure_code=failure_code,
        question_sha_before=question_sha,
        question_sha_sent=question_sha if attempted else None,
        question_sha_after=question_sha,
        original_question_preserved=question_sha is not None,
        provider_kind="FIXTURE",
        provider_attempts=1 if attempted else 0,
        fixture_transport_calls=1 if attempted else 0,
        receipt_observed=False,
        response_id=None,
        provider_model=None,
        provider_status=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        raw_decision_payload_sha256=None,
        normalized_decision_sha256=None,
        normalized_decision_status=None,
        normalized_ambiguity_kind=None,
        raw_receipt_sha256=None,
        receipt_projection_version=RECEIPT_PROJECTION_VERSION,
        canonical_round_trip=False,
        actual_cost_estimate_usd=None,
        cost_estimate_mode="UNAVAILABLE",
        input_usd_per_million=None,
        output_usd_per_million=None,
        rate_snapshot_sha256=None,
        rate_source=None,
        cost_rounding=None,
        cost_precision_usd=None,
    )


def make_fixture_sdk_response(payload: object, *, identity: str) -> FixtureSDKResponse:
    plain = _plain_copy(payload)
    if type(plain) is not dict:
        raise ValueError("fixture receipt must be plain object")
    return FixtureSDKResponse(plain, identity=identity)


def process_fixture_receipt(
    request_payload: object,
    fixture_response: object,
    *,
    transport_error: bool = False,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate one atomic fixture receipt and return outcome plus safe audit."""

    try:
        request = _strict_request(request_payload)
    except (ValidationError, ValueError, TypeError, OverflowError):
        audit = _empty_audit(
            terminal_status="INVALID_REQUEST",
            failure_code="INVALID_REQUEST",
            question_sha=None,
            attempted=False,
        )
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, audit.model_dump(mode="json")
    question_sha = _sha(request.original_question)
    if fixture_response is not None and type(fixture_response) is not FixtureSDKResponse:
        audit = _empty_audit(
            terminal_status="RECEIPT_INCOMPLETE",
            failure_code="RECEIPT_INCOMPLETE",
            question_sha=question_sha,
            attempted=False,
        )
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, audit.model_dump(mode="json")
    transport = _FixtureTransport(fixture_response, fail=transport_error)
    try:
        sdk_response = transport.fetch()
    except BaseException:
        audit = _empty_audit(
            terminal_status="RECEIPT_INCOMPLETE",
            failure_code="TRANSPORT_ERROR",
            question_sha=question_sha,
            attempted=transport.calls == 1,
        )
        return {"status": "FAILED", "failure_code": "UNAVAILABLE"}, audit.model_dump(mode="json")
    try:
        plain = _plain_copy(sdk_response.extract_once())
        if type(plain) is not dict:
            raise ValueError("receipt must be plain object")
        canonical_receipt_input = json.loads(_canonical(plain))
        parsed = ProviderReceipt.model_validate(canonical_receipt_input)
        if parsed.decision.status == "ASK_ONCE" and parsed.decision.ambiguity_kind != request.critical_ambiguity.kind:
            raise ValueError("ambiguity kind mismatch")
        raw_decision = canonical_receipt_input["decision"]
        raw_decision_sha = _sha(_canonical(raw_decision))
        outcome = parsed.decision.model_dump(mode="json", exclude_none=True)
        normalized_decision_sha = _sha(_canonical(outcome))
        projection = {
            "schema_version": RECEIPT_PROJECTION_VERSION,
            "response_id": parsed.response_id,
            "model": parsed.model,
            "provider_status": parsed.provider_status,
            "usage": parsed.usage.model_dump(mode="json"),
            "raw_decision_payload_sha256": raw_decision_sha,
            "decision": outcome,
        }
        projection_round_trip = json.loads(_canonical(projection))
        receipt_sha = _sha(_canonical(projection_round_trip))
        cost = estimate_usage_cost_usd(
            parsed.usage,
            input_usd_per_million=Decimal(RATE_SNAPSHOT["input_usd_per_million"]),
            output_usd_per_million=Decimal(RATE_SNAPSHOT["output_usd_per_million"]),
        )
        audit = ReceiptAudit(
            terminal_status="RECEIPT_COMPLETE",
            failure_code=None,
            question_sha_before=question_sha,
            question_sha_sent=question_sha,
            question_sha_after=question_sha,
            original_question_preserved=True,
            provider_kind="FIXTURE",
            provider_attempts=transport.calls,
            fixture_transport_calls=transport.calls,
            receipt_observed=True,
            response_id=parsed.response_id,
            provider_model=parsed.model,
            provider_status=parsed.provider_status,
            input_tokens=parsed.usage.input_tokens,
            output_tokens=parsed.usage.output_tokens,
            total_tokens=parsed.usage.total_tokens,
            raw_decision_payload_sha256=raw_decision_sha,
            normalized_decision_sha256=normalized_decision_sha,
            normalized_decision_status=parsed.decision.status,
            normalized_ambiguity_kind=parsed.decision.ambiguity_kind,
            raw_receipt_sha256=receipt_sha,
            receipt_projection_version=RECEIPT_PROJECTION_VERSION,
            canonical_round_trip=projection_round_trip == projection,
            actual_cost_estimate_usd=cost,
            cost_estimate_mode="ALL_INPUT_UNCACHED",
            input_usd_per_million=RATE_SNAPSHOT["input_usd_per_million"],
            output_usd_per_million=RATE_SNAPSHOT["output_usd_per_million"],
            rate_snapshot_sha256=RATE_SNAPSHOT_SHA256,
            rate_source=RATE_SNAPSHOT["source"],
            cost_rounding=RATE_SNAPSHOT["rounding"],
            cost_precision_usd=RATE_SNAPSHOT["precision_usd"],
        )
        return json.loads(_canonical(outcome)), audit.model_dump(mode="json")
    except (ValidationError, ValueError, TypeError, OverflowError, json.JSONDecodeError):
        audit = _empty_audit(
            terminal_status="RECEIPT_INCOMPLETE",
            failure_code="RECEIPT_INCOMPLETE",
            question_sha=question_sha,
            attempted=True,
        )
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, audit.model_dump(mode="json")


def rebuild_receipt_projection_sha256(audit_payload: object) -> str:
    plain = _plain_copy(audit_payload)
    if type(plain) is not dict:
        raise ValueError("audit must be plain object")
    required = (
        "response_id",
        "provider_model",
        "provider_status",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "raw_decision_payload_sha256",
        "normalized_decision_sha256",
        "normalized_decision_status",
    )
    if any(plain.get(field) is None for field in required):
        raise ValueError("audit is not a complete receipt")
    projection = {
        "schema_version": RECEIPT_PROJECTION_VERSION,
        "response_id": plain["response_id"],
        "model": plain["provider_model"],
        "provider_status": plain["provider_status"],
        "usage": {
            "input_tokens": plain["input_tokens"],
            "output_tokens": plain["output_tokens"],
            "total_tokens": plain["total_tokens"],
        },
        "raw_decision_payload_sha256": plain["raw_decision_payload_sha256"],
        "decision": {
            "status": plain["normalized_decision_status"],
            **(
                {"ambiguity_kind": plain["normalized_ambiguity_kind"]}
                if plain.get("normalized_ambiguity_kind") is not None
                else {}
            ),
        },
    }
    if _sha(_canonical(projection["decision"])) != plain["normalized_decision_sha256"]:
        raise ValueError("normalized decision digest mismatch")
    return _sha(_canonical(projection))


def rebuild_cost_estimate_usd(audit_payload: object) -> str:
    plain = _plain_copy(audit_payload)
    if type(plain) is not dict:
        raise ValueError("audit must be plain object")
    if plain.get("rate_snapshot_sha256") != RATE_SNAPSHOT_SHA256:
        raise ValueError("rate snapshot mismatch")
    if any(
        plain.get(field) != RATE_SNAPSHOT[key]
        for field, key in (
            ("input_usd_per_million", "input_usd_per_million"),
            ("output_usd_per_million", "output_usd_per_million"),
            ("rate_source", "source"),
            ("cost_rounding", "rounding"),
            ("cost_precision_usd", "precision_usd"),
        )
    ):
        raise ValueError("rate metadata mismatch")
    usage = ReceiptUsage(
        input_tokens=plain["input_tokens"],
        output_tokens=plain["output_tokens"],
        total_tokens=plain["total_tokens"],
    )
    return estimate_usage_cost_usd(
        usage,
        input_usd_per_million=Decimal(RATE_SNAPSHOT["input_usd_per_million"]),
        output_usd_per_million=Decimal(RATE_SNAPSHOT["output_usd_per_million"]),
    )


__all__ = [
    "CONTRACT_VERSION",
    "RECEIPT_PROJECTION_VERSION",
    "RATE_SNAPSHOT",
    "RATE_SNAPSHOT_SHA256",
    "ReceiptUsage",
    "estimate_usage_cost_usd",
    "make_fixture_sdk_response",
    "process_fixture_receipt",
    "rebuild_cost_estimate_usd",
    "rebuild_receipt_projection_sha256",
]
