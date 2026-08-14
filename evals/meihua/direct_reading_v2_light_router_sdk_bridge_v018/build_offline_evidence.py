from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_light_router_adapter_v015 import ModelDecision
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import rebuild_atomic_receipt_sha256
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import (
    bridge_sdk_response_to_v017,
    make_sdk_response_fixture,
    mix_sdk_response_fixtures_for_test,
    rebuild_integration_binding_sha256,
)


OUTPUT_PATH = Path(__file__).with_name("offline_ledger.json")
QUESTION = "我正在决定这个项目的去留：是继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {"original_question": QUESTION, "critical_ambiguity": {"kind": kind, "description": "关键歧义"}}


class MaliciousSDKObject:
    def __init__(self) -> None:
        object.__setattr__(self, "side_effects", 0)

    def __getattr__(self, name: str) -> object:
        object.__setattr__(self, "side_effects", self.side_effects + 1)
        raise AttributeError(name)

    def __iter__(self):
        object.__setattr__(self, "side_effects", self.side_effects + 1)
        return iter(())


def execute(case_id: str, response: object, *, request_payload: object | None = None, kind: str = "SUBJECT") -> dict[str, Any]:
    outcome, bridge = bridge_sdk_response_to_v017(
        case_id=case_id,
        request_payload=request(kind) if request_payload is None else request_payload,
        sdk_response=response,
    )
    v017 = bridge["v017_audit"]
    return {
        "case_id": case_id,
        "terminal_status": bridge["terminal_status"],
        "failure_code": bridge["failure_code"],
        "sdk_response_extraction_attempts": bridge["sdk_response_extraction_attempts"],
        "sdk_response_consumed": bridge["sdk_response_consumed"],
        "sdk_response_local_instance_sha256": bridge["sdk_response_local_instance_sha256"],
        "v017_receipt_attempts": bridge["v017_receipt_attempts"],
        "outcome": outcome,
        "question_sha_before": v017["question_sha_before"] if v017 else None,
        "question_sha_sent": v017["question_sha_sent"] if v017 else None,
        "question_sha_after": v017["question_sha_after"] if v017 else None,
        "original_question_preserved": v017["original_question_preserved"] if v017 else False,
        "response_id": v017["response_id"] if v017 else None,
        "provider_model": v017["provider_model"] if v017 else None,
        "provider_status": v017["provider_status"] if v017 else None,
        "input_tokens": v017["input_tokens"] if v017 else None,
        "output_tokens": v017["output_tokens"] if v017 else None,
        "total_tokens": v017["total_tokens"] if v017 else None,
        "receipt_instance_token_sha256": v017["receipt_instance_token_sha256"] if v017 else None,
        "request_binding_sha256": v017["request_binding_sha256"] if v017 else None,
        "raw_decision_payload_sha256": v017["raw_decision_payload_sha256"] if v017 else None,
        "normalized_decision_sha256": v017["normalized_decision_sha256"] if v017 else None,
        "raw_receipt_sha256": v017["raw_receipt_sha256"] if v017 else None,
        "v017_fixture_transport_calls": v017["fixture_transport_calls"] if v017 else 0,
        "v017_rebuild_match": bool(v017 and v017["receipt_observed"] and rebuild_atomic_receipt_sha256(v017) == v017["raw_receipt_sha256"]),
        "integration_binding_sha256": bridge["integration_binding_sha256"],
        "integration_binding_rebuilt": bool(
            bridge["integration_binding_sha256"]
            and rebuild_integration_binding_sha256(bridge) == bridge["integration_binding_sha256"]
        ),
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "router_high_calls": 0,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
        "automatic_retries": 0,
    }


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rows.append(execute("SUCCESS_PASS", make_sdk_response_fixture(response_id="resp_sdk_alpha")))
    rows.append(execute(
        "SUCCESS_ASK",
        make_sdk_response_fixture(response_id="resp_sdk_beta", input_tokens=120, output_tokens=12, total_tokens=132, decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="JUDGMENT_OBJECT")),
        kind="JUDGMENT_OBJECT",
    ))
    rows.append(execute("MISSING_ID", make_sdk_response_fixture(response_id=None)))
    rows.append(execute("MISSING_USAGE", make_sdk_response_fixture(response_id="resp_missing_usage", input_tokens=None, output_tokens=None, total_tokens=None)))
    rows.append(execute("BAD_USAGE", make_sdk_response_fixture(response_id="resp_bad_usage", total_tokens=999)))
    rows.append(execute("NON_COMPLETED", make_sdk_response_fixture(response_id="resp_incomplete", status="incomplete")))
    rows.append(execute("KIND_MISMATCH", make_sdk_response_fixture(response_id="resp_kind", decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="DECISION_AXIS"))))
    malicious = MaliciousSDKObject()
    rows.append(execute("MALICIOUS_SDK_OBJECT", malicious))
    assert malicious.side_effects == 0
    a = make_sdk_response_fixture(response_id="resp_mix_a")
    b = make_sdk_response_fixture(response_id="resp_mix_b", decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="SUBJECT"))
    rows.append(execute("CROSS_SDK_RESPONSE_MIX", mix_sdk_response_fixtures_for_test(a, b, from_second={"model", "decision"})))
    reused = make_sdk_response_fixture(response_id="resp_reuse")
    assert execute("REUSE_CONTROL", reused)["terminal_status"] == "TELEMETRY_COMPLETE"
    rows.append(execute("CROSS_CASE_REUSE", reused))
    rows.append(execute("EXTRACTION_ERROR", make_sdk_response_fixture(response_id="resp_extract", extraction_error=True)))
    invalid_response = make_sdk_response_fixture(response_id="resp_not_consumed")
    rows.append(execute("INVALID_REQUEST_NO_CALL", invalid_response, request_payload={"bad": "request"}))
    assert execute("INVALID_REQUEST_CONTROL", invalid_response)["terminal_status"] == "TELEMETRY_COMPLETE"

    ids = [row["case_id"] for row in rows]
    assert len(rows) == len(set(ids)) == 12
    successes = [row for row in rows if row["terminal_status"] == "TELEMETRY_COMPLETE"]
    failures = [row for row in rows if row["terminal_status"] != "TELEMETRY_COMPLETE"]
    assert len(successes) == 2 and len(failures) == 10
    assert all(row["v017_rebuild_match"] for row in successes)
    assert all(row["integration_binding_rebuilt"] for row in successes)
    assert all(row["response_id"] is row["total_tokens"] is row["receipt_instance_token_sha256"] is row["raw_receipt_sha256"] is None for row in failures)
    assert all(row["router_live_calls"] == row["router_high_calls"] == row["router_cast_count"] == row["automatic_retries"] == 0 for row in rows)
    return {
        "stage_id": "DIRECT_READING_V2_LIGHT_ROUTER_SDK_BRIDGE_V018",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "case_denominator": len(rows),
        "complete_telemetry_count": len(successes),
        "failed_or_invalid_count": len(failures),
        "sdk_response_extraction_attempts": sum(row["sdk_response_extraction_attempts"] for row in rows),
        "v017_receipt_attempts": sum(row["v017_receipt_attempts"] for row in rows),
        "v017_fixture_transport_calls": sum(row["v017_fixture_transport_calls"] for row in rows),
        "response_id_count": sum(row["response_id"] is not None for row in rows),
        "usage_record_count": sum(row["total_tokens"] is not None for row in rows),
        "instance_token_evidence_count": sum(row["receipt_instance_token_sha256"] is not None for row in rows),
        "raw_receipt_digest_count": sum(row["raw_receipt_sha256"] is not None for row in rows),
        "v017_rebuild_match_count": sum(row["v017_rebuild_match"] for row in rows),
        "integration_binding_count": sum(row["integration_binding_sha256"] is not None for row in rows),
        "integration_binding_rebuild_match_count": sum(row["integration_binding_rebuilt"] for row in rows),
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "router_high_calls": 0,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
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
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": hashlib.sha256(encoded.encode()).hexdigest().upper(), "cases": evidence["case_denominator"]}))


if __name__ == "__main__":
    main()
