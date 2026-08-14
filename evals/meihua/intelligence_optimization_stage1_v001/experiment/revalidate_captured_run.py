"""Revalidate captured model output after a deterministic validator correction.

This script never calls a model. It preserves the source run, validates only
its already-captured structured outputs, and writes a derived audit artifact.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    CONTRACT_VERSION,
    GenerationEnvelope,
    GenerationMetrics,
    Stage1ModelOutput,
    process_stage1_experiment_request,
)
from evals.meihua.intelligence_optimization_stage1_v001.experiment.run_stage1_experiment import (
    STAGE0_REL,
    STAGE1_REL,
    _load_json,
    _main_gates,
    _same_information_turns,
    _visible_text,
    _write_json,
)


class _CapturedProvider:
    def __init__(self, output: dict[str, Any], metrics: dict[str, Any]) -> None:
        self.envelope = GenerationEnvelope(
            output=Stage1ModelOutput.model_validate(output),
            metrics=GenerationMetrics.model_validate(metrics),
        )

    def generate(self, _request):
        return self.envelope


def _validate(
    *,
    case_id: str,
    question_text: str,
    turns: list[dict[str, str]],
    output: dict[str, Any],
    metrics: dict[str, Any],
    suffix: str,
) -> dict[str, Any]:
    return process_stage1_experiment_request(
        {
            "contract_version": CONTRACT_VERSION,
            "session_id": f"{case_id}-{suffix}",
            "question_text": question_text,
            "turns": turns,
            "locale": "zh-CN",
        },
        provider=_CapturedProvider(output, metrics),
    )


def _all_metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for case in payload["cases"]:
        for key in ("pre_confirmation", "completed"):
            response = case.get("arm_b", {}).get(key)
            if response and response.get("generation_metrics"):
                metrics.append(response["generation_metrics"])
        if case.get("rejected_generation_metrics") and not case.get("arm_b", {}).get("completed"):
            metrics.append(case["rejected_generation_metrics"])
    for branch in payload["correction_branches"]:
        response = branch.get("response")
        if response and response.get("generation_metrics"):
            metrics.append(response["generation_metrics"])
        if branch.get("rejected_generation_metrics") and not branch.get("response"):
            metrics.append(branch["rejected_generation_metrics"])
    return metrics


def revalidate(repo_root: Path, source_path: Path) -> Path:
    source = _load_json(source_path)
    payload = copy.deepcopy(source)
    stage0 = repo_root / STAGE0_REL
    stage1 = repo_root / STAGE1_REL
    inputs = _load_json(stage0 / "guided_intake_synthetic_inputs.json")
    baselines = _load_json(stage0 / "baselines/current_guided_intake_snapshots.json")

    input_by_id = {item["case_id"]: item for item in inputs["cases"]}
    baseline_by_id = {item["case_id"]: item for item in baselines["cases"]}
    pre_by_id: dict[str, dict[str, Any]] = {}

    for case in payload["cases"]:
        case_id = case["case_id"]
        pre = case["arm_b"].get("pre_confirmation")
        if pre:
            pre_by_id[case_id] = pre
        if not case.get("rejected_model_output"):
            continue
        frozen_turns = _same_information_turns(baseline_by_id[case_id])
        completed = _validate(
            case_id=case_id,
            question_text=input_by_id[case_id]["question_text"],
            turns=frozen_turns
            + [
                {
                    "question": pre["next_question"],
                    "answer": case["arm_b"]["synthetic_confirmation"],
                }
            ],
            output=case["rejected_model_output"],
            metrics=case["rejected_generation_metrics"],
            suffix="revalidated-confirmed",
        )
        case["original_validation_error"] = case.pop("error")
        case["arm_b"]["completed"] = completed
        case["machine_gates"] = _main_gates(pre, completed)

    for branch in payload["correction_branches"]:
        if not branch.get("rejected_model_output"):
            continue
        case_id = branch["case_id"]
        frozen_turns = _same_information_turns(baseline_by_id[case_id])
        response = _validate(
            case_id=case_id,
            question_text=input_by_id[case_id]["question_text"],
            turns=frozen_turns
            + [
                {
                    "question": pre_by_id[case_id]["next_question"],
                    "answer": branch["correction_answer"],
                }
            ],
            output=branch["rejected_model_output"],
            metrics=branch["rejected_generation_metrics"],
            suffix=f"{branch['script_id'].lower()}-revalidated",
        )
        branch["original_validation_error"] = branch.pop("error")
        branch["response"] = response
        branch["machine_gates"] = {
            "status_is_COMPLETE": response.get("status") == "COMPLETE",
            "confirmation_state_is_CORRECTED": response.get("confirmation", {}).get("state")
            == "CORRECTED",
            "corrected_hypothesis_exists": bool(response.get("hypothesis")),
            "candidate_count_is_one_or_two": 1 <= len(response.get("candidates") or []) <= 2,
            "no_stage2_terms_in_visible_output": not any(
                term in _visible_text(response)
                for term in ("起卦", "排盘", "卦象", "吉凶", "本卦", "变卦")
            ),
        }

    payload["derived_from_run_id"] = source["run_id"]
    payload["run_id"] = f"{source['run_id']}_REVALIDATED_V1"
    payload["validation_only"] = True
    payload["model_recalled"] = False
    payload["validator_change"] = (
        "Accepted natural either-or Chinese questions containing 应该/还是; no content was regenerated."
    )
    metrics = _all_metrics(payload)
    gate_values = [
        value for case in payload["cases"] for value in case.get("machine_gates", {}).values()
    ] + [
        value
        for branch in payload["correction_branches"]
        for value in branch.get("machine_gates", {}).values()
    ]
    payload["aggregate"] = {
        "api_call_count": len(metrics),
        "input_tokens": sum(item.get("input_tokens") or 0 for item in metrics),
        "output_tokens": sum(item.get("output_tokens") or 0 for item in metrics),
        "total_tokens": sum(item.get("total_tokens") or 0 for item in metrics),
        "latency_total_ms": sum(item.get("latency_ms") or 0 for item in metrics),
        "estimated_cost_usd": None,
        "all_machine_gates_pass": bool(gate_values) and all(gate_values),
    }
    output_path = stage1 / "runs" / f"{payload['run_id'].lower()}.json"
    _write_json(output_path, payload)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(revalidate(args.repo_root.resolve(), args.source_run.resolve()))


if __name__ == "__main__":
    main()
