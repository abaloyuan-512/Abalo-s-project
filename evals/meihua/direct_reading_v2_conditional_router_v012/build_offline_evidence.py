from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_conditional_router_v1 import (
    begin_conditional_direct_reading,
    resume_conditional_direct_reading,
)


STAGE_ID = "DIRECT_READING_V2_CONDITIONAL_ROUTER_V012"
QUESTION = "这次合作，我应该继续投入，还是停止并退出？"
OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")


class FixtureRouter:
    def __init__(self, decision: object = None, *, fail: bool = False) -> None:
        self.decision = {"action": "PASS"} if decision is None else decision
        self.fail = fail
        self.calls = 0

    def route(self, **kwargs: object) -> object:
        assert set(kwargs) == {
            "original_question",
            "critical_ambiguity_kind",
            "critical_ambiguity_description",
        }
        self.calls += 1
        if self.fail:
            raise TimeoutError("fixture timeout")
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "decision": self.decision,
        }


class FixtureHigh:
    def __init__(self, status: str = "SUCCESS") -> None:
        self.status = status
        self.calls: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, Any]) -> object:
        self.calls.append(payload)
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "cast_count": 1,
            "response": {
                "status": self.status,
                "direct_reading": (
                    {"text": "fixture-only-complete-reading"}
                    if self.status == "SUCCESS"
                    else None
                ),
                "retryable": False,
            },
        }


def request(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "question_text": QUESTION,
        "numbers": [7, 8, 9],
    }
    payload.update(changes)
    return payload


def ambiguity() -> dict[str, str]:
    return {
        "kind": "SUBJECT",
        "description": "所问的合作可能指两个不同项目",
    }


def row(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "route": result["route"],
        "clarity_result": result["clarity_result"],
        "clarity_reason": result["clarity_reason"],
        "original_question_sha_before": result["original_question_sha_before"],
        "original_question_sha_after": result["original_question_sha_after"],
        "original_question_preserved": result["original_question_preserved"],
        "router_attempts": result["router_attempts"],
        "router_status": result["router_status"],
        "router_failure_code": result["router_failure_code"],
        "high_attempts": result["high_attempts"],
        "high_status": result["high_status"],
        "cast_count": result["cast_count"],
        "automatic_retries": result["automatic_retries"],
        "final_release_status": result["high_status"],
        "router_provider_kind": result["router_provider_kind"],
        "router_real_provider_instantiated": result[
            "router_real_provider_instantiated"
        ],
        "high_provider_kind": result["high_provider_kind"],
        "high_real_provider_instantiated": result[
            "high_real_provider_instantiated"
        ],
    }


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    high = FixtureHigh()
    rows.append(row("CLEAR_DIRECT", begin_conditional_direct_reading(request(), high_invoker=high)))

    high = FixtureHigh()
    rows.append(
        row(
            "CONFIRMED_DIRECT",
            begin_conditional_direct_reading(
                request(user_confirmed=True, critical_ambiguity=ambiguity()),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    rows.append(
        row(
            "SKIP_OVERRIDES_AMBIGUITY",
            begin_conditional_direct_reading(
                request(skip_router=True, critical_ambiguity=ambiguity()),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    rows.append(
        row(
            "AMBIGUITY_PASS",
            begin_conditional_direct_reading(
                request(critical_ambiguity=ambiguity()),
                router=FixtureRouter({"action": "PASS"}),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(
        payload,
        router=FixtureRouter({"action": "ASK_ONCE"}),
        high_invoker=high,
    )
    completed = resume_conditional_direct_reading(
        payload,
        waiting,
        user_answer="我问的是甲项目。",
        high_invoker=high,
    )
    rows.append(row("AMBIGUITY_ASK_ONCE_ANSWER", completed))

    high = FixtureHigh()
    rows.append(
        row(
            "ROUTER_EXCEPTION_FAIL_OPEN",
            begin_conditional_direct_reading(
                request(critical_ambiguity=ambiguity()),
                router=FixtureRouter(fail=True),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    rows.append(
        row(
            "ROUTER_EMPTY_FAIL_OPEN",
            begin_conditional_direct_reading(
                request(critical_ambiguity=ambiguity()),
                router=FixtureRouter(""),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    rows.append(
        row(
            "ROUTER_SCHEMA_FAIL_OPEN",
            begin_conditional_direct_reading(
                request(critical_ambiguity=ambiguity()),
                router=FixtureRouter({"action": "UNKNOWN"}),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh()
    rows.append(
        row(
            "ROUTER_FORBIDDEN_FIELD_FAIL_OPEN",
            begin_conditional_direct_reading(
                request(critical_ambiguity=ambiguity()),
                router=FixtureRouter(
                    {"action": "PASS", "question_text": "替换后的问题"}
                ),
                high_invoker=high,
            ),
        )
    )

    high = FixtureHigh("BLOCKED_OUTPUT")
    rows.append(
        row(
            "HIGH_FAILURE_NO_RETRY",
            begin_conditional_direct_reading(request(), high_invoker=high),
        )
    )

    assert all(item["original_question_preserved"] for item in rows)
    assert all(item["router_attempts"] <= 1 for item in rows)
    assert all(item["high_attempts"] == 1 for item in rows)
    assert all(item["cast_count"] == 1 for item in rows)
    assert all(item["automatic_retries"] == 0 for item in rows)
    assert all(item["high_provider_kind"] == "FIXTURE" for item in rows)
    assert all(item["high_real_provider_instantiated"] is False for item in rows)
    assert rows[-1]["final_release_status"] == "BLOCKED_OUTPUT"

    return {
        "stage_id": STAGE_ID,
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "live_calls": 0,
        "real_router_provider_instantiated": False,
        "real_high_provider_instantiated": False,
        "fixture_case_count": len(rows),
        "fixture_router_attempts": sum(item["router_attempts"] for item in rows),
        "fixture_high_attempts": sum(item["high_attempts"] for item in rows),
        "fixture_cast_count": sum(item["cast_count"] for item in rows),
        "automatic_retries": sum(item["automatic_retries"] for item in rows),
        "cases": rows,
        "candidate_manifest_sha256": None,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def main() -> None:
    evidence = build()
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    OUTPUT_PATH.write_text(encoded, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "path": str(OUTPUT_PATH),
                "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper(),
                "fixture_case_count": evidence["fixture_case_count"],
                "live_calls": evidence["live_calls"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
