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
STAGE = ROOT / "evals" / "meihua" / "direct_reading_v2_stability_v010"
MANIFEST = STAGE / "candidate_manifest.json"
CASES = STAGE / "frozen_cases.json"
RESULT_LEDGER = ROOT / "outputs" / "v010_stability_run_ledger.json"


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
    for row in manifest["candidate_files"]:
        path = ROOT / row["path"]
        if not path.is_file() or file_sha(path) != row["sha256"]:
            raise RuntimeError(f"CANDIDATE_FILE_MISMATCH:{row['path']}")
    return manifest


def validate_authorization(path: Path, manifest_sha256: str) -> dict[str, Any]:
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "stage_id": "DIRECT_READING_V2_STABILITY_V010",
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


def run(
    authorization_path: Path,
    *,
    provider_factory: Any = OpenAIDirectReadingProvider,
    result_path: Path = RESULT_LEDGER,
) -> dict[str, Any]:
    if result_path.exists():
        raise RuntimeError("V010_RESULT_LEDGER_ALREADY_EXISTS")
    manifest = verify_candidate_manifest()
    manifest_sha = file_sha(MANIFEST)
    validate_authorization(authorization_path, manifest_sha)
    frozen = json.loads(CASES.read_text(encoding="utf-8"))
    cases = load_frozen_cases(frozen)
    ledger: dict[str, Any] = {
        "stage_id": "DIRECT_READING_V2_STABILITY_V010",
        "candidate_manifest_sha256": manifest_sha,
        "authorized_fixed_high_attempts": 2,
        "actual_fixed_high_attempts": 0,
        "remaining_fixed_high_attempts": 2,
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
    for case in cases:
        started_row = {
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
        ledger["provider_instantiated"] = True
        ledger["cases"].append(started_row)
        ledger["status"] = "RUNNING"
        _write_json(result_path, ledger)
        try:
            provider = provider_factory()
            row = execute_case(case, provider)
        except Exception as exc:
            row = {
                "slot": case.slot,
                "case_id": case.case_id,
                "input_sha256": case.input_sha256,
                "status": "EXECUTOR_FAILED",
                "consumed": True,
                "deterministic_cast_count": None,
                "fixed_high_attempts": None,
                "provider_attempts": 0,
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
        ledger["cases"][-1] = row
        ledger["actual_fixed_high_attempts"] += int(row.get("provider_attempts") or 0)
        ledger["remaining_fixed_high_attempts"] = (
            ledger["authorized_fixed_high_attempts"] - ledger["actual_fixed_high_attempts"]
        )
        ledger["success_count"] = sum(item["status"] == "SUCCESS" for item in ledger["cases"])
        ledger["technical_success_rate"] = ledger["success_count"] / len(cases)
        ledger["status"] = "COMPLETE" if len(ledger["cases"]) == len(cases) else "STOPPED"
        _write_json(result_path, ledger)
        if row["status"] != "SUCCESS":
            ledger["status"] = "FAIL_STOP"
            _write_json(result_path, ledger)
            break
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    run(args.authorization)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
