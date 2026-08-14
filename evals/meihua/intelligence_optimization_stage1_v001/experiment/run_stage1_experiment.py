"""Run the frozen Stage 1 discernment A/B experiment.

Arm A is read from the Stage 0 snapshot and is never regenerated. Arm B sees
the same original question and the same four frozen answers, then gets one
clearly labelled synthetic confirmation or correction turn. Synthetic turns
exercise the state machine only; they are not evidence of user value.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    CONTRACT_VERSION,
    DEFAULT_MODEL,
    SYSTEM_INSTRUCTIONS_SHA256,
    OpenAIStage1Provider,
    Stage1ExperimentError,
    process_stage1_experiment_request,
)

STAGE0_REL = Path("evals/meihua/intelligence_diagnostic_v001")
STAGE1_REL = Path("evals/meihua/intelligence_optimization_stage1_v001")
FORBIDDEN_OUTPUT_TERMS = ("起卦", "排盘", "卦象", "吉凶", "本卦", "变卦")


class _CapturingProvider:
    """Keep rejected structured output visible when a downstream gate fails."""

    def __init__(self, delegate: OpenAIStage1Provider) -> None:
        self.delegate = delegate
        self.last_envelope = None

    def generate(self, request):
        self.last_envelope = None
        self.last_envelope = self.delegate.generate(request)
        return self.last_envelope


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _same_information_turns(baseline_case: dict[str, Any]) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    for turn in baseline_case["turns"]:
        answer = turn.get("user_answer")
        if answer is not None:
            turns.append({"question": turn["next_question"], "answer": answer})
    if len(turns) != 4:
        raise ValueError(f"{baseline_case['case_id']} does not have four frozen answered turns")
    return turns


def _call(
    *,
    provider: OpenAIStage1Provider,
    case_id: str,
    question_text: str,
    turns: list[dict[str, str]],
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
        provider=provider,
    )


def _visible_text(response: dict[str, Any]) -> str:
    parts = [response.get("assistant_message") or "", response.get("next_question") or ""]
    hypothesis = response.get("hypothesis") or {}
    parts.extend(
        [
            hypothesis.get("statement") or "",
            hypothesis.get("why_decision_is_stuck") or "",
        ]
    )
    for candidate in response.get("candidates") or []:
        parts.extend(
            [
                candidate.get("question") or "",
                candidate.get("what_it_tests") or "",
                candidate.get("why_this_question") or "",
            ]
        )
    return "\n".join(parts)


def _main_gates(
    pre_confirmation: dict[str, Any],
    completed: dict[str, Any] | None,
) -> dict[str, bool]:
    candidates = (completed or {}).get("candidates") or []
    focuses = [item.get("focus_type") for item in candidates]
    visible_text = _visible_text(completed or pre_confirmation)
    return {
        "pre_confirmation_status_is_CONFIRM": pre_confirmation.get("status") == "CONFIRM",
        "no_candidates_before_confirmation": not pre_confirmation.get("candidates"),
        "hypothesis_exists_before_confirmation": bool(pre_confirmation.get("hypothesis")),
        "completed_only_after_confirmation": (completed or {}).get("status") == "COMPLETE",
        "confirmation_state_is_resolved": (completed or {}).get("confirmation", {}).get("state")
        in {"CONFIRMED", "CORRECTED"},
        "candidate_count_is_one_or_two": 1 <= len(candidates) <= 2,
        "candidate_focuses_are_distinct": len(focuses) == len(set(focuses)),
        "no_stage2_terms_in_visible_output": not any(term in visible_text for term in FORBIDDEN_OUTPUT_TERMS),
    }


def _error_payload(exc: Exception) -> dict[str, str]:
    payload = {"type": type(exc).__name__, "message": str(exc)}
    if exc.__cause__ is not None:
        payload["cause_type"] = type(exc.__cause__).__name__
        payload["cause_message"] = str(exc.__cause__)
    return payload


def run(repo_root: Path, model: str) -> Path:
    stage0 = repo_root / STAGE0_REL
    stage1 = repo_root / STAGE1_REL
    inputs = _load_json(stage0 / "guided_intake_synthetic_inputs.json")
    baselines = _load_json(stage0 / "baselines/current_guided_intake_snapshots.json")
    scripts = _load_json(stage1 / "synthetic_actor_scripts.json")

    input_by_id = {item["case_id"]: item for item in inputs["cases"]}
    baseline_by_id = {item["case_id"]: item for item in baselines["cases"]}
    confirmation_by_id = {item["case_id"]: item for item in scripts["main_confirmation_scripts"]}

    if set(input_by_id) != set(baseline_by_id) or set(input_by_id) != set(confirmation_by_id):
        raise ValueError("frozen inputs, baselines, and confirmation scripts do not cover the same cases")

    provider = _CapturingProvider(OpenAIStage1Provider(model=model, timeout_seconds=90.0))
    results: list[dict[str, Any]] = []
    confirmation_prompts: dict[str, dict[str, Any]] = {}

    for case_id in sorted(input_by_id):
        baseline = baseline_by_id[case_id]
        case_input = input_by_id[case_id]
        frozen_turns = _same_information_turns(baseline)
        case_result: dict[str, Any] = {
            "case_id": case_id,
            "synthetic": True,
            "arm_a_frozen": {
                "source_dataset": baselines["dataset_id"],
                "terminal_status": baseline["terminal_status"],
                "final_suggested_question": baseline["final_suggested_question"],
                "usage_totals": baseline["usage_totals"],
                "latency_total_ms": baseline["latency_total_ms"],
            },
            "arm_b": {
                "same_original_question": True,
                "same_four_frozen_answers": [turn["answer"] for turn in frozen_turns]
                == case_input["answer_pool"],
                "pre_confirmation": None,
                "synthetic_confirmation": confirmation_by_id[case_id]["answer"],
                "completed": None,
            },
        }
        try:
            pre = _call(
                provider=provider,
                case_id=case_id,
                question_text=case_input["question_text"],
                turns=frozen_turns,
                suffix="pre",
            )
            case_result["arm_b"]["pre_confirmation"] = pre
            if pre["status"] == "CONFIRM" and pre.get("next_question"):
                confirmation_prompts[case_id] = pre
                completed = _call(
                    provider=provider,
                    case_id=case_id,
                    question_text=case_input["question_text"],
                    turns=frozen_turns
                    + [
                        {
                            "question": pre["next_question"],
                            "answer": confirmation_by_id[case_id]["answer"],
                        }
                    ],
                    suffix="confirmed",
                )
                case_result["arm_b"]["completed"] = completed
            else:
                case_result["arm_b"]["stop_reason"] = (
                    "No extra user information was fabricated when the model did not enter CONFIRM."
                )
            case_result["machine_gates"] = _main_gates(
                pre,
                case_result["arm_b"].get("completed"),
            )
        except Exception as exc:  # result must preserve failures for PMO review
            case_result["error"] = _error_payload(exc)
            if provider.last_envelope is not None:
                case_result["rejected_model_output"] = provider.last_envelope.output.model_dump(mode="json")
                case_result["rejected_generation_metrics"] = provider.last_envelope.metrics.model_dump(
                    mode="json"
                )
            case_result["machine_gates"] = {"experiment_call_succeeded": False}
        results.append(case_result)

    corrections: list[dict[str, Any]] = []
    for script in scripts["correction_scripts"]:
        case_id = script["case_id"]
        branch: dict[str, Any] = {
            "script_id": script["script_id"],
            "case_id": case_id,
            "synthetic": True,
            "correction_answer": script["answer"],
        }
        try:
            pre = confirmation_prompts[case_id]
            frozen_turns = _same_information_turns(baseline_by_id[case_id])
            corrected = _call(
                provider=provider,
                case_id=case_id,
                question_text=input_by_id[case_id]["question_text"],
                turns=frozen_turns
                + [{"question": pre["next_question"], "answer": script["answer"]}],
                suffix=script["script_id"].lower(),
            )
            branch["response"] = corrected
            branch["machine_gates"] = {
                "status_is_COMPLETE": corrected.get("status") == "COMPLETE",
                "confirmation_state_is_CORRECTED": corrected.get("confirmation", {}).get("state")
                == "CORRECTED",
                "corrected_hypothesis_exists": bool(corrected.get("hypothesis")),
                "candidate_count_is_one_or_two": 1 <= len(corrected.get("candidates") or []) <= 2,
                "no_stage2_terms_in_visible_output": not any(
                    term in _visible_text(corrected) for term in FORBIDDEN_OUTPUT_TERMS
                ),
            }
        except Exception as exc:
            branch["error"] = _error_payload(exc)
            if provider.last_envelope is not None:
                branch["rejected_model_output"] = provider.last_envelope.output.model_dump(mode="json")
                branch["rejected_generation_metrics"] = provider.last_envelope.metrics.model_dump(mode="json")
            branch["machine_gates"] = {"experiment_call_succeeded": False}
        corrections.append(branch)

    all_metrics = []
    for result in results:
        for key in ("pre_confirmation", "completed"):
            response = result.get("arm_b", {}).get(key)
            if response and response.get("generation_metrics"):
                all_metrics.append(response["generation_metrics"])
    for branch in corrections:
        response = branch.get("response")
        if response and response.get("generation_metrics"):
            all_metrics.append(response["generation_metrics"])

    gate_values = [
        value
        for result in results
        for value in result.get("machine_gates", {}).values()
    ] + [
        value
        for branch in corrections
        for value in branch.get("machine_gates", {}).values()
    ]
    payload = {
        "run_id": f"GUANXIANG_STAGE1_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "scope": "STAGE_1_DISCERNMENT_EXPERIMENT_ONLY",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model,
        "contract_version": CONTRACT_VERSION,
        "system_instructions_sha256": SYSTEM_INSTRUCTIONS_SHA256,
        "arm_a_policy": "READ_FROZEN_STAGE0_BASELINE_ONLY",
        "synthetic_confirmation_policy": (
            "State-machine evidence only; never count as real user approval or user-value evidence."
        ),
        "cases": results,
        "correction_branches": corrections,
        "aggregate": {
            "api_call_count": len(all_metrics),
            "input_tokens": sum(item.get("input_tokens") or 0 for item in all_metrics),
            "output_tokens": sum(item.get("output_tokens") or 0 for item in all_metrics),
            "total_tokens": sum(item.get("total_tokens") or 0 for item in all_metrics),
            "latency_total_ms": sum(item.get("latency_ms") or 0 for item in all_metrics),
            "estimated_cost_usd": None,
            "all_machine_gates_pass": bool(gate_values) and all(gate_values),
        },
    }
    output_path = stage1 / "runs" / f"{payload['run_id'].lower()}.json"
    _write_json(output_path, payload)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=os.getenv("ABALO_STAGE1_DISCERNMENT_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()
    path = run(args.repo_root.resolve(), args.model)
    print(path)


if __name__ == "__main__":
    main()
