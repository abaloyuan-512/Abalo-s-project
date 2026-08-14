"""Zero-live bridge from one OpenAI parsed response object to V017 telemetry."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from openai.types.responses.parsed_response import (
    ParsedResponse,
    ParsedResponseOutputMessage,
    ParsedResponseOutputText,
)
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)

from abalo_iching.application.sites_light_router_adapter_v015 import LightRouterRequest, ModelDecision
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import (
    make_atomic_fixture_response,
    process_atomic_fixture_receipt,
)


CONTRACT_VERSION = "DRV2_REAL_ADAPTER_RESPONSE_TO_V017_TELEMETRY_V018_OFFLINE"
SDK_RESPONSE_TYPE = ParsedResponse[ModelDecision]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _strict_request(value: object) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValueError("request must be a plain object")
    canonical = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    parsed = LightRouterRequest.model_validate(canonical)
    return parsed.model_dump(mode="json")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class _StampedSDKField:
    source_token: str
    value: object


class SDKResponseSnapshot:
    """One internally issued, immutable and one-shot SDK response snapshot."""

    __slots__ = ("_fields", "_source_token", "_consumed", "_extraction_error", "_sealed")

    def __init__(self, response: ParsedResponse[ModelDecision], *, extraction_error: bool = False) -> None:
        if type(response) is not SDK_RESPONSE_TYPE:
            raise ValueError("exact parsed SDK response required")
        token = uuid4().hex
        fields = {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage is not None else None,
            "decision": response.output_parsed.model_dump(mode="json", exclude_none=True)
            if type(response.output_parsed) is ModelDecision else None,
        }
        object.__setattr__(self, "_fields", tuple(
            (name, _StampedSDKField(token, value)) for name, value in fields.items()
        ))
        object.__setattr__(self, "_source_token", token)
        object.__setattr__(self, "_consumed", False)
        object.__setattr__(self, "_extraction_error", extraction_error)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("SDK snapshot is immutable")
        object.__setattr__(self, name, value)

    @classmethod
    def _mixed_for_adversary(
        cls, first: SDKResponseSnapshot, second: SDKResponseSnapshot, from_second: set[str]
    ) -> SDKResponseSnapshot:
        obj = object.__new__(cls)
        a, b = dict(first._fields), dict(second._fields)
        object.__setattr__(obj, "_fields", tuple(
            (name, b[name] if name in from_second else a[name]) for name in a
        ))
        object.__setattr__(obj, "_source_token", first._source_token)
        object.__setattr__(obj, "_consumed", False)
        object.__setattr__(obj, "_extraction_error", False)
        object.__setattr__(obj, "_sealed", True)
        return obj

    def extract_once(self) -> tuple[str, dict[str, object]]:
        if self._consumed:
            raise ValueError("SDK snapshot already consumed")
        object.__setattr__(self, "_consumed", True)
        if self._extraction_error:
            raise RuntimeError("fixture extraction failure")
        fields = dict(self._fields)
        tokens = {item.source_token for item in fields.values()}
        if tokens != {self._source_token}:
            raise ValueError("mixed SDK response sources")
        return self._source_token, {name: item.value for name, item in fields.items()}


def make_sdk_response_fixture(
    *,
    response_id: str | None,
    model: str = "gpt-5.6-luna-fixture",
    status: str = "completed",
    input_tokens: int | None = 100,
    output_tokens: int | None = 10,
    total_tokens: int | None = 110,
    decision: ModelDecision | None = None,
    extraction_error: bool = False,
) -> SDKResponseSnapshot:
    """Build an exact SDK-shaped response fixture; never creates an OpenAI client."""

    parsed = decision or ModelDecision(status="PASS")
    text = ParsedResponseOutputText(
        annotations=[], text="fixture-output-not-persisted", type="output_text", parsed=parsed
    )
    message = ParsedResponseOutputMessage(
        id="fixture-message", content=[text], role="assistant", status="completed", type="message"
    )
    usage = None
    if input_tokens is not None or output_tokens is not None or total_tokens is not None:
        usage = ResponseUsage.model_construct(
            input_tokens=input_tokens,
            input_tokens_details=InputTokensDetails.model_construct(
                cache_write_tokens=0, cached_tokens=0
            ),
            output_tokens=output_tokens,
            output_tokens_details=OutputTokensDetails.model_construct(reasoning_tokens=0),
            total_tokens=total_tokens,
        )
    response = SDK_RESPONSE_TYPE.model_construct(
        id=response_id,
        model=model,
        status=status,
        usage=usage,
        output=[message],
    )
    return SDKResponseSnapshot(response, extraction_error=extraction_error)


def mix_sdk_response_fixtures_for_test(
    first: SDKResponseSnapshot,
    second: SDKResponseSnapshot,
    *,
    from_second: set[str],
) -> SDKResponseSnapshot:
    """Adversarial helper: mix fields from two independently valid SDK fixtures."""

    if type(first) is not SDKResponseSnapshot or type(second) is not SDKResponseSnapshot:
        raise ValueError("exact SDK snapshots required")
    return SDKResponseSnapshot._mixed_for_adversary(first, second, from_second)


def bridge_sdk_response_to_v017(
    *, case_id: str, request_payload: object, sdk_response: object
) -> tuple[dict[str, str], dict[str, Any]]:
    """Atomically snapshot one exact SDK response and delegate all telemetry to V017."""

    bridge: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "terminal_status": "SDK_RESPONSE_REJECTED",
        "failure_code": "INVALID_SDK_RESPONSE",
        "sdk_response_extraction_attempts": 0,
        "sdk_response_consumed": False,
        "sdk_response_local_instance_sha256": None,
        "v017_receipt_attempts": 0,
        "integration_binding_sha256": None,
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "router_high_calls": 0,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
        "automatic_retries": 0,
        "v017_audit": None,
    }
    if type(sdk_response) is not SDKResponseSnapshot:
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, bridge
    try:
        validated_request = _strict_request(request_payload)
    except BaseException:
        bridge["terminal_status"] = "INVALID_REQUEST"
        bridge["failure_code"] = "INVALID_REQUEST"
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, bridge
    try:
        bridge["sdk_response_extraction_attempts"] = 1
        bridge["sdk_response_consumed"] = True
        token, fields = sdk_response.extract_once()
        bridge["sdk_response_local_instance_sha256"] = _sha(token)
        response_id = fields["id"]
        model = fields["model"]
        status = fields["status"]
        usage = fields["usage"]
        decision = fields["decision"]
        parsed_decision = ModelDecision.model_validate(decision) if type(decision) is dict else None
        payload = {
            "response_id": response_id,
            "model": model,
            "provider_status": status,
            "usage": {
                "input_tokens": usage.get("input_tokens") if type(usage) is dict else None,
                "output_tokens": usage.get("output_tokens") if type(usage) is dict else None,
                "total_tokens": usage.get("total_tokens") if type(usage) is dict else None,
            },
            "decision": parsed_decision.model_dump(mode="json", exclude_none=True)
            if parsed_decision is not None else None,
        }
        atomic = make_atomic_fixture_response(payload)
        bridge["v017_receipt_attempts"] = 1
        outcome, v017 = process_atomic_fixture_receipt(
            case_id=case_id, request_payload=validated_request, response=atomic
        )
        bridge["v017_audit"] = v017
        if v017["terminal_status"] == "RECEIPT_COMPLETE":
            bridge["integration_binding_sha256"] = _sha(_canonical({
                "schema_version": "DRV2_SDK_TO_V017_INTEGRATION_BINDING_V1",
                "sdk_response_local_instance_sha256": bridge["sdk_response_local_instance_sha256"],
                "request_binding_sha256": v017["request_binding_sha256"],
                "receipt_projection_sha256": v017["raw_receipt_sha256"],
            }))
            bridge["terminal_status"] = "TELEMETRY_COMPLETE"
            bridge["failure_code"] = None
        else:
            bridge["terminal_status"] = "TELEMETRY_INCOMPLETE"
            bridge["failure_code"] = "INVALID_SDK_RESPONSE"
        return outcome, bridge
    except BaseException:
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, bridge


def rebuild_integration_binding_sha256(bridge: dict[str, Any]) -> str:
    v017 = bridge["v017_audit"]
    if type(v017) is not dict or not v017.get("raw_receipt_sha256"):
        raise ValueError("complete V017 receipt required")
    return _sha(_canonical({
        "schema_version": "DRV2_SDK_TO_V017_INTEGRATION_BINDING_V1",
        "sdk_response_local_instance_sha256": bridge["sdk_response_local_instance_sha256"],
        "request_binding_sha256": v017["request_binding_sha256"],
        "receipt_projection_sha256": v017["raw_receipt_sha256"],
    }))


__all__ = [
    "bridge_sdk_response_to_v017",
    "make_sdk_response_fixture",
    "mix_sdk_response_fixtures_for_test",
    "rebuild_integration_binding_sha256",
]
