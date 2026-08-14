from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_light_router_adapter_v015 import (
    MODEL,
    OpenAILightRouterAdapter,
)


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals/meihua/direct_reading_v2_light_router_adapter_v015"
CASES_PATH = EVAL_DIR / "live_cases.json"
AUTH_PATH = EVAL_DIR / "live_authorization.json"
MANIFEST_PATH = EVAL_DIR / "candidate_manifest.json"
LEDGER_PATH = ROOT / "outputs/v015_router_only_live_ledger.json"
EXPECTED_MANIFEST_SHA = "D88700084FBE154AFE7F4BB307D45C1015302C26C43645986B1D9AD4F40CD49F"
EXPECTED_CASES_SHA = "011B96383E3D568E3A134C2D25A4F41CE244095AB5CE21C07DAD38E705CB5D5C"
EXPECTED_AUTH_SHA = "15AD0298ABBA6AED5A148534C5DADD12807C9685E086BB868EF5005F321F8764"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_write(value: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = LEDGER_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(LEDGER_PATH)


def _load_and_guard() -> tuple[dict[str, Any], dict[str, Any]]:
    if LEDGER_PATH.exists():
        raise RuntimeError("V015_LIVE_LEDGER_ALREADY_EXISTS")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
    if _sha_bytes(MANIFEST_PATH.read_bytes()) != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("V015_CANDIDATE_MANIFEST_MISMATCH")
    if _sha_bytes(CASES_PATH.read_bytes()) != EXPECTED_CASES_SHA:
        raise RuntimeError("V015_LIVE_CASES_MISMATCH")
    if _sha_bytes(AUTH_PATH.read_bytes()) != EXPECTED_AUTH_SHA:
        raise RuntimeError("V015_LIVE_AUTHORIZATION_MISMATCH")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for group in ("candidate_files", "immutable_authority_evidence"):
        for item in manifest[group]:
            if _sha_bytes((ROOT / item["path"]).read_bytes()) != item["sha256"]:
                raise RuntimeError(f"V015_LOCKED_FILE_MISMATCH:{item['path']}")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    if cases["case_order"] != [item["case_id"] for item in cases["cases"]] or len(cases["cases"]) != 2:
        raise RuntimeError("V015_CASE_IDENTITY_MISMATCH")
    if (
        auth["authorized_router_only_calls"] != 2
        or Decimal(auth["authorized_cost_usd"]) != Decimal("0.05")
        or auth["model"] != MODEL
        or auth["max_output_tokens_per_call"] != 128
        or auth["sdk_max_retries"] != 0
        or not auth["stop_on_first_failure"]
        or auth["replacement_cases"]
        or any(auth[field] != 0 for field in ("high_calls", "prepare_calls", "cast_calls", "process_calls"))
    ):
        raise RuntimeError("V015_AUTHORIZATION_MISMATCH")
    if Decimal(auth["pricing"]["conservative_batch_cost_usd"]) > Decimal(auth["authorized_cost_usd"]):
        raise RuntimeError("V015_CONSERVATIVE_COST_EXCEEDS_AUTHORIZATION")
    if Decimal(auth["pricing"]["conservative_batch_cost_usd"]) != Decimal(auth["pricing"]["conservative_cost_per_call_usd"]) * 2:
        raise RuntimeError("V015_CONSERVATIVE_COST_ACCOUNTING_MISMATCH")
    return cases, auth


def _empty_row(case: dict[str, Any]) -> dict[str, Any]:
    question_sha = _sha_text(case["original_question"])
    return {
        "slot": case["slot"],
        "case_id": case["case_id"],
        "original_question_sha256": question_sha,
        "critical_ambiguity_kind": case["critical_ambiguity"]["kind"],
        "expected_outcome": case["expected_outcome"],
        "status": "NOT_STARTED",
        "consumed": False,
        "provider_kind": None,
        "provider_attempts": 0,
        "router_live_calls": 0,
        "real_provider_instantiated": False,
        "model": MODEL,
        "response_id": None,
        "response_id_reason": "V015 adapter audit does not expose API response id",
        "normalized_decision_sha256": None,
        "normalized_decision_sha_semantics": "SHA-256 of strict normalized decision; not an API receipt digest",
        "outcome_sha256": None,
        "actual_outcome": None,
        "question_sha_before": None,
        "question_sha_sent": None,
        "question_sha_after": None,
        "original_question_preserved": None,
        "canonical_round_trip": None,
        "actual_input_tokens": None,
        "actual_output_tokens": None,
        "actual_total_tokens": None,
        "actual_cost_usd": None,
        "actual_usage_reason": "V015 adapter audit does not expose provider usage",
        "conservative_charged_cost_usd": "0.000000",
        "latency_ms": None,
        "failure_code": None,
        "not_executed_reason": None,
        "attempt_state": "NOT_STARTED",
        "call_may_have_been_sent": False,
        "router_prepare_calls": 0,
        "router_cast_count": 0,
        "router_process_calls": 0,
        "router_high_calls": 0,
        "automatic_retries": 0,
    }


def _totals(ledger: dict[str, Any]) -> None:
    rows = ledger["cases"]
    ledger.update(
        {
            "actual_provider_attempts": (
                None
                if any(row["provider_attempts"] is None for row in rows)
                else sum(int(row["provider_attempts"]) for row in rows)
            ),
            "actual_router_live_calls": (
                None
                if any(row["router_live_calls"] is None for row in rows)
                else sum(int(row["router_live_calls"]) for row in rows)
            ),
            "normalized_decision_digest_count": sum(bool(row["normalized_decision_sha256"]) for row in rows),
            "usage_record_count": sum(row["actual_total_tokens"] is not None for row in rows),
            "success_count": sum(row["status"] == "SUCCESS" for row in rows),
            "failed_count": sum(row["status"] == "FAILED" for row in rows),
            "not_executed_count": sum(row["status"] == "NOT_EXECUTED_DUE_TO_PRIOR_FAILURE" for row in rows),
            "conservative_total_cost_usd": str(
                sum(Decimal(row["conservative_charged_cost_usd"]) for row in rows)
            ),
            "high_calls": 0,
            "prepare_calls": 0,
            "cast_calls": 0,
            "process_calls": 0,
            "automatic_retries": 0,
        }
    )


def run() -> dict[str, Any]:
    cases_doc, auth = _load_and_guard()
    per_call_bound = Decimal(auth["pricing"]["conservative_cost_per_call_usd"])
    authorized_cost = Decimal(auth["authorized_cost_usd"])
    ledger: dict[str, Any] = {
        "stage_id": cases_doc["stage_id"],
        "contract_id": "DRV2-EXTERNAL-LIGHT-ROUTER-ADAPTER-V015-ROUTER-ONLY-LIVE-ACCEPTANCE-V1",
        "status": "STARTED",
        "candidate_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "live_cases_sha256": _sha_bytes(CASES_PATH.read_bytes()),
        "live_authorization_sha256": _sha_bytes(AUTH_PATH.read_bytes()),
        "authorized_router_only_calls": 2,
        "authorized_cost_usd": "0.05",
        "pricing_source": auth["pricing"]["source"],
        "pricing_checked_date": auth["pricing"]["checked_date"],
        "conservative_cost_per_call_usd": str(per_call_bound),
        "case_denominator": 2,
        "model": MODEL,
        "cases": [_empty_row(case) for case in cases_doc["cases"]],
        "stop_reason": None,
        "deployment": False,
        "production": False,
        "default_replacement": False,
        "product_wiring": False,
    }
    _totals(ledger)
    _atomic_write(ledger)

    prior_failure: tuple[str, str] | None = None
    for index, case in enumerate(cases_doc["cases"]):
        row = ledger["cases"][index]
        if prior_failure is not None:
            row.update(
                {
                    "status": "NOT_EXECUTED_DUE_TO_PRIOR_FAILURE",
                    "not_executed_reason": f"PRIOR_FAILURE:{prior_failure[0]}:{prior_failure[1]}",
                }
            )
            continue
        projected = Decimal(ledger["conservative_total_cost_usd"]) + per_call_bound
        if projected > authorized_cost:
            row.update(
                {
                    "status": "FAILED",
                    "failure_code": "COST_BOUND_EXCEEDED_BEFORE_CALL",
                    "not_executed_reason": "CALL_NOT_SENT",
                }
            )
            prior_failure = (row["case_id"], row["failure_code"])
            continue
        row.update(
            {
                "status": "STARTED",
                "consumed": True,
                "attempt_state": "IN_FLIGHT_UNKNOWN",
                "provider_attempts": None,
                "router_live_calls": None,
                "real_provider_instantiated": None,
                "call_may_have_been_sent": True,
            }
        )
        _totals(ledger)
        _atomic_write(ledger)
        try:
            outcome, audit = OpenAILightRouterAdapter().route_once(
                {
                    "original_question": case["original_question"],
                    "critical_ambiguity": case["critical_ambiguity"],
                }
            )
            row.update(
                {
                    "provider_kind": audit["provider_kind"],
                    "provider_attempts": audit["provider_attempts"],
                    "router_live_calls": audit["router_live_calls"],
                    "real_provider_instantiated": audit["real_provider_instantiated"],
                    "normalized_decision_sha256": audit["raw_receipt_sha256"],
                    "outcome_sha256": audit["outcome_sha256"],
                    "actual_outcome": outcome,
                    "question_sha_before": audit["question_sha_before"],
                    "question_sha_sent": audit["question_sha_sent"],
                    "question_sha_after": audit["question_sha_after"],
                    "original_question_preserved": audit["original_question_preserved"],
                    "canonical_round_trip": audit["canonical_round_trip"],
                    "latency_ms": audit["latency_ms"],
                    "failure_code": audit["normalized_failure_code"],
                    "router_prepare_calls": audit["router_prepare_calls"],
                    "router_cast_count": audit["router_cast_count"],
                    "router_process_calls": audit["router_process_calls"],
                    "router_high_calls": audit["router_high_calls"],
                    "automatic_retries": audit["automatic_retries"],
                    "conservative_charged_cost_usd": str(per_call_bound),
                    "attempt_state": "TERMINAL_KNOWN",
                    "call_may_have_been_sent": bool(audit["router_live_calls"]),
                }
            )
            expected = case["expected_outcome"]
            reasons: list[str] = []
            if outcome != expected:
                reasons.append("EXPECTED_OUTCOME_MISMATCH")
            if audit["provider_kind"] != "OPENAI" or not audit["real_provider_instantiated"]:
                reasons.append("REAL_PROVIDER_NOT_PROVEN")
            if audit["provider_attempts"] != 1 or audit["router_live_calls"] != 1:
                reasons.append("LIVE_ATTEMPT_INVARIANT")
            if not audit["raw_receipt_sha256"]:
                reasons.append("NORMALIZED_DECISION_DIGEST_MISSING")
            if not (
                audit["question_sha_before"]
                == audit["question_sha_sent"]
                == audit["question_sha_after"]
                == row["original_question_sha256"]
            ):
                reasons.append("QUESTION_SHA_MISMATCH")
            if not audit["canonical_round_trip"]:
                reasons.append("CANONICAL_ROUND_TRIP_FAILED")
            if any(audit[field] != 0 for field in ("router_prepare_calls", "router_cast_count", "router_process_calls", "router_high_calls", "automatic_retries")):
                reasons.append("ROUTER_ONLY_BOUNDARY_VIOLATION")
            if reasons:
                row.update({"status": "FAILED", "failure_code": "+".join(reasons)})
                prior_failure = (row["case_id"], row["failure_code"])
            else:
                row.update({"status": "SUCCESS", "failure_code": None})
        except BaseException as exc:
            row.update(
                {
                    "status": "FAILED",
                    "provider_attempts": None,
                    "router_live_calls": None,
                    "real_provider_instantiated": None,
                    "failure_code": f"UNEXPECTED_RUNNER_FAILURE:{type(exc).__name__}",
                    "conservative_charged_cost_usd": str(per_call_bound),
                    "attempt_state": "TERMINAL_UNKNOWN",
                    "call_may_have_been_sent": True,
                }
            )
            prior_failure = (row["case_id"], row["failure_code"])
        _totals(ledger)
        _atomic_write(ledger)

    if prior_failure is not None:
        for row in ledger["cases"]:
            if row["status"] == "NOT_STARTED":
                row.update(
                    {
                        "status": "NOT_EXECUTED_DUE_TO_PRIOR_FAILURE",
                        "not_executed_reason": f"PRIOR_FAILURE:{prior_failure[0]}:{prior_failure[1]}",
                    }
                )
        ledger["status"] = "FAIL_STOP"
        ledger["stop_reason"] = f"PRIOR_FAILURE:{prior_failure[0]}:{prior_failure[1]}"
    else:
        ledger["status"] = "SUCCESS" if all(row["status"] == "SUCCESS" for row in ledger["cases"]) else "FAIL_STOP"
    _totals(ledger)
    _atomic_write(ledger)
    return ledger


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "status": result["status"],
                "actual_router_live_calls": result["actual_router_live_calls"],
                "success_count": result["success_count"],
                "case_denominator": result["case_denominator"],
                "conservative_total_cost_usd": result["conservative_total_cost_usd"],
                "ledger_sha256": _sha_bytes(LEDGER_PATH.read_bytes()),
            },
            ensure_ascii=False,
        )
    )
