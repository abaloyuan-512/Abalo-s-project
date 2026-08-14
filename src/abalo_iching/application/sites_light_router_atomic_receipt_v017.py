"""Atomic fixture receipt provenance repair for V017; zero-live only."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from abalo_iching.application.sites_light_router_adapter_v015 import LightRouterRequest
from abalo_iching.application.sites_light_router_receipt_v016 import (
    RATE_SNAPSHOT,
    RATE_SNAPSHOT_SHA256,
    ProviderReceipt,
    estimate_usage_cost_usd,
)


CONTRACT_VERSION = "DRV2_LIGHT_ROUTER_ATOMIC_RECEIPT_V017_OFFLINE"
RECEIPT_PROJECTION_VERSION = "DRV2_LIGHT_ROUTER_ATOMIC_RECEIPT_PROJECTION_V1"


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


def _plain(value: object, depth: int = 0) -> object:
    if depth > 20:
        raise ValueError("too deep")
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return value
    if type(value) is list:
        return [_plain(x, depth + 1) for x in value]
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise ValueError("bad key")
        return {k: _plain(v, depth + 1) for k, v in dict.items(value)}
    raise ValueError("not plain")


@dataclass(frozen=True)
class _Stamped:
    token: str
    value_json: str


class _FixtureTransportError(RuntimeError):
    pass


class AtomicFixtureResponse:
    """One immutable, one-shot fixture response issued by the fixture transport."""

    __slots__ = ("_fields", "_token", "_consumed", "_binding", "_sealed", "_fail_on_extract")

    def __init__(self, payload: object, *, _fail_on_extract: bool = False) -> None:
        plain = _plain(payload)
        if type(plain) is not dict:
            raise ValueError("receipt must be object")
        token = uuid4().hex
        object.__setattr__(self, "_token", token)
        object.__setattr__(self, "_fields", tuple(
            (name, _Stamped(token, _canonical(value))) for name, value in sorted(plain.items())
        ))
        object.__setattr__(self, "_consumed", False)
        object.__setattr__(self, "_binding", None)
        object.__setattr__(self, "_fail_on_extract", _fail_on_extract)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("fixture response is immutable")
        object.__setattr__(self, name, value)

    @classmethod
    def _mixed_for_adversary(
        cls, first: AtomicFixtureResponse, second: AtomicFixtureResponse, from_second: set[str]
    ) -> AtomicFixtureResponse:
        obj = object.__new__(cls)
        a, b = dict(first._fields), dict(second._fields)
        obj._fields = tuple((name, b[name] if name in from_second else a[name]) for name in sorted(a))
        obj._token = first._token
        obj._consumed = False
        obj._binding = None
        obj._fail_on_extract = False
        obj._sealed = True
        return obj

    def extract_once(self, binding: str) -> tuple[str, dict[str, object]]:
        if self._consumed or self._binding is not None:
            raise RuntimeError("receipt already consumed")
        object.__setattr__(self, "_consumed", True)
        object.__setattr__(self, "_binding", binding)
        if self._fail_on_extract:
            raise _FixtureTransportError("fixture transport response unavailable")
        fields = dict(self._fields)
        tokens = {item.token for item in fields.values()}
        if tokens != {self._token}:
            raise ValueError("mixed receipt provenance")
        return self._token, {name: json.loads(item.value_json) for name, item in fields.items()}


class _AtomicFixtureTransport:
    """The only fixture transport boundary; its counter is the accounting source."""

    __slots__ = ("_response", "calls")

    def __init__(self, response: AtomicFixtureResponse) -> None:
        self._response = response
        self.calls = 0

    def fetch(self) -> AtomicFixtureResponse:
        self.calls += 1
        return self._response


def make_atomic_fixture_response(payload: object) -> AtomicFixtureResponse:
    return AtomicFixtureResponse(payload)


def make_atomic_fixture_transport_error() -> AtomicFixtureResponse:
    placeholder = {
        "response_id": "fixture_transport_error",
        "model": "fixture",
        "provider_status": "completed",
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "decision": {"status": "PASS"},
    }
    return AtomicFixtureResponse(placeholder, _fail_on_extract=True)


def mix_valid_responses_for_test(
    first: AtomicFixtureResponse, second: AtomicFixtureResponse, *, from_second: set[str]
) -> AtomicFixtureResponse:
    return AtomicFixtureResponse._mixed_for_adversary(first, second, from_second)


def process_atomic_fixture_receipt(
    *, case_id: str, request_payload: object, response: object
) -> tuple[dict[str, str], dict[str, Any]]:
    base: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION, "case_id": case_id,
        "terminal_status": "RECEIPT_INCOMPLETE", "failure_code": "INVALID_RECEIPT",
        "provider_kind": "FIXTURE", "provider_attempts": 0, "fixture_transport_calls": 0,
        "receipt_observed": False, "receipt_instance_token_sha256": None,
        "request_binding_sha256": None, "response_id": None, "provider_model": None,
        "provider_status": None, "input_tokens": None, "output_tokens": None, "total_tokens": None,
        "question_sha_before": None, "question_sha_sent": None, "question_sha_after": None,
        "original_question_preserved": False,
        "raw_decision_payload_sha256": None, "normalized_decision_sha256": None,
        "normalized_decision": None, "normalized_decision_status": None,
        "normalized_ambiguity_kind": None, "raw_receipt_sha256": None,
        "receipt_projection_version": RECEIPT_PROJECTION_VERSION,
        "canonical_round_trip": False, "actual_cost_estimate_usd": None,
        "input_usd_per_million": None, "output_usd_per_million": None,
        "rate_snapshot_sha256": None, "rate_source": None,
        "cost_rounding": None, "cost_precision_usd": None,
        "router_live_calls": 0, "real_provider_instantiated": False,
        "router_prepare_calls": 0, "router_cast_count": 0, "router_process_calls": 0,
        "router_high_calls": 0, "automatic_retries": 0,
    }
    try:
        if type(case_id) is not str or not case_id:
            raise ValueError("invalid case ID")
        plain_request = _plain(request_payload)
        if type(plain_request) is not dict:
            raise ValueError("request must be object")
        raw_question = plain_request.get("original_question")
        if type(raw_question) is not str:
            raise ValueError("question must be string")
        raw_question_sha = _sha(raw_question)
        req = LightRouterRequest.model_validate(json.loads(_canonical(plain_request)))
        if req.original_question != raw_question:
            raise ValueError("question normalization is not allowed")
        question_sha = _sha(req.original_question)
        binding = _sha(_canonical({"case_id": case_id, "question_sha256": question_sha, "ambiguity_kind": req.critical_ambiguity.kind}))
    except (ValueError, ValidationError, TypeError):
        base["terminal_status"] = "INVALID_REQUEST"
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, base
    if type(response) is not AtomicFixtureResponse:
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, base
    transport = _AtomicFixtureTransport(response)
    base.update({
        "request_binding_sha256": binding,
        "question_sha_before": raw_question_sha,
        "question_sha_sent": question_sha,
        "question_sha_after": question_sha,
        "original_question_preserved": raw_question_sha == question_sha,
    })
    try:
        sdk_response = transport.fetch()
        base.update({
            "provider_attempts": transport.calls,
            "fixture_transport_calls": transport.calls,
        })
        token, payload = sdk_response.extract_once(binding)
        parsed = ProviderReceipt.model_validate(payload)
        if parsed.decision.status == "ASK_ONCE" and parsed.decision.ambiguity_kind != req.critical_ambiguity.kind:
            raise ValueError("kind mismatch")
        outcome = parsed.decision.model_dump(mode="json", exclude_none=True)
        raw_decision_sha = _sha(_canonical(payload["decision"]))
        decision_sha = _sha(_canonical(outcome))
        token_sha = _sha(token)
        projection = {
            "schema_version": RECEIPT_PROJECTION_VERSION,
            "receipt_instance_token_sha256": token_sha,
            "request_binding_sha256": binding,
            "response_id": parsed.response_id, "model": parsed.model,
            "provider_status": parsed.provider_status,
            "usage": parsed.usage.model_dump(mode="json"),
            "raw_decision_payload_sha256": raw_decision_sha, "decision": outcome,
        }
        receipt_sha = _sha(_canonical(projection))
        cost = estimate_usage_cost_usd(parsed.usage, input_usd_per_million=Decimal(RATE_SNAPSHOT["input_usd_per_million"]), output_usd_per_million=Decimal(RATE_SNAPSHOT["output_usd_per_million"]))
        base.update({
            "terminal_status": "RECEIPT_COMPLETE", "failure_code": None, "receipt_observed": True,
            "receipt_instance_token_sha256": token_sha, "response_id": parsed.response_id,
            "provider_model": parsed.model, "provider_status": parsed.provider_status,
            "input_tokens": parsed.usage.input_tokens, "output_tokens": parsed.usage.output_tokens,
            "total_tokens": parsed.usage.total_tokens, "raw_decision_payload_sha256": raw_decision_sha,
            "normalized_decision_sha256": decision_sha, "normalized_decision": outcome,
            "normalized_decision_status": parsed.decision.status,
            "normalized_ambiguity_kind": parsed.decision.ambiguity_kind,
            "raw_receipt_sha256": receipt_sha, "actual_cost_estimate_usd": cost,
            "canonical_round_trip": json.loads(_canonical(projection)) == projection,
            "input_usd_per_million": RATE_SNAPSHOT["input_usd_per_million"],
            "output_usd_per_million": RATE_SNAPSHOT["output_usd_per_million"],
            "rate_snapshot_sha256": RATE_SNAPSHOT_SHA256,
            "rate_source": RATE_SNAPSHOT["source"],
            "cost_rounding": RATE_SNAPSHOT["rounding"],
            "cost_precision_usd": RATE_SNAPSHOT["precision_usd"],
        })
        return outcome, base
    except _FixtureTransportError:
        base["failure_code"] = "TRANSPORT_ERROR"
        return {"status": "FAILED", "failure_code": "UNAVAILABLE"}, base
    except BaseException:
        return {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}, base


def rebuild_atomic_receipt_sha256(audit: dict[str, Any]) -> str:
    projection = {
        "schema_version": audit["receipt_projection_version"],
        "receipt_instance_token_sha256": audit["receipt_instance_token_sha256"],
        "request_binding_sha256": audit["request_binding_sha256"],
        "response_id": audit["response_id"], "model": audit["provider_model"],
        "provider_status": audit["provider_status"],
        "usage": {"input_tokens": audit["input_tokens"], "output_tokens": audit["output_tokens"], "total_tokens": audit["total_tokens"]},
        "raw_decision_payload_sha256": audit["raw_decision_payload_sha256"],
        "decision": audit["normalized_decision"],
    }
    if _sha(_canonical(projection["decision"])) != audit["normalized_decision_sha256"]:
        raise ValueError("decision mismatch")
    return _sha(_canonical(projection))


def rebuild_atomic_cost_estimate_usd(audit: dict[str, Any]) -> str:
    if audit["rate_snapshot_sha256"] != RATE_SNAPSHOT_SHA256:
        raise ValueError("rate snapshot mismatch")
    for field, key in (
        ("input_usd_per_million", "input_usd_per_million"),
        ("output_usd_per_million", "output_usd_per_million"),
        ("rate_source", "source"),
        ("cost_rounding", "rounding"),
        ("cost_precision_usd", "precision_usd"),
    ):
        if audit[field] != RATE_SNAPSHOT[key]:
            raise ValueError("rate evidence mismatch")
    usage = ProviderReceipt.model_validate({
        "response_id": audit["response_id"],
        "model": audit["provider_model"],
        "provider_status": audit["provider_status"],
        "usage": {
            "input_tokens": audit["input_tokens"],
            "output_tokens": audit["output_tokens"],
            "total_tokens": audit["total_tokens"],
        },
        "decision": audit["normalized_decision"],
    }).usage
    return estimate_usage_cost_usd(
        usage,
        input_usd_per_million=Decimal(RATE_SNAPSHOT["input_usd_per_million"]),
        output_usd_per_million=Decimal(RATE_SNAPSHOT["output_usd_per_million"]),
    )


__all__ = [
    "make_atomic_fixture_response",
    "make_atomic_fixture_transport_error",
    "mix_valid_responses_for_test",
    "process_atomic_fixture_receipt",
    "rebuild_atomic_receipt_sha256",
    "rebuild_atomic_cost_estimate_usd",
]
