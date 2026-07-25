"""Run the one authorized Gate 2 Stage C.1 background retest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching.personalization_gate2.background_checkpoint import (
    Gate2BackgroundCheckpointWriter,
)
from abalo_iching.personalization_gate2.background_provider import (
    OpenAIGate2BackgroundProvider,
)
from abalo_iching.personalization_gate2.background_runner import (
    Gate2BackgroundCalibrationRunner,
)
from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    CALIBRATION_SET_VERSION,
    VISIBLE_CALIBRATION_CASES,
)
from abalo_iching.personalization_gate2.calibration_prompt_builder import (
    Gate2CalibrationPromptBuilder,
)
from abalo_iching.personalization_gate2.models import ExperimentArm
from abalo_iching.personalization_gate2.stage_c1 import (
    PAID_RETEST_AUTHORIZATION_CONSUMED,
    build_stage_c1_request,
)
from scripts.run_personalization_gate2_stage_c import (
    _json_bytes,
    _validate_output_root,
    _write_new_json,
)


STAGE_C1_RETEST_VERSION = "personalization_gate2_stage_c1_paid_retest_v1"
DECLARED_BALANCE_USD = Decimal("8.85")
REQUIRED_RESERVE_USD = Decimal("7")
AUTHORIZED_SPEND_USD = Decimal("0.45")
EXPECTED_GENERATION_CALLS = 1
AUTHORIZED_CASE_ID = "G2CAL-001"
AUTHORIZED_ARM = ExperimentArm.B


def validate_paid_retest_preflight(
    *,
    output_root: Path,
    confirmed: bool,
    generation_calls: int | None,
    usable_budget_usd: Decimal | None,
    declared_balance_usd: Decimal | None,
    required_reserve_usd: Decimal | None,
    api_key_present: bool,
    authorization_consumed: bool,
) -> Path:
    """Reject any invocation that differs from the one narrow authorization."""

    if authorization_consumed:
        raise SystemExit("STAGE_C1_PAID_RETEST_AUTHORIZATION_ALREADY_CONSUMED")
    if not confirmed:
        raise SystemExit("STAGE_C1_PAID_RETEST_EXPLICIT_CONFIRMATION_REQUIRED")
    if generation_calls != EXPECTED_GENERATION_CALLS:
        raise SystemExit("GENERATION_CALL_LIMIT_CONFIRMATION_MISMATCH")
    if usable_budget_usd != AUTHORIZED_SPEND_USD:
        raise SystemExit("USABLE_BUDGET_CONFIRMATION_MISMATCH")
    if declared_balance_usd != DECLARED_BALANCE_USD:
        raise SystemExit("DECLARED_BALANCE_CONFIRMATION_MISMATCH")
    if required_reserve_usd != REQUIRED_RESERVE_USD:
        raise SystemExit("REQUIRED_RESERVE_CONFIRMATION_MISMATCH")
    if not api_key_present:
        raise SystemExit("OPENAI_API_KEY_NOT_CONFIGURED")
    Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=DECLARED_BALANCE_USD,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    return _validate_output_root(output_root)


def run(
    output_root: Path,
    *,
    provider_factory: Callable[..., Any] = OpenAIGate2BackgroundProvider,
    runner_factory: Callable[..., Any] = Gate2BackgroundCalibrationRunner,
) -> dict[str, object]:
    output_root = _validate_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=False)

    case = VISIBLE_CALIBRATION_CASES[0]
    if case.case_id != AUTHORIZED_CASE_ID:
        raise RuntimeError("VISIBLE_CALIBRATION_CASE_ORDER_CHANGED")
    request = build_stage_c1_request(case, AUTHORIZED_ARM)
    input_payload = request.model_dump(mode="json")
    input_bytes = _json_bytes(input_payload)

    checkpoint_writer = Gate2BackgroundCheckpointWriter(
        repository_root=ROOT,
        output_root=output_root,
        case_id=case.case_id,
        arm=AUTHORIZED_ARM,
    )
    provider = provider_factory(on_checkpoint=checkpoint_writer.write)
    prompt = Gate2CalibrationPromptBuilder().build(request)
    estimated_cost = provider.pricing.conservative_preflight_estimate(
        prompt,
        max_output_tokens=provider.max_output_tokens,
    )
    if estimated_cost > AUTHORIZED_SPEND_USD:
        raise RuntimeError("STAGE_C1_CONSERVATIVE_ESTIMATE_EXCEEDS_AUTHORIZATION")

    _write_new_json(
        output_root / "run_manifest.json",
        {
            "stage_c1_retest_version": STAGE_C1_RETEST_VERSION,
            "calibration_set_version": CALIBRATION_SET_VERSION,
            "case_id": case.case_id,
            "arm": AUTHORIZED_ARM.value,
            "request_sha256": hashlib.sha256(input_bytes).hexdigest(),
            "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
            "automatic_model_repair_calls": 0,
            "declared_account_balance_usd": str(DECLARED_BALANCE_USD),
            "required_reserve_usd": str(REQUIRED_RESERVE_USD),
            "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
            "conservative_preflight_estimate_usd": str(estimated_cost),
            "background_mode": True,
            "store": False,
            "locked_payload_included": False,
            "stage_d_authorized": False,
        },
    )
    _write_new_json(output_root / "visible_calibration_input.json", input_payload)

    budget = Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=DECLARED_BALANCE_USD,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    result = runner_factory(
        repository_root=ROOT,
        budget_guard=budget,
    ).run(
        request,
        provider=provider,
        evidence_root=output_root,
    )
    record = result.evidence_record
    if provider.call_count > EXPECTED_GENERATION_CALLS:
        raise RuntimeError("GENERATION_CALL_LIMIT_EXCEEDED")

    summary = {
        "status": result.status.value,
        "stage_c1_retest_version": STAGE_C1_RETEST_VERSION,
        "case_id": case.case_id,
        "arm": AUTHORIZED_ARM.value,
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "max_output_tokens": provider.max_output_tokens,
        "generation_calls": provider.call_count,
        "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
        "poll_count": provider.poll_count,
        "automatic_model_repair_calls": 0,
        "cost_usd": record.cost_usd,
        "cost_status": (
            "UNKNOWN_NO_USAGE_OBJECT"
            if record.cost_usd is None
            else "CALCULATED_FROM_API_USAGE"
        ),
        "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
        "required_reserve_usd": str(REQUIRED_RESERVE_USD),
        "conservative_preflight_estimate_usd": str(estimated_cost),
        "response_id": record.response_id,
        "api_status": record.api_status,
        "incomplete_reason": record.incomplete_reason,
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
        "checkpoint_directory": str(checkpoint_writer.directory),
    }
    _write_new_json(output_root / "summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-stage-c1-paid-retest", action="store_true")
    parser.add_argument("--confirm-generation-calls", type=int)
    parser.add_argument("--confirm-usable-budget-usd", type=Decimal)
    parser.add_argument("--confirm-declared-balance-usd", type=Decimal)
    parser.add_argument("--confirm-required-reserve-usd", type=Decimal)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_root = validate_paid_retest_preflight(
        output_root=args.output_dir,
        confirmed=args.confirm_stage_c1_paid_retest,
        generation_calls=args.confirm_generation_calls,
        usable_budget_usd=args.confirm_usable_budget_usd,
        declared_balance_usd=args.confirm_declared_balance_usd,
        required_reserve_usd=args.confirm_required_reserve_usd,
        api_key_present=bool(os.getenv("OPENAI_API_KEY")),
        authorization_consumed=PAID_RETEST_AUTHORIZATION_CONSUMED,
    )
    print(json.dumps(run(output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
