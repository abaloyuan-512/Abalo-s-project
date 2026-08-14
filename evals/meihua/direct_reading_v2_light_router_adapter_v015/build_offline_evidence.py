from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_light_router_adapter_v015 import (
    run_fixture_light_router_adapter,
    run_without_provider,
)
from abalo_iching.application.sites_pure_data_router_v014 import (
    begin_pure_data_direct_reading,
)
from tests.test_sites_direct_reading_v2 import _complete_text


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "这次合作，我应该继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {
        "original_question": QUESTION,
        "critical_ambiguity": {
            "kind": kind,
            "description": "这个表述可能指向两个不同对象",
        },
    }


def row(case_id: str, outcome: dict[str, str], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "question_sha_before": audit["question_sha_before"],
        "question_sha_sent": audit["question_sha_sent"],
        "question_sha_after": audit["question_sha_after"],
        "original_question_preserved": audit["original_question_preserved"],
        "ambiguity_kind": audit["ambiguity_kind"],
        "provider_kind": audit["provider_kind"],
        "provider_attempted": audit["provider_attempted"],
        "provider_attempts": audit["provider_attempts"],
        "provider_status": audit["provider_status"],
        "fixture_transport_calls": audit["fixture_transport_calls"],
        "router_live_calls": audit["router_live_calls"],
        "real_provider_instantiated": audit["real_provider_instantiated"],
        "raw_receipt_sha256": audit["raw_receipt_sha256"],
        "normalized_outcome_status": outcome["status"],
        "normalized_failure_code": outcome.get("failure_code"),
        "outcome_sha256": audit["outcome_sha256"],
        "plain_json": type(outcome) is dict,
        "canonical_round_trip": audit["canonical_round_trip"],
        "router_prepare_calls": audit["router_prepare_calls"],
        "router_cast_count": audit["router_cast_count"],
        "router_process_calls": audit["router_process_calls"],
        "router_high_calls": audit["router_high_calls"],
        "automatic_retries": audit["automatic_retries"],
        "terminal_status": audit["terminal_status"],
        "deployment": audit["deployment"],
        "production": audit["production"],
        "default_replacement": audit["default_replacement"],
    }


def build() -> dict[str, Any]:
    cases: list[tuple[str, dict[str, object], object, str]] = [
        ("PASS", request(), {"status": "PASS"}, "RETURN"),
        ("ASK_SUBJECT", request("SUBJECT"), {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}, "RETURN"),
        ("ASK_DECISION_AXIS", request("DECISION_AXIS"), {"status": "ASK_ONCE", "ambiguity_kind": "DECISION_AXIS"}, "RETURN"),
        ("ASK_JUDGMENT_OBJECT", request("JUDGMENT_OBJECT"), {"status": "ASK_ONCE", "ambiguity_kind": "JUDGMENT_OBJECT"}, "RETURN"),
        ("FORBIDDEN_PROVIDER_FAILED", request(), {"status": "FAILED", "failure_code": "UNAVAILABLE"}, "RETURN"),
        ("TIMEOUT", request(), None, "TIMEOUT"),
        ("EXCEPTION", request(), None, "EXCEPTION"),
        ("EMPTY", request(), "", "RETURN"),
        ("EXTRA_FIELD", request(), {"status": "PASS", "question_text": "forbidden"}, "RETURN"),
        ("KIND_MISMATCH", request(), {"status": "ASK_ONCE", "ambiguity_kind": "DECISION_AXIS"}, "RETURN"),
    ]
    rows: list[dict[str, Any]] = []
    for case_id, payload, receipt, behavior in cases:
        outcome, audit = run_fixture_light_router_adapter(
            payload,
            fixture_response=receipt,
            fixture_behavior=behavior,
            fixture_latency_ms=3,
        )
        rows.append(row(case_id, outcome, audit))
    absent_outcome, absent_audit = run_without_provider(request())
    rows.append(row("PROVIDER_ABSENT", absent_outcome, absent_audit))

    assert len(rows) == 11
    assert all(item["plain_json"] and item["canonical_round_trip"] for item in rows)
    assert all(item["original_question_preserved"] for item in rows)
    assert all(item["router_prepare_calls"] == item["router_cast_count"] == 0 for item in rows)
    assert all(item["router_process_calls"] == item["router_high_calls"] == 0 for item in rows)
    assert all(item["router_live_calls"] == 0 for item in rows)
    assert all(item["real_provider_instantiated"] is False for item in rows)
    assert all(item["automatic_retries"] == 0 for item in rows)

    high_fixture = {
        "output_text": _complete_text(base="地天泰", mutual="雷泽归妹", changed="地泽临", line_name="初九", line_text="拔茅茹，以其汇。征吉。"),
        "api_status": "completed",
        "incomplete_details": None,
        "response_id": "fixture-v015-ledger-high",
        "model": "gpt-5.6-sol",
        "input_tokens": 200,
        "output_tokens": 2000,
        "latency_ms": 10,
    }
    integration_rows: list[dict[str, Any]] = []
    for case_id, receipt in (
        ("INTEGRATION_PASS", {"status": "PASS"}),
        ("INTEGRATION_FAILED", None),
        ("INTEGRATION_ASK", {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}),
    ):
        behavior = "TIMEOUT" if case_id == "INTEGRATION_FAILED" else "RETURN"
        outcome, adapter_audit = run_fixture_light_router_adapter(
            request(), fixture_response=receipt, fixture_behavior=behavior
        )
        diode = json.loads(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
        v014_result = begin_pure_data_direct_reading(
            {
                "question_text": QUESTION,
                "numbers": [7, 8, 9],
                "critical_ambiguity": request()["critical_ambiguity"],
            },
            router_outcome=diode,
            fixture_provider_result=high_fixture,
        )
        integration_rows.append({
            "case_id": case_id,
            "adapter_outcome_sha256": adapter_audit["outcome_sha256"],
            "canonical_json_diode": diode == outcome,
            "v014_outcome_consumed": v014_result.get("router_outcomes_consumed", 0),
            "v014_route": v014_result.get("route"),
            "v014_status": v014_result.get("status"),
            "v014_high_status": v014_result.get("high_status"),
            "v014_high_attempts": v014_result.get("high_attempts", 0),
            "v014_cast_count": v014_result.get("deterministic_cast_count", 0),
            "released": bool((v014_result.get("high_response") or {}).get("direct_reading")),
            "original_question_preserved": v014_result.get("original_question_preserved", True),
        })
    assert integration_rows[0]["v014_high_attempts"] == integration_rows[0]["v014_cast_count"] == 1
    assert integration_rows[1]["v014_high_attempts"] == integration_rows[1]["v014_cast_count"] == 1
    assert integration_rows[2]["v014_status"] == "WAITING_FOR_ONE_ANSWER"
    assert integration_rows[2]["v014_high_attempts"] == integration_rows[2]["v014_cast_count"] == 0
    assert all(item["canonical_json_diode"] and item["original_question_preserved"] for item in integration_rows)

    pass_or_ask = sum(item["normalized_outcome_status"] in {"PASS", "ASK_ONCE"} for item in rows)
    failed = sum(item["normalized_outcome_status"] == "FAILED" for item in rows)
    return {
        "stage_id": "DIRECT_READING_V2_LIGHT_ROUTER_ADAPTER_V015",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "fixture_case_count": len(rows),
        "case_denominator": len(rows),
        "pass_or_ask_outcomes": pass_or_ask,
        "failed_outcomes": failed,
        "provider_attempts": sum(item["provider_attempts"] for item in rows),
        "fixture_transport_calls": sum(item["fixture_transport_calls"] for item in rows),
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
        "router_high_calls": 0,
        "automatic_retries": 0,
        "cases": rows,
        "integration_case_denominator": len(integration_rows),
        "integration_cases": integration_rows,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def main() -> None:
    evidence = build()
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    OUTPUT_PATH.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({
        "path": str(OUTPUT_PATH),
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper(),
        "cases": evidence["fixture_case_count"],
    }))


if __name__ == "__main__":
    main()
