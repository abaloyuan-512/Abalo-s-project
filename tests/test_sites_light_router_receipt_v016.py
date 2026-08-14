from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from abalo_iching.application.sites_light_router_receipt_v016 import (
    RECEIPT_PROJECTION_VERSION,
    RATE_SNAPSHOT_SHA256,
    ReceiptUsage,
    estimate_usage_cost_usd,
    make_fixture_sdk_response,
    process_fixture_receipt,
    rebuild_cost_estimate_usd,
    rebuild_receipt_projection_sha256,
)


QUESTION = "我正在决定一个副业项目的去留：是继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {
        "original_question": QUESTION,
        "critical_ambiguity": {
            "kind": kind,
            "description": "上游已标记一个可能改变判断对象的关键歧义",
        },
    }


def receipt(
    *,
    response_id: str = "resp_fixture_unique_A",
    model: str = "gpt-5.6-luna-2026-08-01",
    input_tokens: int = 211,
    output_tokens: int = 19,
    total_tokens: int = 230,
    decision: object = None,
) -> dict[str, object]:
    return {
        "response_id": response_id,
        "model": model,
        "provider_status": "completed",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "decision": decision if decision is not None else {"status": "PASS"},
    }


def sdk(payload: object, identity: str = "fixture-response-instance") -> object:
    return make_fixture_sdk_response(payload, identity=identity)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def assert_complete(outcome: dict[str, str], audit: dict[str, Any]) -> None:
    assert audit["terminal_status"] == "RECEIPT_COMPLETE"
    assert audit["receipt_observed"] is True
    assert audit["provider_attempts"] == audit["fixture_transport_calls"] == 1
    assert audit["router_live_calls"] == 0
    assert audit["real_provider_instantiated"] is False
    assert audit["router_prepare_calls"] == audit["router_cast_count"] == 0
    assert audit["router_process_calls"] == audit["router_high_calls"] == 0
    assert audit["automatic_retries"] == 0
    assert audit["question_sha_before"] == audit["question_sha_sent"] == audit["question_sha_after"] == sha(QUESTION)
    assert audit["original_question_preserved"] is True
    assert audit["receipt_projection_version"] == RECEIPT_PROJECTION_VERSION
    assert audit["raw_receipt_sha256"] == rebuild_receipt_projection_sha256(audit)
    assert audit["raw_receipt_sha256"] != audit["normalized_decision_sha256"]
    assert audit["rate_snapshot_sha256"] == RATE_SNAPSHOT_SHA256
    assert audit["actual_cost_estimate_usd"] == rebuild_cost_estimate_usd(audit)
    assert QUESTION not in json.dumps(audit, ensure_ascii=False)
    assert "original_question\"" not in json.dumps(audit, ensure_ascii=False)
    assert type(outcome) is dict


def test_complete_pass_receipt_preserves_exact_id_usage_and_rebuildable_digests() -> None:
    payload = receipt(response_id="resp_opaque_sentinel_Alpha", input_tokens=321, output_tokens=17, total_tokens=338)
    outcome, audit = process_fixture_receipt(request(), sdk(payload))
    assert outcome == {"status": "PASS"}
    assert audit["response_id"] == "resp_opaque_sentinel_Alpha"
    assert audit["provider_model"] == payload["model"]
    assert (audit["input_tokens"], audit["output_tokens"], audit["total_tokens"]) == (321, 17, 338)
    assert audit["actual_cost_estimate_usd"] == "0.000423000000"
    assert_complete(outcome, audit)


def test_two_distinct_receipts_do_not_reuse_ids_or_digests() -> None:
    _, first = process_fixture_receipt(request(), sdk(receipt(response_id="resp_unique_A"), "instance-A"))
    _, second = process_fixture_receipt(request(), sdk(receipt(response_id="resp_unique_B"), "instance-B"))
    assert first["response_id"] == "resp_unique_A"
    assert second["response_id"] == "resp_unique_B"
    assert first["raw_receipt_sha256"] != second["raw_receipt_sha256"]


def test_fixture_sdk_response_is_deeply_immutable_and_one_shot() -> None:
    response = sdk(receipt(), "one-shot-instance")
    first = response.extract_once()  # type: ignore[attr-defined]
    first["usage"]["input_tokens"] = 999  # type: ignore[index]
    with pytest.raises(RuntimeError, match="already consumed"):
        response.extract_once()  # type: ignore[attr-defined]
    fresh = sdk(receipt(), "fresh-instance")
    extracted = fresh.extract_once()  # type: ignore[attr-defined]
    assert extracted["usage"]["input_tokens"] == 211  # type: ignore[index]


@pytest.mark.parametrize("field", ["response_id", "model", "provider_status", "usage", "decision"])
def test_missing_receipt_field_is_incomplete(field: str) -> None:
    payload = receipt()
    payload.pop(field)
    outcome, audit = process_fixture_receipt(request(), sdk(payload))
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert audit["terminal_status"] == "RECEIPT_INCOMPLETE"
    assert audit["receipt_observed"] is False
    assert audit["response_id"] is audit["input_tokens"] is audit["raw_receipt_sha256"] is None


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": True, "output_tokens": 1, "total_tokens": 2},
        {"input_tokens": -1, "output_tokens": 1, "total_tokens": 0},
        {"input_tokens": 1, "output_tokens": 2, "total_tokens": 4},
        {"input_tokens": 1, "output_tokens": 2},
        {"input_tokens": "1", "output_tokens": 2, "total_tokens": 3},
    ],
)
def test_bad_usage_is_incomplete(usage: dict[str, object]) -> None:
    payload = receipt()
    payload["usage"] = usage
    _, audit = process_fixture_receipt(request(), sdk(payload))
    assert audit["terminal_status"] == "RECEIPT_INCOMPLETE"
    assert audit["input_tokens"] is audit["output_tokens"] is audit["total_tokens"] is None


@pytest.mark.parametrize(
    "decision",
    [
        {"status": "FAILED", "failure_code": "TIMEOUT"},
        {"status": "PASS", "question": "free text"},
        {"status": "ASK_ONCE"},
        {"status": "ASK_ONCE", "ambiguity_kind": "DECISION_AXIS"},
        {"status": "UNKNOWN"},
    ],
)
def test_invalid_decision_or_kind_mismatch_is_incomplete(decision: object) -> None:
    payload = receipt(decision=decision)
    outcome, audit = process_fixture_receipt(request(), sdk(payload))
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert audit["terminal_status"] == "RECEIPT_INCOMPLETE"


def test_ask_receipt_matches_kind_and_preserves_payload_digest() -> None:
    decision = {"status": "ASK_ONCE", "ambiguity_kind": "JUDGMENT_OBJECT"}
    outcome, audit = process_fixture_receipt(
        request("JUDGMENT_OBJECT"), sdk(receipt(decision=decision))
    )
    assert outcome == decision
    canonical = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert audit["raw_decision_payload_sha256"] == sha(canonical)
    assert audit["normalized_decision_sha256"] == sha(canonical)
    assert_complete(outcome, audit)


class Evil:
    def __init__(self) -> None:
        object.__setattr__(self, "effects", 0)

    def __iter__(self):
        object.__setattr__(self, "effects", self.effects + 1)
        return iter(())

    def __getattr__(self, _name: str) -> object:
        object.__setattr__(self, "effects", self.effects + 1)
        raise AttributeError

    def model_dump(self) -> object:
        object.__setattr__(self, "effects", self.effects + 1)
        return receipt()


def test_malicious_non_plain_receipt_is_rejected_without_side_effect() -> None:
    evil = Evil()
    _, audit = process_fixture_receipt(request(), evil)
    assert evil.effects == 0
    assert audit["terminal_status"] == "RECEIPT_INCOMPLETE"


def test_nested_evil_and_cross_receipt_injection_are_rejected_atomically() -> None:
    evil = Evil()
    payload = receipt()
    payload["decision"] = evil
    with pytest.raises(ValueError):
        sdk(payload)
    assert evil.effects == 0
    _, audit = process_fixture_receipt(request(), evil)
    assert audit["receipt_observed"] is False
    mixed = receipt(response_id="resp_from_A")
    mixed["decision_receipt_id"] = "resp_from_B"
    _, mixed_audit = process_fixture_receipt(request(), sdk(mixed))
    assert mixed_audit["terminal_status"] == "RECEIPT_INCOMPLETE"


@pytest.mark.parametrize(
    ("mutator", "field"),
    [
        (lambda value: value.update(response_id="resp_changed"), "response_id"),
        (lambda value: value.update(provider_model="different-model"), "provider_model"),
        (lambda value: value.update(input_tokens=value["input_tokens"] + 1, total_tokens=value["total_tokens"] + 1), "input_tokens"),
        (lambda value: value.update(raw_decision_payload_sha256="0" * 64), "raw_decision_payload_sha256"),
    ],
)
def test_projection_digest_changes_when_any_bound_field_changes(mutator: Any, field: str) -> None:
    _, audit = process_fixture_receipt(request(), sdk(receipt()))
    original = rebuild_receipt_projection_sha256(audit)
    changed = dict(audit)
    mutator(changed)
    assert rebuild_receipt_projection_sha256(changed) != original, field


def test_transport_error_and_invalid_request_have_no_receipt_or_usage() -> None:
    _, transport = process_fixture_receipt(request(), None, transport_error=True)
    assert transport["provider_attempts"] == transport["fixture_transport_calls"] == 1
    assert transport["receipt_observed"] is False
    assert transport["response_id"] is transport["total_tokens"] is None
    _, invalid = process_fixture_receipt({**request(), "numbers": [1, 2, 3]}, sdk(receipt()))
    assert invalid["terminal_status"] == "INVALID_REQUEST"
    assert invalid["provider_attempts"] == invalid["fixture_transport_calls"] == 0


def test_cost_estimate_is_decimal_and_rejects_negative_rates() -> None:
    usage = ReceiptUsage(input_tokens=1000, output_tokens=100, total_tokens=1100)
    assert estimate_usage_cost_usd(
        usage,
        input_usd_per_million=Decimal("1"),
        output_usd_per_million=Decimal("6"),
    ) == "0.001600000000"
    with pytest.raises(ValueError, match="non-negative"):
        estimate_usage_cost_usd(
            usage,
            input_usd_per_million=Decimal("-1"),
            output_usd_per_million=Decimal("6"),
        )


def test_cost_rebuild_rejects_rate_tampering() -> None:
    _, audit = process_fixture_receipt(request(), sdk(receipt()))
    assert rebuild_cost_estimate_usd(audit) == audit["actual_cost_estimate_usd"]
    tampered = dict(audit)
    tampered["input_usd_per_million"] = "0.01"
    with pytest.raises(ValueError, match="rate metadata"):
        rebuild_cost_estimate_usd(tampered)


def test_v015_live_fail_and_history_are_immutable() -> None:
    root = Path(__file__).resolve().parents[1]
    locked = {
        "outputs/v015_router_only_live_ledger.json": "FAB59E6BC856C3EA217D7702C76D8252A670E7E2F17DB8639CB6E0A2EA491321",
        "evals/meihua/direct_reading_v2_light_router_adapter_v015/candidate_manifest.json": "D88700084FBE154AFE7F4BB307D45C1015302C26C43645986B1D9AD4F40CD49F",
        "src/abalo_iching/application/sites_light_router_adapter_v015.py": "01F5DF3C7E3E119F96E7CA54898A81E8C837B6E04E86974E67C23584CA0B55A7",
        "src/abalo_iching/application/sites_pure_data_router_v014.py": "CB2A3827AC433403F1D0F38DE5E0B0456D1D4FC99B49DBF5F285B6814BCA51BB",
    }
    for relative, expected in locked.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest().upper() == expected
    final = json.loads(
        (root / "evals/meihua/direct_reading_v2_light_router_adapter_v015/live_final_outcome.json").read_text(encoding="utf-8")
    )
    assert final["verdict"] == "ROUTER_ONLY_LIVE_FAIL_STOP"
    assert final["calls_remaining"] == 0
