from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_light_router_atomic_receipt_v017 import (
    make_atomic_fixture_response,
    make_atomic_fixture_transport_error,
    mix_valid_responses_for_test,
    process_atomic_fixture_receipt,
    rebuild_atomic_cost_estimate_usd,
    rebuild_atomic_receipt_sha256,
)


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "我正在决定一个副业项目的去留：是继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {
        "original_question": QUESTION,
        "critical_ambiguity": {"kind": kind, "description": "已标记的关键歧义"},
    }


def receipt(
    response_id: str,
    decision: dict[str, str] | None = None,
    *,
    usage: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "response_id": response_id,
        "model": "gpt-5.6-luna-fixture",
        "provider_status": "completed",
        "usage": usage or {"input_tokens": 211, "output_tokens": 19, "total_tokens": 230},
        "decision": decision or {"status": "PASS"},
    }


class MaliciousReceipt:
    def __init__(self) -> None:
        object.__setattr__(self, "side_effects", 0)

    def __getattr__(self, name: str) -> object:
        object.__setattr__(self, "side_effects", self.side_effects + 1)
        raise AttributeError(name)

    def __iter__(self):
        object.__setattr__(self, "side_effects", self.side_effects + 1)
        return iter(())


def execute(case_id: str, request_payload: object, response: object) -> dict[str, Any]:
    outcome, audit = process_atomic_fixture_receipt(
        case_id=case_id,
        request_payload=request_payload,
        response=response,
    )
    complete = audit["terminal_status"] == "RECEIPT_COMPLETE"
    return {
        **audit,
        "outcome": outcome,
        "receipt_projection_reconstructed": (
            rebuild_atomic_receipt_sha256(audit) == audit["raw_receipt_sha256"]
            if complete
            else False
        ),
        "cost_estimate_reconstructed": (
            rebuild_atomic_cost_estimate_usd(audit) == audit["actual_cost_estimate_usd"]
            if complete
            else False
        ),
    }


def build() -> dict[str, Any]:
    pass_response = make_atomic_fixture_response(receipt("resp_fixture_alpha"))
    rows = [execute("SUCCESS_PASS", request(), pass_response)]
    rows.append(
        execute(
            "SUCCESS_ASK",
            request("JUDGMENT_OBJECT"),
            make_atomic_fixture_response(
                receipt(
                    "resp_fixture_beta",
                    {"status": "ASK_ONCE", "ambiguity_kind": "JUDGMENT_OBJECT"},
                    usage={"input_tokens": 211, "output_tokens": 30, "total_tokens": 241},
                )
            ),
        )
    )
    missing_id = receipt("placeholder")
    del missing_id["response_id"]
    rows.append(execute("MISSING_ID", request(), make_atomic_fixture_response(missing_id)))
    missing_usage = receipt("resp_missing_usage")
    del missing_usage["usage"]
    rows.append(execute("MISSING_USAGE", request(), make_atomic_fixture_response(missing_usage)))
    rows.append(
        execute(
            "BAD_USAGE",
            request(),
            make_atomic_fixture_response(
                receipt(
                    "resp_bad_usage",
                    usage={"input_tokens": 211, "output_tokens": 19, "total_tokens": 999},
                )
            ),
        )
    )
    rows.append(
        execute(
            "BAD_DECISION",
            request(),
            make_atomic_fixture_response(receipt("resp_bad_decision", {"status": "FAILED"})),
        )
    )
    rows.append(execute("TRANSPORT_ERROR", request(), make_atomic_fixture_transport_error()))
    rows.append(
        execute(
            "INVALID_REQUEST",
            {**request(), "numbers": [1, 2, 3]},
            make_atomic_fixture_response(receipt("resp_never")),
        )
    )
    malicious = MaliciousReceipt()
    rows.append(execute("MALICIOUS_RECEIPT_OR_FIELD", request(), malicious))
    assert malicious.side_effects == 0

    source_a = make_atomic_fixture_response(receipt("resp_mix_a"))
    source_b = make_atomic_fixture_response(
        receipt("resp_mix_b", {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"})
    )
    mixed = mix_valid_responses_for_test(source_a, source_b, from_second={"model", "decision"})
    rows.append(execute("CROSS_RECEIPT_MIX", request(), mixed))
    rows.append(execute("CROSS_CASE_REUSE", request(), pass_response))

    complete = [item for item in rows if item["terminal_status"] == "RECEIPT_COMPLETE"]
    failures = [item for item in rows if item["terminal_status"] != "RECEIPT_COMPLETE"]
    assert len(rows) == 11 and len(complete) == 2 and len(failures) == 9
    assert [item["case_id"] for item in rows] == [
        "SUCCESS_PASS", "SUCCESS_ASK", "MISSING_ID", "MISSING_USAGE", "BAD_USAGE",
        "BAD_DECISION", "TRANSPORT_ERROR", "INVALID_REQUEST",
        "MALICIOUS_RECEIPT_OR_FIELD", "CROSS_RECEIPT_MIX", "CROSS_CASE_REUSE",
    ]
    assert all(item["receipt_projection_reconstructed"] for item in complete)
    assert all(item["cost_estimate_reconstructed"] for item in complete)
    assert all(item["provider_attempts"] == item["fixture_transport_calls"] for item in rows)
    assert all(
        item["router_live_calls"] == item["router_prepare_calls"] == item["router_cast_count"]
        == item["router_process_calls"] == item["router_high_calls"] == item["automatic_retries"] == 0
        for item in rows
    )
    assert all(
        item["response_id"] is item["total_tokens"] is item["receipt_instance_token_sha256"]
        is item["raw_receipt_sha256"] is None
        for item in failures
    )
    costs = [Decimal(item["actual_cost_estimate_usd"]) for item in complete]
    evidence_count = len(complete)
    return {
        "stage_id": "DIRECT_READING_V2_LIGHT_ROUTER_ATOMIC_RECEIPT_V017",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "case_denominator": len(rows),
        "complete_receipt_count": evidence_count,
        "failed_or_invalid_count": len(failures),
        "provider_attempts": sum(item["provider_attempts"] for item in rows),
        "fixture_transport_calls": sum(item["fixture_transport_calls"] for item in rows),
        "response_id_count": sum(item["response_id"] is not None for item in rows),
        "usage_record_count": sum(item["total_tokens"] is not None for item in rows),
        "instance_token_evidence_count": sum(item["receipt_instance_token_sha256"] is not None for item in rows),
        "raw_receipt_digest_count": sum(item["raw_receipt_sha256"] is not None for item in rows),
        "unique_instance_token_count": len({item["receipt_instance_token_sha256"] for item in complete}),
        "unique_request_binding_count": len({item["request_binding_sha256"] for item in complete}),
        "missing_usage_failure_count": sum(item["case_id"] == "MISSING_USAGE" for item in failures),
        "malicious_rejection_count": sum(item["case_id"] == "MALICIOUS_RECEIPT_OR_FIELD" for item in failures),
        "cross_receipt_rejection_count": sum(item["case_id"] == "CROSS_RECEIPT_MIX" for item in failures),
        "cross_case_reuse_rejection_count": sum(item["case_id"] == "CROSS_CASE_REUSE" for item in failures),
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
        "default_replacement": False,
    }


def main() -> None:
    evidence = build()
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    OUTPUT_PATH.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({
        "path": str(OUTPUT_PATH),
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper(),
        "cases": evidence["case_denominator"],
    }))


if __name__ == "__main__":
    main()
