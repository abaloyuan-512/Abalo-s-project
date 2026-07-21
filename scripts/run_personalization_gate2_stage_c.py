"""Run Gate 2 Stage C visible synthetic calibration with a hard cost ceiling."""

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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    CALIBRATION_SET_VERSION,
    VISIBLE_CALIBRATION_CASES,
    build_manifest,
    build_request,
)
from abalo_iching.personalization_gate2.evidence import Gate2EvidenceWriter
from abalo_iching.personalization_gate2.live_provider import OpenAIGate2Provider
from abalo_iching.personalization_gate2.live_runner import Gate2CalibrationRunner
from abalo_iching.personalization_gate2.models import ExperimentArm
from abalo_iching.personalization_gate2.runner import Gate2OfflineRunner
from abalo_iching.personalization_gate2.validators import Gate2ExperimentValidator


DECLARED_BALANCE_USD = Decimal("9")
REQUIRED_RESERVE_USD = Decimal("7")
AUTHORIZED_SPEND_USD = Decimal("2")
EXPECTED_GENERATION_CALLS = len(VISIBLE_CALIBRATION_CASES) * 3


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_new_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"拒绝覆盖已有阶段 C 证据文件：{path}")
    data = _json_bytes(value)
    temp = path.with_name(f".{path.name}.tmp")
    if temp.exists():
        raise FileExistsError(f"拒绝覆盖已有临时文件：{temp}")
    temp.write_bytes(data)
    os.replace(temp, path)


def _validate_output_root(output_root: Path) -> Path:
    resolved = output_root.resolve()
    repository = ROOT.resolve()
    if resolved == repository or repository in resolved.parents:
        raise ValueError("阶段 C 真实运行证据必须位于 Git 仓库之外")
    if resolved.exists():
        raise FileExistsError("阶段 C 输出目录必须是尚不存在的新目录")
    return resolved


def _baseline_record(request, output_root: Path) -> dict[str, object]:
    result = Gate2OfflineRunner(repository_root=ROOT).run(request)
    record = result.evidence_record.model_copy(
        update={
            "human_review": {
                "status": "PENDING",
                "reviewer": None,
                "scores": None,
                "notes": None,
            }
        }
    )
    evidence_dir = Gate2EvidenceWriter(repository_root=ROOT).write(
        record,
        output_root,
    )
    return {
        "case_id": request.metadata.case_id,
        "arm": "A",
        "status": result.status.value,
        "evidence_directory": str(evidence_dir),
        "response_id": None,
        "cost_usd": 0.0,
        "hard_failure_codes": [],
        "quality_failure_codes": [],
    }


def run(output_root: Path) -> dict[str, object]:
    output_root = _validate_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=False)

    manifest = build_manifest()
    requests = {
        case.case_id: {
            arm.value: build_request(case, arm).model_dump(mode="json")
            for arm in ExperimentArm
        }
        for case in VISIBLE_CALIBRATION_CASES
    }
    inputs_bytes = _json_bytes(
        {
            "calibration_set_version": CALIBRATION_SET_VERSION,
            "manifest": manifest.model_dump(mode="json"),
            "requests": requests,
        }
    )
    _write_new_json(
        output_root / "run_manifest.json",
        {
            "calibration_set_version": CALIBRATION_SET_VERSION,
            "manifest": manifest.model_dump(mode="json"),
            "requests_sha256": hashlib.sha256(inputs_bytes).hexdigest(),
            "locked_payload_included": False,
            "declared_account_balance_usd": str(DECLARED_BALANCE_USD),
            "required_reserve_usd": str(REQUIRED_RESERVE_USD),
            "authorized_spend_usd": str(AUTHORIZED_SPEND_USD),
            "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
        },
    )
    (output_root / "visible_calibration_inputs.json").write_bytes(inputs_bytes)

    budget = Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=DECLARED_BALANCE_USD,
        required_reserve_usd=REQUIRED_RESERVE_USD,
        authorized_spend_usd=AUTHORIZED_SPEND_USD,
    )
    provider = OpenAIGate2Provider()
    runner = Gate2CalibrationRunner(
        repository_root=ROOT,
        budget_guard=budget,
    )
    validator = Gate2ExperimentValidator()
    results: list[dict[str, object]] = []
    cross_arm_quality_findings: list[dict[str, object]] = []
    hard_stop = False

    for case in VISIBLE_CALIBRATION_CASES:
        case_outputs = {}
        baseline_request = build_request(case, ExperimentArm.A)
        results.append(_baseline_record(baseline_request, output_root))

        for arm in (ExperimentArm.B, ExperimentArm.C, ExperimentArm.D):
            request = build_request(case, arm)
            result = runner.run(
                request,
                provider=provider,
                evidence_root=output_root,
            )
            hard_codes = [item.code for item in result.validation.hard_failures]
            quality_codes = [item.code for item in result.validation.quality_failures]
            results.append(
                {
                    "case_id": case.case_id,
                    "arm": arm.value,
                    "status": result.status.value,
                    "evidence_directory": result.evidence_directory,
                    "response_id": result.evidence_record.response_id,
                    "cost_usd": result.evidence_record.cost_usd,
                    "hard_failure_codes": hard_codes,
                    "quality_failure_codes": quality_codes,
                }
            )
            if result.output is not None:
                case_outputs[arm] = result.output
            if hard_codes:
                hard_stop = True
                break
        if hard_stop:
            break
        if set(case_outputs) == {
            ExperimentArm.B,
            ExperimentArm.C,
            ExperimentArm.D,
        }:
            findings = validator.validate_arm_set(case_outputs)
            cross_arm_quality_findings.extend(
                {
                    "case_id": case.case_id,
                    "code": item.code,
                    "message": item.message,
                }
                for item in findings
            )

    if hard_stop:
        status = "HARD_STOP_FIRST_GENERATION_FAILURE_PRESERVED"
    elif cross_arm_quality_findings or any(
        item["quality_failure_codes"] for item in results
    ):
        status = "COMPLETED_WITH_QUALITY_FINDINGS"
    else:
        status = "COMPLETED_PENDING_HUMAN_REVIEW"

    known_costs = [
        Decimal(str(item["cost_usd"]))
        for item in results
        if item["cost_usd"] is not None
    ]
    calculated_cost = sum(
        known_costs,
        Decimal("0"),
    )
    summary = {
        "status": status,
        "calibration_set_version": CALIBRATION_SET_VERSION,
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "max_output_tokens": provider.max_output_tokens,
        "generation_calls": provider.call_count,
        "maximum_generation_calls": EXPECTED_GENERATION_CALLS,
        "calculated_cost_usd": str(calculated_cost),
        "cost_status": (
            "UNKNOWN_FOR_AT_LEAST_ONE_GENERATION_ATTEMPT"
            if any(item["cost_usd"] is None for item in results)
            else "CALCULATED_FROM_API_USAGE"
        ),
        "authorized_spend_usd": str(budget.authorized_spend_usd),
        "required_reserve_usd": str(budget.required_reserve_usd),
        "pricing_version": provider.pricing.version,
        "pricing_source": provider.pricing.source,
        "locked_test_set_used": False,
        "formal_product_changed": False,
        "automatic_model_repair_calls": 0,
        "results": results,
        "cross_arm_quality_findings": cross_arm_quality_findings,
    }
    _write_new_json(output_root / "summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-stage-c", action="store_true")
    parser.add_argument("--confirm-generation-calls", type=int)
    parser.add_argument("--confirm-usable-budget-usd", type=Decimal)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.confirm_stage_c:
        raise SystemExit("STAGE_C_EXPLICIT_CONFIRMATION_REQUIRED")
    if args.confirm_generation_calls != EXPECTED_GENERATION_CALLS:
        raise SystemExit("GENERATION_CALL_LIMIT_CONFIRMATION_MISMATCH")
    if args.confirm_usable_budget_usd != AUTHORIZED_SPEND_USD:
        raise SystemExit("USABLE_BUDGET_CONFIRMATION_MISMATCH")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY_NOT_CONFIGURED")
    print(json.dumps(run(args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
