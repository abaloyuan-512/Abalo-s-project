from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_light_router_receipt_v016 import (
    process_fixture_receipt,
    make_fixture_sdk_response,
    rebuild_receipt_projection_sha256,
    rebuild_cost_estimate_usd,
)


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "我正在决定一个副业项目的去留：是继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {
        "original_question": QUESTION,
        "critical_ambiguity": {"kind": kind, "description": "已标记的关键歧义"},
    }


def receipt(response_id: str, decision: dict[str, str], *, total: int = 230) -> dict[str, object]:
    return {
        "response_id": response_id,
        "model": "gpt-5.6-luna-fixture",
        "provider_status": "completed",
        "usage": {"input_tokens": 211, "output_tokens": total - 211, "total_tokens": total},
        "decision": decision,
    }


def row(case_id: str, outcome: dict[str, str], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "terminal_status": audit["terminal_status"],
        "failure_code": audit["failure_code"],
        "question_sha_before": audit["question_sha_before"],
        "question_sha_sent": audit["question_sha_sent"],
        "question_sha_after": audit["question_sha_after"],
        "original_question_preserved": audit["original_question_preserved"],
        "provider_kind": audit["provider_kind"],
        "provider_attempts": audit["provider_attempts"],
        "fixture_transport_calls": audit["fixture_transport_calls"],
        "receipt_observed": audit["receipt_observed"],
        "response_id": audit["response_id"],
        "provider_model": audit["provider_model"],
        "provider_status": audit["provider_status"],
        "input_tokens": audit["input_tokens"],
        "output_tokens": audit["output_tokens"],
        "total_tokens": audit["total_tokens"],
        "raw_decision_payload_sha256": audit["raw_decision_payload_sha256"],
        "normalized_decision_sha256": audit["normalized_decision_sha256"],
        "normalized_decision_status": audit["normalized_decision_status"],
        "normalized_ambiguity_kind": audit["normalized_ambiguity_kind"],
        "raw_receipt_sha256": audit["raw_receipt_sha256"],
        "receipt_projection_version": audit["receipt_projection_version"],
        "receipt_projection_reconstructed": (
            rebuild_receipt_projection_sha256(audit) == audit["raw_receipt_sha256"]
            if audit["receipt_observed"]
            else False
        ),
        "outcome": outcome,
        "actual_cost_estimate_usd": audit["actual_cost_estimate_usd"],
        "cost_estimate_mode": audit["cost_estimate_mode"],
        "input_usd_per_million": audit["input_usd_per_million"],
        "output_usd_per_million": audit["output_usd_per_million"],
        "rate_snapshot_sha256": audit["rate_snapshot_sha256"],
        "rate_source": audit["rate_source"],
        "cost_rounding": audit["cost_rounding"],
        "cost_precision_usd": audit["cost_precision_usd"],
        "cost_estimate_reconstructed": (
            rebuild_cost_estimate_usd(audit) == audit["actual_cost_estimate_usd"]
            if audit["receipt_observed"]
            else False
        ),
        "router_live_calls": audit["router_live_calls"],
        "real_provider_instantiated": audit["real_provider_instantiated"],
        "router_prepare_calls": audit["router_prepare_calls"],
        "router_cast_count": audit["router_cast_count"],
        "router_process_calls": audit["router_process_calls"],
        "router_high_calls": audit["router_high_calls"],
        "automatic_retries": audit["automatic_retries"],
    }


def build() -> dict[str, Any]:
    pass_outcome, pass_audit = process_fixture_receipt(
        request(), make_fixture_sdk_response(receipt("resp_fixture_alpha", {"status": "PASS"}), identity="sdk-alpha")
    )
    ask_outcome, ask_audit = process_fixture_receipt(
        request("JUDGMENT_OBJECT"),
        make_fixture_sdk_response(receipt("resp_fixture_beta", {"status": "ASK_ONCE", "ambiguity_kind": "JUDGMENT_OBJECT"}, total=241), identity="sdk-beta"),
    )
    fixtures: list[tuple[str, object, object, bool]] = [
        ("SUCCESS_PASS", request(), None, False),
        ("SUCCESS_ASK", request(), None, False),
        ("MISSING_ID", request(), {"model": "gpt-5.6-luna-fixture", "provider_status": "completed", "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}, "decision": {"status": "PASS"}}, False),
        ("BAD_USAGE", request(), {**receipt("resp_bad_usage", {"status": "PASS"}), "usage": {"input_tokens": 211, "output_tokens": 19, "total_tokens": 999}}, False),
        ("BAD_DECISION", request(), receipt("resp_bad_decision", {"status": "FAILED"}), False),
        ("TRANSPORT_ERROR", request(), None, True),
        ("INVALID_REQUEST", {**request(), "numbers": [1, 2, 3]}, receipt("resp_never", {"status": "PASS"}), False),
    ]
    rows: list[dict[str, Any]] = []
    for case_id, request_payload, receipt_payload, transport_error in fixtures:
        if case_id == "SUCCESS_PASS":
            rows.append(row(case_id, pass_outcome, pass_audit))
            continue
        if case_id == "SUCCESS_ASK":
            rows.append(row(case_id, ask_outcome, ask_audit))
            continue
        fixture_response = (
            make_fixture_sdk_response(receipt_payload, identity=f"sdk-{case_id.lower()}")
            if receipt_payload is not None
            else None
        )
        outcome, audit = process_fixture_receipt(
            request_payload,
            fixture_response,
            transport_error=transport_error,
        )
        rows.append(row(case_id, outcome, audit))

    complete = [item for item in rows if item["terminal_status"] == "RECEIPT_COMPLETE"]
    assert len(rows) == 7 and len(complete) == 2
    assert len({item["response_id"] for item in complete}) == 2
    assert all(item["receipt_projection_reconstructed"] for item in complete)
    assert all(item["cost_estimate_reconstructed"] for item in complete)
    assert all(item["provider_attempts"] == item["fixture_transport_calls"] for item in rows)
    assert all(item["router_live_calls"] == item["router_cast_count"] == item["router_high_calls"] == 0 for item in rows)

    costs = [Decimal(item["actual_cost_estimate_usd"]) for item in complete]
    return {
        "stage_id": "DIRECT_READING_V2_LIGHT_ROUTER_RECEIPT_V016",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "case_denominator": len(rows),
        "provider_attempts": sum(item["provider_attempts"] for item in rows),
        "fixture_transport_calls": sum(item["fixture_transport_calls"] for item in rows),
        "complete_receipt_count": len(complete),
        "response_id_count": sum(item["response_id"] is not None for item in rows),
        "raw_receipt_digest_count": sum(item["raw_receipt_sha256"] is not None for item in rows),
        "usage_record_count": sum(item["total_tokens"] is not None for item in rows),
        "actual_cost_estimate_count": len(costs),
        "actual_cost_estimate_total_usd": str(sum(costs)),
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
        "router_high_calls": 0,
        "automatic_retries": 0,
        "cases": rows,
        "deployment": False,
        "production": False,
        "default_replacement": False
    }


def main() -> None:
    evidence = build()
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    OUTPUT_PATH.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper(), "cases": evidence["case_denominator"]}))


if __name__ == "__main__":
    main()
