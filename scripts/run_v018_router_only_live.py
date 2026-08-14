from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from openai import OpenAI

from abalo_iching.application.sites_light_router_adapter_v015 import (
    MAX_OUTPUT_TOKENS,
    TIMEOUT_SECONDS,
    build_openai_request,
)
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import (
    rebuild_atomic_cost_estimate_usd,
    rebuild_atomic_receipt_sha256,
)
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import (
    SDKResponseSnapshot,
    bridge_sdk_response_to_v017,
    rebuild_integration_binding_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "evals/meihua/direct_reading_v2_light_router_sdk_bridge_v018"
MANIFEST = STAGE / "candidate_manifest.json"
CASE = STAGE / "live_case.json"
AUTH = STAGE / "live_authorization.json"
LEDGER = ROOT / "outputs/v018_router_only_live_ledger.json"
EXPECTED_MANIFEST_SHA = "30C1E24EB0675B7FC5091431AA1599CBAD9D0A14314713CDCDC812956D432109"
EXPECTED_CASE_SHA = "8B850B26C9A48E15C23469E0EFAF95040D63C2A4EB0518F74EA04CD6FF789AD4"
EXPECTED_AUTH_SHA = "0A059DCC6735239C640E8DB0B521C9F06FC6E6A9190A60A83C0F2F4571733336"


def sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def atomic_write(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary = LEDGER.with_suffix(".json.tmp")
    temporary.write_text(encoded, encoding="utf-8", newline="\n")
    temporary.replace(LEDGER)


def guarded_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if LEDGER.exists():
        raise RuntimeError("LIVE_LEDGER_ALREADY_EXISTS")
    if sha_bytes(MANIFEST) != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("MANIFEST_SHA_MISMATCH")
    if sha_bytes(CASE) != EXPECTED_CASE_SHA:
        raise RuntimeError("CASE_SHA_MISMATCH")
    if sha_bytes(AUTH) != EXPECTED_AUTH_SHA:
        raise RuntimeError("AUTH_SHA_MISMATCH")
    case = json.loads(CASE.read_text(encoding="utf-8"))
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    if auth != {
        "authorization_id": "V018_ROUTER_ONLY_LIVE_AUTH_2026_08_14",
        "candidate_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "authorized_router_only_calls": 1,
        "authorized_cost_cap_usd": None,
        "reuse_existing_api_key": True,
        "automatic_retries": 0,
        "high_calls": 0,
        "prepare_calls": 0,
        "cast_calls": 0,
        "process_calls": 0,
        "replacement_cases": False,
        "stop_after_terminal_result": True,
        "product_wiring": False,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }:
        raise RuntimeError("AUTHORIZATION_CONTRACT_MISMATCH")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY_MISSING")
    return case, auth


def initial_ledger(case: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    request = case["request"]
    question_sha = hashlib.sha256(request["original_question"].encode()).hexdigest().upper()
    return {
        "stage_id": "DIRECT_READING_V2_LIGHT_ROUTER_SDK_BRIDGE_V018_LIVE",
        "status": "STARTED",
        "candidate_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "live_case_sha256": EXPECTED_CASE_SHA,
        "live_authorization_sha256": EXPECTED_AUTH_SHA,
        "authorization": auth,
        "denominator": 1,
        "authorized_router_only_calls": 1,
        "actual_provider_attempts": 0,
        "real_router_live_calls": 0,
        "remaining_router_only_calls": 1,
        "success_count": 0,
        "failed_count": 0,
        "usage_record_count": 0,
        "response_id_count": 0,
        "v017_receipt_count": 0,
        "integration_binding_count": 0,
        "automatic_retries": 0,
        "high_calls": 0,
        "prepare_calls": 0,
        "cast_calls": 0,
        "process_calls": 0,
        "v014_consumption_calls": 0,
        "cases": [{
            "case_id": case["case_id"],
            "input_question_sha256": question_sha,
            "ambiguity_kind": request["critical_ambiguity"]["kind"],
            "expected_outcome": case["expected_outcome"],
            "terminal_status": "IN_FLIGHT_UNKNOWN",
            "provider_kind": "OPENAI",
            "provider_attempts": None,
            "router_live_calls": None,
            "real_provider_instantiated": None,
            "call_may_have_been_sent": False,
            "response_id": None,
            "provider_model": None,
            "provider_status": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "actual_cost_estimate_usd": None,
            "cost_estimate_mode": None,
            "input_usd_per_million": None,
            "output_usd_per_million": None,
            "rate_snapshot_sha256": None,
            "rate_source": None,
            "cost_rounding": None,
            "cost_precision_usd": None,
            "cost_estimate_rebuilt": False,
            "outcome": None,
            "question_sha_before": None,
            "question_sha_sent": None,
            "question_sha_after": None,
            "original_question_preserved": False,
            "sdk_response_extraction_attempts": 0,
            "v017_receipt_attempts": 0,
            "v017_fixture_fetches": 0,
            "sdk_response_local_instance_sha256": None,
            "v017_request_binding_sha256": None,
            "v017_instance_token_sha256": None,
            "raw_decision_payload_sha256": None,
            "normalized_decision_sha256": None,
            "raw_receipt_sha256": None,
            "v017_receipt_rebuilt": False,
            "integration_binding_sha256": None,
            "integration_binding_rebuilt": False,
            "canonical_round_trip": False,
            "failure_code": None,
            "latency_ms": None,
        }],
        "product_wiring": False,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def main() -> int:
    case, auth = guarded_inputs()
    ledger = initial_ledger(case, auth)
    atomic_write(ledger)
    row = ledger["cases"][0]
    client: OpenAI | None = None
    started = perf_counter()
    try:
        client = OpenAI(timeout=TIMEOUT_SECONDS, max_retries=0)
        row["real_provider_instantiated"] = True
        row["call_may_have_been_sent"] = True
        row["provider_attempts"] = 1
        row["router_live_calls"] = 1
        ledger["actual_provider_attempts"] = 1
        ledger["real_router_live_calls"] = 1
        ledger["remaining_router_only_calls"] = 0
        atomic_write(ledger)
        response = client.responses.parse(**build_openai_request(case["request"]))
        snapshot = SDKResponseSnapshot(response)
        outcome, bridge = bridge_sdk_response_to_v017(
            case_id=case["case_id"], request_payload=case["request"], sdk_response=snapshot
        )
        v017 = bridge["v017_audit"]
        rebuilt_receipt = bool(v017 and rebuild_atomic_receipt_sha256(v017) == v017["raw_receipt_sha256"])
        rebuilt_binding = rebuild_integration_binding_sha256(bridge) == bridge["integration_binding_sha256"]
        rebuilt_cost = rebuild_atomic_cost_estimate_usd(v017)
        cost_match = rebuilt_cost == v017["actual_cost_estimate_usd"]
        row.update({
            "terminal_status": "SUCCESS" if outcome == case["expected_outcome"] and bridge["terminal_status"] == "TELEMETRY_COMPLETE" and rebuilt_receipt and rebuilt_binding and cost_match else "FAIL_STOP",
            "call_may_have_been_sent": True,
            "response_id": v017["response_id"],
            "provider_model": v017["provider_model"],
            "provider_status": v017["provider_status"],
            "input_tokens": v017["input_tokens"],
            "output_tokens": v017["output_tokens"],
            "total_tokens": v017["total_tokens"],
            "actual_cost_estimate_usd": rebuilt_cost,
            "cost_estimate_mode": "INTERNAL_CONSERVATIVE_ESTIMATE_NOT_API_INVOICE",
            "input_usd_per_million": v017["input_usd_per_million"],
            "output_usd_per_million": v017["output_usd_per_million"],
            "rate_snapshot_sha256": v017["rate_snapshot_sha256"],
            "rate_source": v017["rate_source"],
            "cost_rounding": v017["cost_rounding"],
            "cost_precision_usd": v017["cost_precision_usd"],
            "cost_estimate_rebuilt": cost_match,
            "outcome": outcome,
            "question_sha_before": v017["question_sha_before"],
            "question_sha_sent": v017["question_sha_sent"],
            "question_sha_after": v017["question_sha_after"],
            "original_question_preserved": v017["original_question_preserved"],
            "sdk_response_extraction_attempts": bridge["sdk_response_extraction_attempts"],
            "v017_receipt_attempts": bridge["v017_receipt_attempts"],
            "v017_fixture_fetches": v017["fixture_transport_calls"],
            "sdk_response_local_instance_sha256": bridge["sdk_response_local_instance_sha256"],
            "v017_request_binding_sha256": v017["request_binding_sha256"],
            "v017_instance_token_sha256": v017["receipt_instance_token_sha256"],
            "raw_decision_payload_sha256": v017["raw_decision_payload_sha256"],
            "normalized_decision_sha256": v017["normalized_decision_sha256"],
            "raw_receipt_sha256": v017["raw_receipt_sha256"],
            "v017_receipt_rebuilt": rebuilt_receipt,
            "integration_binding_sha256": bridge["integration_binding_sha256"],
            "integration_binding_rebuilt": rebuilt_binding,
            "canonical_round_trip": v017["canonical_round_trip"],
            "latency_ms": max(0, int((perf_counter() - started) * 1000)),
        })
        success = row["terminal_status"] == "SUCCESS"
        ledger.update({
            "status": "SUCCESS" if success else "FAIL_STOP",
            "success_count": 1 if success else 0,
            "failed_count": 0 if success else 1,
            "usage_record_count": 1 if v017["total_tokens"] is not None else 0,
            "response_id_count": 1 if v017["response_id"] else 0,
            "v017_receipt_count": 1 if v017["raw_receipt_sha256"] else 0,
            "integration_binding_count": 1 if bridge["integration_binding_sha256"] else 0,
        })
    except BaseException as exc:
        row.update({
            "terminal_status": "TERMINAL_UNKNOWN" if row["call_may_have_been_sent"] else "FAIL_STOP",
            "failure_code": "LIVE_EXECUTION_FAILED",
            "latency_ms": max(0, int((perf_counter() - started) * 1000)),
        })
        ledger["status"] = "FAIL_STOP"
        ledger["failed_count"] = 1
    finally:
        atomic_write(ledger)
    return 0 if ledger["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
