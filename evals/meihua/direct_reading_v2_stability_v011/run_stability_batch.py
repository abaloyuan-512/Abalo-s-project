from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from abalo_iching.application.sites_direct_reading_v2 import OpenAIDirectReadingProvider
from evals.meihua.direct_reading_v2_stability_v010.stability_executor import (
    FrozenStabilityCase,
    execute_case,
    load_frozen_cases,
)


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals" / "meihua" / "direct_reading_v2_stability_v011"
MANIFEST = STAGE / "candidate_manifest.json"
CASES = ROOT / "evals" / "meihua" / "direct_reading_v2_stability_v010" / "frozen_cases.json"
RESULT_LEDGER = ROOT / "outputs" / "v011_stability_run_ledger.json"
STAGE_ID = "DIRECT_READING_V2_STABILITY_V011"
NOT_EXECUTED = "NOT_EXECUTED_DUE_TO_PRIOR_FAILURE"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_candidate_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for group in ("candidate_files", "immutable_authority_evidence"):
        for row in manifest[group]:
            path = ROOT / row["path"]
            if not path.is_file() or file_sha(path) != row["sha256"]:
                raise RuntimeError(f"CANDIDATE_FILE_MISMATCH:{row['path']}")
    return manifest


def validate_authorization(path: Path, manifest_sha256: str) -> dict[str, Any]:
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "stage_id": STAGE_ID,
        "candidate_manifest_sha256": manifest_sha256,
        "explicit_user_authorization": True,
        "authorized_fixed_high_attempts": 2,
        "router_attempts": 0,
        "automatic_retries": 0,
        "replacement_cases_allowed": False,
        "stop_on_first_failure": True,
    }
    if authorization != expected:
        raise RuntimeError("EXACT_NUMERIC_AUTHORIZATION_REQUIRED")
    return authorization


def _started_row(case: FrozenStabilityCase) -> dict[str, Any]:
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": "STARTED",
        "consumed": True,
        "deterministic_cast_count": None,
        "fixed_high_attempts": None,
        "provider_attempts": None,
        "attempt_accounting_status": "IN_FLIGHT_UNKNOWN_ON_CRASH",
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": [],
        "usage": None,
        "latency_ms": None,
        "reading_utf8_sha256": None,
        "released_direct_reading": None,
        "mechanical_mapping": None,
    }


def _not_executed_row(
    case: FrozenStabilityCase,
    first_failure: dict[str, Any],
) -> dict[str, Any]:
    failure_case_id = str(first_failure["case_id"])
    failure_status = str(first_failure["status"])
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": NOT_EXECUTED,
        "consumed": False,
        "deterministic_cast_count": 0,
        "fixed_high_attempts": 0,
        "provider_attempts": 0,
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": [],
        "usage": None,
        "usage_unavailable_reason": NOT_EXECUTED,
        "latency_ms": None,
        "latency_unavailable_reason": NOT_EXECUTED,
        "reading_utf8_sha256": None,
        "released_direct_reading": None,
        "mechanical_mapping": None,
        "prior_failure_case_id": failure_case_id,
        "prior_failure_status": failure_status,
        "not_executed_reason": f"PRIOR_FAILURE:{failure_case_id}:{failure_status}",
    }


class _ProviderConstructionFailure:
    """Convert provider construction failure into the case's sole protocol attempt."""

    def __init__(self, cause: Exception) -> None:
        self._cause = cause

    def generate(self, **_kwargs: Any) -> Any:
        raise self._cause


def _unexpected_executor_failure_row(
    case: FrozenStabilityCase,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": "EXECUTOR_FAILED",
        "consumed": True,
        "deterministic_cast_count": None,
        "fixed_high_attempts": 1,
        "provider_attempts": 1,
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": [f"EXECUTOR:{type(exc).__name__}"],
        "usage": None,
        "usage_unavailable_reason": "EXECUTOR_FAILED",
        "latency_ms": None,
        "latency_unavailable_reason": "EXECUTOR_FAILED",
        "reading_utf8_sha256": None,
        "released_direct_reading": None,
        "mechanical_mapping": None,
    }


def _finalize_accounting(
    ledger: dict[str, Any],
    cases: tuple[FrozenStabilityCase, ...],
) -> None:
    frozen_identity = [(case.slot, case.case_id, case.input_sha256) for case in cases]
    ledger_identity = [
        (int(row["slot"]), str(row["case_id"]), str(row["input_sha256"]))
        for row in ledger["cases"]
    ]
    if ledger_identity != frozen_identity:
        raise RuntimeError("FROZEN_CASE_LEDGER_IDENTITY_MISMATCH")
    actual = sum(int(row["provider_attempts"]) for row in ledger["cases"])
    consumed = sum(row["consumed"] is True for row in ledger["cases"])
    unexecuted = sum(row["status"] == NOT_EXECUTED for row in ledger["cases"])
    success_count = sum(row["status"] == "SUCCESS" for row in ledger["cases"])
    if actual != consumed or len(cases) - actual != unexecuted:
        raise RuntimeError("LEDGER_ACCOUNTING_INVARIANT")
    ledger["actual_fixed_high_attempts"] = actual
    ledger["remaining_fixed_high_attempts"] = len(cases) - actual
    ledger["success_count"] = success_count
    ledger["technical_success_rate"] = success_count / len(cases)
    ledger["not_executed_count"] = unexecuted


def run(
    authorization_path: Path,
    *,
    provider_factory: Any = OpenAIDirectReadingProvider,
    result_path: Path = RESULT_LEDGER,
) -> dict[str, Any]:
    if result_path.exists():
        raise RuntimeError("V011_RESULT_LEDGER_ALREADY_EXISTS")
    verify_candidate_manifest()
    manifest_sha = file_sha(MANIFEST)
    validate_authorization(authorization_path, manifest_sha)
    frozen = json.loads(CASES.read_text(encoding="utf-8"))
    cases = load_frozen_cases(frozen)
    ledger: dict[str, Any] = {
        "stage_id": STAGE_ID,
        "candidate_manifest_sha256": manifest_sha,
        "authorized_fixed_high_attempts": len(cases),
        "actual_fixed_high_attempts": 0,
        "remaining_fixed_high_attempts": len(cases),
        "router_attempts": 0,
        "automatic_retries": 0,
        "provider_instantiated": False,
        "failure_consumes_slot": True,
        "stop_on_first_failure": True,
        "replacement_cases_allowed": False,
        "success_denominator": len(cases),
        "cases": [],
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }
    _write_json(result_path, ledger)

    for index, case in enumerate(cases):
        ledger["provider_instantiated"] = True
        ledger["cases"].append(_started_row(case))
        ledger["status"] = "RUNNING"
        _write_json(result_path, ledger)
        try:
            provider = provider_factory()
        except Exception as exc:
            provider = _ProviderConstructionFailure(exc)
        try:
            row = execute_case(case, provider)
        except Exception as exc:
            row = _unexpected_executor_failure_row(case, exc)
        ledger["cases"][-1] = row
        if row["status"] != "SUCCESS":
            for remaining_case in cases[index + 1 :]:
                ledger["cases"].append(_not_executed_row(remaining_case, row))
            _finalize_accounting(ledger, cases)
            ledger["status"] = "FAIL_STOP"
            _write_json(result_path, ledger)
            return ledger
        _write_json(result_path, ledger)

    _finalize_accounting(ledger, cases)
    ledger["status"] = "COMPLETE"
    _write_json(result_path, ledger)
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    run(args.authorization)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
