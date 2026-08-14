from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_pure_data_router_v014 import (
    begin_pure_data_direct_reading,
    resume_pure_data_direct_reading,
)
from tests.test_sites_direct_reading_v2 import _complete_text


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "这次合作，我应该继续投入，还是停止并退出？"


def request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {"question_text": QUESTION, "numbers": [7, 8, 9]}
    value.update(changes)
    return value


def ambiguity() -> dict[str, str]:
    return {"kind": "SUBJECT", "description": "所问的合作可能指两个不同项目"}


def provider(*, text: str | None = None, failure: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "output_text": text if text is not None else _complete_text(base="地天泰", mutual="雷泽归妹", changed="地泽临", line_name="初九", line_text="拔茅茹，以其彙。征吉。"),
        "api_status": "completed",
        "incomplete_details": None,
        "response_id": "fixture-v014-ledger",
        "model": "gpt-5.6-sol",
        "input_tokens": 200,
        "output_tokens": 2000,
        "latency_ms": 10,
    }
    if failure:
        value["failure_code"] = "PROVIDER_UNAVAILABLE"
    return value


def row(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": result["status"],
        "original_question_sha_before": result.get("original_question_sha_before"),
        "original_question_sha_after": result.get("original_question_sha_after"),
        "original_question_preserved": result.get("original_question_preserved"),
        "clarity_result": result.get("clarity_result"),
        "route": result.get("route"),
        "router_outcome_present": result.get("router_outcome_present", False),
        "router_outcome_status": result.get("router_outcome_status"),
        "router_outcome_validation_code": result.get("router_outcome_validation_code"),
        "router_outcomes_consumed": result.get("router_outcomes_consumed", 0),
        "router_callback_executions": result["router_callback_executions"],
        "router_cast_count": result["router_cast_count"],
        "prepare_calls": result["prepare_calls"],
        "deterministic_cast_count": result["deterministic_cast_count"],
        "provider_calls": result["provider_calls"],
        "high_attempts": result["high_attempts"],
        "high_status": result["high_status"],
        "automatic_retries": result["automatic_retries"],
        "released": bool((result.get("high_response") or {}).get("direct_reading")),
    }


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case_id, changes, outcome in (
        ("CLEAR", {}, None),
        ("CONFIRMED", {"user_confirmed": True, "critical_ambiguity": ambiguity()}, {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}),
        ("SKIP", {"skip_router": True, "critical_ambiguity": ambiguity()}, {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}),
        ("PASS", {"critical_ambiguity": ambiguity()}, {"status": "PASS"}),
        ("FAILED", {"critical_ambiguity": ambiguity()}, {"status": "FAILED", "failure_code": "TIMEOUT"}),
        ("MISSING", {"critical_ambiguity": ambiguity()}, None),
        ("INVALID", {"critical_ambiguity": ambiguity()}, {"status": "PASS", "question_text": "改题"}),
    ):
        rows.append(row(case_id, begin_pure_data_direct_reading(request(**changes), router_outcome=outcome, fixture_provider_result=provider())))
    payload = request(critical_ambiguity=ambiguity())
    waiting_answer = begin_pure_data_direct_reading(payload, router_outcome={"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"})
    rows.append(row("ASK_ANSWER", resume_pure_data_direct_reading(payload, waiting_answer, user_answer="甲项目", fixture_provider_result=provider())))
    waiting_skip = begin_pure_data_direct_reading(payload, router_outcome={"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"})
    rows.append(row("ASK_SKIP", resume_pure_data_direct_reading(payload, waiting_skip, skip_answer=True, fixture_provider_result=provider())))
    rows.append(row("HIGH_BLOCKED", begin_pure_data_direct_reading(request(), fixture_provider_result=provider(text="## 判断\n空壳"))))
    rows.append(row("HIGH_UNAVAILABLE", begin_pure_data_direct_reading(request(), fixture_provider_result=provider(failure=True))))

    assert all(item["router_callback_executions"] == item["router_cast_count"] == 0 for item in rows)
    assert all(item["prepare_calls"] == item["deterministic_cast_count"] == item["provider_calls"] == item["high_attempts"] == 1 for item in rows)
    assert all(item["automatic_retries"] == 0 for item in rows)
    assert all(item["original_question_preserved"] for item in rows)

    return {
        "stage_id": "DIRECT_READING_V2_PURE_DATA_ROUTER_V014",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "fixture_case_count": len(rows),
        "router_callback_executions": 0,
        "router_cast_count": 0,
        "prepare_calls": sum(item["prepare_calls"] for item in rows),
        "deterministic_cast_count": sum(item["deterministic_cast_count"] for item in rows),
        "provider_calls": sum(item["provider_calls"] for item in rows),
        "high_attempts": sum(item["high_attempts"] for item in rows),
        "automatic_retries": 0,
        "live_calls": 0,
        "real_provider_instantiated": False,
        "cases": rows,
        "deployment": False,
        "production": False,
        "default_replacement": False
    }


def main() -> None:
    evidence = build()
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    OUTPUT_PATH.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper(), "cases": evidence["fixture_case_count"]}))


if __name__ == "__main__":
    main()
