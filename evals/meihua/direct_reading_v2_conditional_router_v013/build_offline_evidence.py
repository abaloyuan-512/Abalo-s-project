from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_conditional_router_v013 import (
    begin_guarded_conditional_direct_reading,
    resume_guarded_conditional_direct_reading,
)


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "这次合作，我应该继续投入，还是停止并退出？"
CLOCK = lambda: datetime(2026, 8, 13, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
SAVED_PREPARE = high_service.prepare_direct_reading_v2_request
SAVED_CAST = high_service.cast_meihua


def request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {"question_text": QUESTION, "numbers": [7, 8, 9]}
    value.update(changes)
    return value


def ambiguity() -> dict[str, str]:
    return {"kind": "SUBJECT", "description": "所问的合作可能指两个不同项目"}


def receipt(decision: object) -> dict[str, object]:
    return {"provider_kind": "FIXTURE", "real_provider_instantiated": False, "decision": decision}


class Router:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def route(self, **_: object) -> object:
        if self.mode == "PASS":
            return receipt({"action": "PASS"})
        if self.mode == "ASK":
            return receipt({"action": "ASK_ONCE"})
        if self.mode == "FAIL":
            raise TimeoutError("fixture")
        if self.mode == "SCHEMA":
            return receipt({"action": "UNKNOWN"})
        if self.mode == "DIRECT_PREPARE":
            SAVED_PREPARE(request(), clock=CLOCK, request_id="drv2-v013-ledger1")
        if self.mode == "DIRECT_CAST":
            SAVED_CAST(high_service.MeihuaInput(7, 8, 9, CLOCK(), "Asia/Shanghai", "drv2-v013-ledger2"))
        if self.mode == "ALIAS_HELPER":
            helper_prepare()
        return receipt({"action": "PASS"})


def helper_prepare() -> object:
    return SAVED_PREPARE(request(), clock=CLOCK, request_id="drv2-v013-ledger3")


class High:
    def __init__(self, status: str = "SUCCESS") -> None:
        self.status = status

    def __call__(self, payload: dict[str, Any]) -> object:
        SAVED_PREPARE(payload, clock=CLOCK, request_id="drv2-v013-ledger-high")
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "cast_count": 1,
            "response": {
                "status": self.status,
                "direct_reading": {"text": "fixture"} if self.status == "SUCCESS" else None,
                "retryable": False,
            },
        }


def row(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": result["status"],
        "route": result.get("route"),
        "original_question_sha_before": result.get("original_question_sha_before"),
        "original_question_sha_after": result.get("original_question_sha_after"),
        "original_question_preserved": result.get("original_question_preserved"),
        "router_attempts": result.get("router_attempts", 0),
        "router_status": result.get("router_status"),
        "router_failure_code": result.get("router_failure_code"),
        "router_cast_count": result["router_cast_count"],
        "high_attempts": result["high_attempts"],
        "high_status": result["high_status"],
        "high_cast_count": result["high_cast_count"],
        "total_cast_count": result["total_cast_count"],
        "count_source": result["count_source"],
        "released": bool((result.get("high_response") or {}).get("direct_reading")),
        "automatic_retries": result["automatic_retries"],
    }


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case_id, changes in (
        ("CLEAR_DIRECT", {}),
        ("CONFIRMED_DIRECT", {"user_confirmed": True, "critical_ambiguity": ambiguity()}),
        ("SKIP_DIRECT", {"skip_router": True, "critical_ambiguity": ambiguity()}),
    ):
        rows.append(row(case_id, begin_guarded_conditional_direct_reading(request(**changes), high_invoker=High())))
    for case_id, mode in (
        ("ROUTER_PASS", "PASS"),
        ("ROUTER_EXCEPTION_FAIL_OPEN", "FAIL"),
        ("ROUTER_SCHEMA_FAIL_OPEN", "SCHEMA"),
    ):
        rows.append(row(case_id, begin_guarded_conditional_direct_reading(request(critical_ambiguity=ambiguity()), router=Router(mode), high_invoker=High())))
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_guarded_conditional_direct_reading(payload, router=Router("ASK"), high_invoker=High())
    rows.append(row("ROUTER_ASK_RESUME", resume_guarded_conditional_direct_reading(payload, waiting, user_answer="甲项目", high_invoker=High())))
    for case_id, mode in (
        ("VIOLATION_DIRECT_PREPARE", "DIRECT_PREPARE"),
        ("VIOLATION_DIRECT_CAST", "DIRECT_CAST"),
        ("VIOLATION_ALIAS_HELPER", "ALIAS_HELPER"),
    ):
        rows.append(row(case_id, begin_guarded_conditional_direct_reading(request(critical_ambiguity=ambiguity()), router=Router(mode), high_invoker=High())))
    rows.append(row("HIGH_BLOCKED_NO_RETRY", begin_guarded_conditional_direct_reading(request(), high_invoker=High("BLOCKED_OUTPUT"))))

    assert all(item["total_cast_count"] == item["router_cast_count"] + item["high_cast_count"] for item in rows)
    assert all(item["automatic_retries"] == 0 for item in rows)
    violations = [item for item in rows if item["router_status"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 3
    assert all(item["high_attempts"] == 0 and not item["released"] for item in violations)
    normal = [item for item in rows if item not in violations]
    assert all(item["router_cast_count"] == 0 and item["high_cast_count"] == 1 for item in normal)

    return {
        "stage_id": "DIRECT_READING_V2_CONDITIONAL_ROUTER_V013",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "live_calls": 0,
        "real_router_provider_instantiated": False,
        "real_high_provider_instantiated": False,
        "fixture_case_count": len(rows),
        "total_cast_count": sum(item["total_cast_count"] for item in rows),
        "count_source": "IN_PROCESS_AUTHORITY_BOUNDARY",
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
