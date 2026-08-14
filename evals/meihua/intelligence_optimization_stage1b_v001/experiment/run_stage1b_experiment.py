"""Run the single frozen six-case Stage 1B experiment.

The held-out cases are opened only after the prompt and contract hashes are
frozen. This runner performs no retries and refuses a second held-out run.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    CONTRACT_VERSION,
    DEFAULT_MODEL,
    SYSTEM_INSTRUCTIONS_SHA256,
    OpenAIStage1BProvider,
    Stage1BGenerationEnvelope,
    process_stage1b_experiment_request,
)

STAGE0_REL = Path("evals/meihua/intelligence_diagnostic_v001")
STAGE1B_REL = Path("evals/meihua/intelligence_optimization_stage1b_v001")
GENERIC_CONFIRMATION = "基本准确，这就是我现在真正需要判断的纠结。"
FORBIDDEN_OUTPUT_TERMS = ("起卦", "排盘", "卦象", "吉凶", "本卦", "变卦")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class _CapturingProvider:
    def __init__(self, delegate: OpenAIStage1BProvider) -> None:
        self.delegate = delegate
        self.last_envelope: Stage1BGenerationEnvelope | None = None

    def generate(self, request):
        self.last_envelope = None
        self.last_envelope = self.delegate.generate(request)
        return self.last_envelope


def _call(provider, case_id, question_text, turns, suffix):
    return process_stage1b_experiment_request(
        {
            "contract_version": CONTRACT_VERSION,
            "session_id": f"{case_id}-{suffix}",
            "question_text": question_text,
            "turns": turns,
            "locale": "zh-CN",
        },
        provider=provider,
    )


def _error(exc: Exception) -> dict[str, str]:
    result = {"type": type(exc).__name__, "message": str(exc)}
    if exc.__cause__ is not None:
        result["cause_type"] = type(exc.__cause__).__name__
        result["cause_message"] = str(exc.__cause__)
    return result


def _visible_text(response: dict[str, Any]) -> str:
    parts = [response.get("assistant_message") or "", response.get("next_question") or ""]
    frame = response.get("frame") or {}
    for axis in frame.get("decision_axes") or []:
        parts.extend([axis.get("name") or "", axis.get("option_a") or "", axis.get("option_b") or ""])
    for premise in frame.get("stated_premises") or []:
        parts.append(premise.get("statement") or "")
    hypothesis = response.get("hypothesis") or {}
    parts.extend([hypothesis.get("statement") or "", hypothesis.get("why_decision_is_stuck") or ""])
    for candidate in response.get("candidates") or []:
        parts.extend([candidate.get("question") or "", candidate.get("why_this_question") or ""])
    return "\n".join(parts)


def _initial_turns(case_id: str, baseline_by_id: dict[str, Any], answer_pool: list[str]):
    if case_id in baseline_by_id:
        turns = [
            {
                "question": turn["next_question"],
                "answer": turn["user_answer"],
                "kind": "FROZEN_CONTEXT",
            }
            for turn in baseline_by_id[case_id]["turns"]
            if turn.get("user_answer") is not None
        ]
        if [turn["answer"] for turn in turns] != answer_pool:
            raise ValueError(f"{case_id} baseline answers differ from frozen input")
        return turns
    return [
        {
            "question": f"冻结背景补充{index + 1}",
            "answer": answer,
            "kind": "FROZEN_CONTEXT",
        }
        for index, answer in enumerate(answer_pool)
    ]


def run(repo_root: Path, model: str) -> Path:
    stage0 = repo_root / STAGE0_REL
    stage1b = repo_root / STAGE1B_REL
    manifest = _load(stage1b / "manifest.json")
    if manifest["prompt_sha256"].lower() != SYSTEM_INSTRUCTIONS_SHA256.lower():
        raise RuntimeError("prompt hash changed after freeze")
    contract_path = stage1b / "experiment/decision_frame_experiment_v1.py"
    if manifest["contract_file_sha256"] != _sha256(contract_path):
        raise RuntimeError("contract file changed after freeze")
    for key, path_key in (
        ("heldout_cases_sha256", "heldout_cases"),
        ("heldout_expectations_sha256", "heldout_expectations"),
    ):
        if manifest[key] != _sha256(stage1b / manifest[path_key]):
            raise RuntimeError(f"{path_key} changed after freeze")
    existing = list((stage1b / "runs").glob("stage1b_six_case_*.json"))
    if existing:
        raise RuntimeError("held-out run already exists; a second run is forbidden")

    inputs = _load(stage0 / "guided_intake_synthetic_inputs.json")
    baselines = _load(stage0 / "baselines/current_guided_intake_snapshots.json")
    heldout = _load(stage1b / manifest["heldout_cases"])
    heldout_expectations = _load(stage1b / manifest["heldout_expectations"])
    development_answers = _load(stage1b / "cases/development_critical_answers.json")
    heldout_answers = _load(stage1b / "cases/heldout_critical_answers.json")

    cases = inputs["cases"] + heldout["cases"]
    baseline_by_id = {item["case_id"]: item for item in baselines["cases"]}
    answer_by_id = {
        item["case_id"]: item
        for item in development_answers["cases"] + heldout_answers["cases"]
    }
    expected_state_by_id = {
        item["case_id"]: item["acceptable_initial_state"]
        for item in heldout_expectations["expectations"]
    }
    expected_dimension_by_id = {
        item["case_id"]: item.get("expected_dimension")
        for item in development_answers["cases"] + heldout_answers["cases"]
    }
    if {item["case_id"] for item in cases} != set(answer_by_id):
        raise RuntimeError("critical-answer scripts do not cover all six cases")

    provider = _CapturingProvider(OpenAIStage1BProvider(model=model))
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["case_id"]
        initial_turns = _initial_turns(case_id, baseline_by_id, case["answer_pool"])
        result: dict[str, Any] = {
            "case_id": case_id,
            "set": "DEVELOPMENT" if case_id in baseline_by_id else "HELDOUT",
            "synthetic": True,
            "question_text": case["question_text"],
            "frozen_answers": case["answer_pool"],
            "initial": None,
            "critical_answer": answer_by_id[case_id].get("critical_answer"),
            "after_critical": None,
            "completed": None,
        }
        try:
            initial = _call(provider, case_id, case["question_text"], initial_turns, "initial")
            result["initial"] = initial
            ready = initial
            turns = list(initial_turns)
            if initial["status"] == "ASK_CRITICAL":
                critical_answer = result["critical_answer"]
                if not critical_answer:
                    raise RuntimeError("model asked a critical question where no frozen answer is allowed")
                turns.append(
                    {
                        "question": initial["next_question"],
                        "answer": critical_answer,
                        "kind": "CRITICAL_ANSWER",
                    }
                )
                ready = _call(provider, case_id, case["question_text"], turns, "after-critical")
                result["after_critical"] = ready
            if ready["status"] == "CONFIRM":
                turns.append(
                    {
                        "question": ready["next_question"],
                        "answer": GENERIC_CONFIRMATION,
                        "kind": "CONFIRMATION",
                    }
                )
                result["completed"] = _call(
                    provider, case_id, case["question_text"], turns, "complete"
                )
            elif ready["status"] != "INSUFFICIENT_TO_HYPOTHESIZE":
                raise RuntimeError(f"unexpected ready state: {ready['status']}")

            expected_states = expected_state_by_id.get(case_id, ["ASK_CRITICAL"])
            expected_dimension = expected_dimension_by_id.get(case_id)
            actual_dimension = (
                (initial.get("frame") or {}).get("highest_value_unknown") or {}
            ).get("dimension")
            completed = result["completed"]
            all_visible = "\n".join(
                _visible_text(response)
                for response in (initial, result["after_critical"], completed)
                if response
            )
            result["machine_gates"] = {
                "initial_state_matches_frozen_expectation": initial["status"] in expected_states,
                "critical_dimension_matches_frozen_expectation": (
                    expected_dimension is None or actual_dimension == expected_dimension
                ),
                "at_most_one_critical_question": sum(
                    response is not None
                    for response in [initial if initial["status"] == "ASK_CRITICAL" else None]
                )
                <= 1,
                "resolved_or_honestly_insufficient_after_one_question": ready["status"]
                in {"CONFIRM", "INSUFFICIENT_TO_HYPOTHESIZE"},
                "complete_only_after_confirmation": (
                    completed is None
                    if ready["status"] == "INSUFFICIENT_TO_HYPOTHESIZE"
                    else completed is not None and completed["status"] == "COMPLETE"
                ),
                "candidate_count_one_or_two_when_complete": (
                    completed is None or 1 <= len(completed.get("candidates") or []) <= 2
                ),
                "no_stage2_terms": not any(term in all_visible for term in FORBIDDEN_OUTPUT_TERMS),
            }
        except Exception as exc:
            result["error"] = _error(exc)
            if provider.last_envelope is not None:
                result["rejected_model_output"] = provider.last_envelope.output.model_dump(mode="json")
                result["rejected_generation_metrics"] = provider.last_envelope.metrics.model_dump(mode="json")
            result["machine_gates"] = {"experiment_call_succeeded": False}
        results.append(result)

    metrics: list[dict[str, Any]] = []
    for result in results:
        for key in ("initial", "after_critical", "completed"):
            response = result.get(key)
            if response and response.get("generation_metrics"):
                metrics.append(response["generation_metrics"])
        if result.get("rejected_generation_metrics"):
            metrics.append(result["rejected_generation_metrics"])
    gate_values = [
        value for result in results for value in result.get("machine_gates", {}).values()
    ]
    payload = {
        "run_id": f"GUANXIANG_STAGE1B_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "scope": "STAGE1B_SINGLE_SIX_CASE_RUN",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model,
        "contract_version": CONTRACT_VERSION,
        "prompt_sha256": SYSTEM_INSTRUCTIONS_SHA256,
        "contract_file_sha256": _sha256(contract_path),
        "heldout_run_number": 1,
        "no_retries": True,
        "generic_confirmation_is_synthetic": True,
        "cases": results,
        "aggregate": {
            "api_call_count": len(metrics),
            "input_tokens": sum(item.get("input_tokens") or 0 for item in metrics),
            "output_tokens": sum(item.get("output_tokens") or 0 for item in metrics),
            "total_tokens": sum(item.get("total_tokens") or 0 for item in metrics),
            "latency_total_ms": sum(item.get("latency_ms") or 0 for item in metrics),
            "estimated_cost_usd": None,
            "all_machine_gates_pass": bool(gate_values) and all(gate_values),
        },
    }
    path = stage1b / "runs" / f"stage1b_six_case_{payload['run_id'].lower()}.json"
    _write(path, payload)
    return path


def main() -> None:
    repo_root = Path.cwd().resolve()
    model = os.getenv("ABALO_STAGE1B_MODEL", DEFAULT_MODEL)
    print(run(repo_root, model))


if __name__ == "__main__":
    main()

