"""Run exactly one authorized Gate 2 Stage C diagnostic retry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    CALIBRATION_SET_VERSION,
    VISIBLE_CALIBRATION_CASES,
    build_request,
)
from abalo_iching.personalization_gate2.live_provider import OpenAIGate2Provider
from abalo_iching.personalization_gate2.live_runner import Gate2CalibrationRunner
from abalo_iching.personalization_gate2.models import ExperimentArm
from scripts.run_personalization_gate2_stage_c import (
    _json_bytes,
    _validate_output_root,
    _write_new_json,
)


DIAGNOSTIC_RETRY_VERSION = "personalization_gate2_stage_c_diagnostic_retry_v1"
DECLARED_BALANCE_USD = Decimal("9")
REQUIRED_RESERVE_USD = Decimal("7")
AUTHORIZED_SPEND_USD = Decimal("0.35")
EXPECTED_GENERATION_CALLS = 1


def run(output_root: Path) -> dict[str, object]:
    output_root = _validate_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=False)

    case = VISIBLE_CALIBRATION_CASES[0]
    request = build_request(case, ExperimentArm.B)
    input_payload = request.model_dump(mode="json")
    input_bytes = _json_bytes(input_payload)
    _write_new_json(
        output_root / "run_manifest.json",
        {
            "diagnostic_retry_version": DIAGNOSTIC_RETRY_VERSION,
            "calibration_set_version": CALIBRATION_SET_VERSION,
            "case_id": case.case_id,
            "arm": ExperimentArm.B.value,
            "request_sha256": hashlib.sha256(input_bytes).hexdigest(),
            "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
            "automatic_model_repair_calls": 0,
            "declared_account_balance_usd": str(DECLARED_BALANCE_USD),
            "required_reserve_usd": str(REQUIRED_RESERVE_USD),
            "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
            "locked_payload_included": False,
            "original_failed_run": "gate2_personalization_stage_c_v001_20260721",
        },
    )
    _write_new_json(output_root / "visible_calibration_input.json", input_payload)

    budget = Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=DECLARED_BALANCE_USD,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    provider = OpenAIGate2Provider()
    result = Gate2CalibrationRunner(
        repository_root=ROOT,
        budget_guard=budget,
    ).run(
        request,
        provider=provider,
        evidence_root=output_root,
    )
    record = result.evidence_record
    summary = {
        "status": result.status.value,
        "diagnostic_retry_version": DIAGNOSTIC_RETRY_VERSION,
        "case_id": case.case_id,
        "arm": ExperimentArm.B.value,
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "max_output_tokens": provider.max_output_tokens,
        "generation_calls": provider.call_count,
        "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
        "automatic_model_repair_calls": 0,
        "cost_usd": record.cost_usd,
        "cost_status": (
            "UNKNOWN_NO_USAGE_OBJECT"
            if record.cost_usd is None
            else "CALCULATED_FROM_API_USAGE"
        ),
        "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
        "required_reserve_usd": str(REQUIRED_RESERVE_USD),
        "response_id": record.response_id,
        "usage": record.usage.model_dump(mode="json"),
        "hard_failures": [
            item.model_dump(mode="json") for item in result.validation.hard_failures
        ],
        "quality_failures": [
            item.model_dump(mode="json")
            for item in result.validation.quality_failures
        ],
        "first_raw_output_present": record.first_raw_output is not None,
        "locked_test_set_used": False,
        "formal_product_changed": False,
        "stage_d_entered": False,
        "evidence_directory": result.evidence_directory,
    }
    _write_new_json(output_root / "summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-diagnostic-retry", action="store_true")
    parser.add_argument("--confirm-generation-calls", type=int)
    parser.add_argument("--confirm-usable-budget-usd", type=Decimal)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.confirm_diagnostic_retry:
        raise SystemExit("DIAGNOSTIC_RETRY_EXPLICIT_CONFIRMATION_REQUIRED")
    if args.confirm_generation_calls != EXPECTED_GENERATION_CALLS:
        raise SystemExit("GENERATION_CALL_LIMIT_CONFIRMATION_MISMATCH")
    if args.confirm_usable_budget_usd != AUTHORIZED_SPEND_USD:
        raise SystemExit("USABLE_BUDGET_CONFIRMATION_MISMATCH")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY_NOT_CONFIGURED")
    print(json.dumps(run(args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
