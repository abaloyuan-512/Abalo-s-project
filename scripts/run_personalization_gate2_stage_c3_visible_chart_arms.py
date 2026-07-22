"""Prepare the Gate 2 C.3 visible C/D run; live use stays disabled by default."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal
from importlib.metadata import version
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
from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    CALIBRATION_SET_VERSION,
    VISIBLE_CALIBRATION_CASES,
)
from abalo_iching.personalization_gate2.models import DryRunStatus, ExperimentArm
from abalo_iching.personalization_gate2.pricing import Gate2TokenPricing
from abalo_iching.personalization_gate2.stage_c2_contract import (
    STAGE_C2_PROMPT_VERSION,
    STAGE_C2_RETEST_MAX_OUTPUT_TOKENS,
    STAGE_C2_RETEST_REASONING_EFFORT,
    STAGE_C2_SCHEMA_VERSION,
    STAGE_C2_VALIDATOR_VERSION,
    Gate2StageC2PromptBuilder,
    build_stage_c2_retest_request,
)
from abalo_iching.personalization_gate2.stage_c2_execution import (
    Gate2StageC2BackgroundRunner,
    OpenAIGate2StageC2BackgroundProvider,
)
from scripts.run_personalization_gate2_stage_c import (
    _json_bytes,
    _validate_output_root,
    _write_new_json,
)


STAGE_C3_RUN_VERSION = "personalization_gate2_stage_c3_visible_chart_arms_v1"
AUTHORIZED_SPEND_USD = Decimal("1.00")
REQUIRED_RESERVE_USD = Decimal("7")
MINIMUM_DECLARED_BALANCE_USD = AUTHORIZED_SPEND_USD + REQUIRED_RESERVE_USD
EXPECTED_GENERATION_CALLS = 2
AUTHORIZED_CASE_ID = "G2CAL-001"
AUTHORIZED_ARMS = (ExperimentArm.C, ExperimentArm.D)
PAID_VISIBLE_CHART_ARMS_AUTHORIZED = True
PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_CONSUMED = True
EXPECTED_OPENAI_SDK_VERSION = "2.46.0"


def write_root_evidence_manifest(output_root: Path) -> Path:
    manifest_path = output_root / "evidence_manifest.json"
    files: dict[str, dict[str, object]] = {}
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        payload = path.read_bytes()
        files[path.relative_to(output_root).as_posix()] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    _write_new_json(
        manifest_path,
        {
            "package_version": "personalization_gate2_stage_c3_root_evidence_v1",
            "files": files,
        },
    )
    return manifest_path


def validate_paid_preflight(
    *,
    output_root: Path,
    confirmed: bool,
    generation_calls: int | None,
    usable_budget_usd: Decimal | None,
    declared_balance_usd: Decimal | None,
    required_reserve_usd: Decimal | None,
    openai_sdk_version: str,
    api_key_present: bool | Callable[[], bool],
    authorized: bool,
    authorization_consumed: bool,
) -> Path:
    if not authorized:
        raise SystemExit("STAGE_C3_PAID_VISIBLE_CHART_ARMS_NOT_AUTHORIZED")
    if authorization_consumed:
        raise SystemExit("STAGE_C3_PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_ALREADY_CONSUMED")
    if not confirmed:
        raise SystemExit("STAGE_C3_EXPLICIT_CONFIRMATION_REQUIRED")
    if generation_calls != EXPECTED_GENERATION_CALLS:
        raise SystemExit("GENERATION_CALL_LIMIT_CONFIRMATION_MISMATCH")
    if usable_budget_usd != AUTHORIZED_SPEND_USD:
        raise SystemExit("USABLE_BUDGET_CONFIRMATION_MISMATCH")
    if required_reserve_usd != REQUIRED_RESERVE_USD:
        raise SystemExit("REQUIRED_RESERVE_CONFIRMATION_MISMATCH")
    if openai_sdk_version != EXPECTED_OPENAI_SDK_VERSION:
        raise SystemExit("OPENAI_SDK_VERSION_MISMATCH")
    if (
        declared_balance_usd is None
        or declared_balance_usd < MINIMUM_DECLARED_BALANCE_USD
    ):
        raise SystemExit("DECLARED_BALANCE_BELOW_REQUIRED_MINIMUM")
    key_present = api_key_present() if callable(api_key_present) else api_key_present
    if not key_present:
        raise SystemExit("OPENAI_API_KEY_NOT_CONFIGURED")
    Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=declared_balance_usd,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    return _validate_output_root(output_root)


def _result_summary(
    *,
    arm: ExperimentArm,
    provider: Any,
    result: Any,
) -> dict[str, object]:
    record = result.evidence_record
    return {
        "arm": arm.value,
        "status": result.status.value,
        "generation_calls": provider.call_count,
        "poll_count": provider.poll_count,
        "response_id": record.response_id,
        "api_status": record.api_status,
        "incomplete_reason": record.incomplete_reason,
        "usage": record.usage.model_dump(mode="json"),
        "cost_usd": record.cost_usd,
        "hard_failures": [
            item.model_dump(mode="json") for item in result.validation.hard_failures
        ],
        "quality_failures": [
            item.model_dump(mode="json") for item in result.validation.quality_failures
        ],
        "first_raw_output_present": record.first_raw_output is not None,
        "evidence_directory": result.evidence_directory,
    }


def run(
    output_root: Path,
    *,
    declared_balance_usd: Decimal,
    provider_factory: Callable[..., Any] = OpenAIGate2StageC2BackgroundProvider,
    runner_factory: Callable[..., Any] = Gate2StageC2BackgroundRunner,
) -> dict[str, object]:
    output_root = _validate_output_root(output_root)
    case = VISIBLE_CALIBRATION_CASES[0]
    if case.case_id != AUTHORIZED_CASE_ID:
        raise RuntimeError("VISIBLE_CALIBRATION_CASE_ORDER_CHANGED")

    requests = {
        arm: build_stage_c2_retest_request(case, arm) for arm in AUTHORIZED_ARMS
    }
    prompts = {
        arm: Gate2StageC2PromptBuilder().build(request)
        for arm, request in requests.items()
    }
    pricing = Gate2TokenPricing()
    estimates = {
        arm: pricing.conservative_preflight_estimate(
            prompts[arm],
            max_output_tokens=requests[arm].metadata.max_output_tokens,
        )
        for arm in AUTHORIZED_ARMS
    }
    if sum(estimates.values(), Decimal("0")) > AUTHORIZED_SPEND_USD:
        raise RuntimeError("STAGE_C3_CONSERVATIVE_ESTIMATE_EXCEEDS_AUTHORIZATION")

    output_root.mkdir(parents=True, exist_ok=False)
    for arm, request in requests.items():
        _write_new_json(
            output_root / f"visible_calibration_input_{arm.value}.json",
            request.model_dump(mode="json"),
        )
    _write_new_json(
        output_root / "run_manifest.json",
        {
            "stage_c3_run_version": STAGE_C3_RUN_VERSION,
            "calibration_set_version": CALIBRATION_SET_VERSION,
            "case_id": case.case_id,
            "arm_order": [arm.value for arm in AUTHORIZED_ARMS],
            "request_sha256": {
                arm.value: hashlib.sha256(
                    _json_bytes(requests[arm].model_dump(mode="json"))
                ).hexdigest()
                for arm in AUTHORIZED_ARMS
            },
            "prompt_sha256": {
                arm.value: prompts[arm].prompt_sha256 for arm in AUTHORIZED_ARMS
            },
            "prompt_version": STAGE_C2_PROMPT_VERSION,
            "schema_version": STAGE_C2_SCHEMA_VERSION,
            "validator_version": STAGE_C2_VALIDATOR_VERSION,
            "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
            "automatic_sdk_retries": 0,
            "automatic_model_repair_calls": 0,
            "openai_sdk_version": version("openai"),
            "declared_account_balance_usd": str(declared_balance_usd),
            "required_reserve_usd": str(REQUIRED_RESERVE_USD),
            "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
            "conservative_preflight_estimate_usd": {
                arm.value: str(estimates[arm]) for arm in AUTHORIZED_ARMS
            },
            "conservative_preflight_total_usd": str(
                sum(estimates.values(), Decimal("0"))
            ),
            "background_mode": True,
            "store": False,
            "locked_payload_included": False,
            "stage_d_authorized": False,
        },
    )

    budget = Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=declared_balance_usd,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    summaries: list[dict[str, object]] = []
    total_generation_calls = 0
    final_status = "READY_FOR_BLIND_REVIEW"
    for arm in AUTHORIZED_ARMS:
        request = requests[arm]
        checkpoint_writer = Gate2BackgroundCheckpointWriter(
            repository_root=ROOT,
            output_root=output_root,
            case_id=case.case_id,
            arm=arm,
        )
        provider = provider_factory(on_checkpoint=checkpoint_writer.write)
        if (
            provider.reasoning_effort != STAGE_C2_RETEST_REASONING_EFFORT
            or provider.max_output_tokens != STAGE_C2_RETEST_MAX_OUTPUT_TOKENS
        ):
            raise RuntimeError("STAGE_C3_PROVIDER_RUNTIME_COORDINATES_MISMATCH")
        result = runner_factory(
            repository_root=ROOT,
            budget_guard=budget,
        ).run(
            request,
            provider=provider,
            evidence_root=output_root,
        )
        if provider.call_count > 1:
            raise RuntimeError("STAGE_C3_PER_ARM_GENERATION_CALL_LIMIT_EXCEEDED")
        total_generation_calls += provider.call_count
        summaries.append(_result_summary(arm=arm, provider=provider, result=result))
        if result.status is not DryRunStatus.VALIDATED:
            final_status = f"HARD_STOP_{arm.value}_{result.status.value}"
            break

    if total_generation_calls > EXPECTED_GENERATION_CALLS:
        raise RuntimeError("STAGE_C3_TOTAL_GENERATION_CALL_LIMIT_EXCEEDED")
    summary = {
        "status": final_status,
        "stage_c3_run_version": STAGE_C3_RUN_VERSION,
        "case_id": case.case_id,
        "arm_order": [arm.value for arm in AUTHORIZED_ARMS],
        "arms_attempted": [item["arm"] for item in summaries],
        "generation_calls": total_generation_calls,
        "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
        "automatic_sdk_retries": 0,
        "automatic_model_repair_calls": 0,
        "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
        "required_reserve_usd": str(REQUIRED_RESERVE_USD),
        "actual_cost_usd": str(budget.spent_usd),
        "locked_test_set_used": False,
        "formal_product_changed": False,
        "stage_d_entered": False,
        "results": summaries,
    }
    _write_new_json(output_root / "summary.json", summary)
    write_root_evidence_manifest(output_root)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-stage-c3-paid-visible-chart-arms", action="store_true")
    parser.add_argument("--confirm-generation-calls", type=int)
    parser.add_argument("--confirm-usable-budget-usd", type=Decimal)
    parser.add_argument("--confirm-declared-balance-usd", type=Decimal)
    parser.add_argument("--confirm-required-reserve-usd", type=Decimal)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not PAID_VISIBLE_CHART_ARMS_AUTHORIZED:
        raise SystemExit("STAGE_C3_PAID_VISIBLE_CHART_ARMS_NOT_AUTHORIZED")
    if PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_CONSUMED:
        raise SystemExit("STAGE_C3_PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_ALREADY_CONSUMED")
    output_root = validate_paid_preflight(
        output_root=args.output_dir,
        confirmed=args.confirm_stage_c3_paid_visible_chart_arms,
        generation_calls=args.confirm_generation_calls,
        usable_budget_usd=args.confirm_usable_budget_usd,
        declared_balance_usd=args.confirm_declared_balance_usd,
        required_reserve_usd=args.confirm_required_reserve_usd,
        openai_sdk_version=version("openai"),
        api_key_present=lambda: "OPENAI_API_KEY" in os.environ,
        authorized=PAID_VISIBLE_CHART_ARMS_AUTHORIZED,
        authorization_consumed=PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_CONSUMED,
    )
    print(
        json.dumps(
            run(
                output_root,
                declared_balance_usd=args.confirm_declared_balance_usd,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
