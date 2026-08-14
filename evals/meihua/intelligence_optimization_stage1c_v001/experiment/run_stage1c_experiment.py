"""Run the single frozen Stage 1C readiness-veto experiment."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
    GenerationMetrics,
)
from evals.meihua.intelligence_optimization_stage1c_v001.experiment.readiness_veto_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_PROMPT_SHA256,
    PROPOSER_PROMPT_SHA256,
    FrameProposal,
    OpenAICritic,
    OpenAIProposer,
    ProposalEnvelope,
    Stage1CRequest,
    arbitrate_stage1c_request,
)

STAGE0_REL = Path("evals/meihua/intelligence_diagnostic_v001")
STAGE1B_REL = Path("evals/meihua/intelligence_optimization_stage1b_v001")
STAGE1C_REL = Path("evals/meihua/intelligence_optimization_stage1c_v001")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _initial_turns(case_id: str, baselines: dict[str, Any], answers: list[str]):
    if case_id in baselines:
        turns = [
            {
                "question": turn["next_question"],
                "answer": turn["user_answer"],
                "kind": "FROZEN_CONTEXT",
            }
            for turn in baselines[case_id]["turns"]
            if turn.get("user_answer") is not None
        ]
        if [turn["answer"] for turn in turns] != answers:
            raise RuntimeError(f"{case_id} baseline differs from frozen answers")
        return turns
    return [
        {
            "question": f"冻结背景补充{index + 1}",
            "answer": answer,
            "kind": "FROZEN_CONTEXT",
        }
        for index, answer in enumerate(answers)
    ]


class FrozenProposer:
    """Expose the exact Stage 1B proposal without another model call."""

    def __init__(self, proposal: FrameProposal) -> None:
        self.proposal = proposal

    def generate(self, _request):
        return ProposalEnvelope(
            output=self.proposal,
            metrics=GenerationMetrics(model="frozen-stage1b-no-new-call", total_tokens=0, latency_ms=0),
        )


def _stage1b_proposal(case_result: dict[str, Any]) -> FrameProposal:
    raw = case_result["rejected_model_output"]
    return FrameProposal(
        frame=raw["frame"],
        candidate_hypothesis=raw["hypothesis"],
        proposal_note="冻结的阶段1B候选框架；未重新生成。",
    )


def _request_payload(case_id, question_text, turns):
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": case_id,
        "question_text": question_text,
        "turns": turns,
        "locale": "zh-CN",
    }


def run(repo_root: Path, model: str) -> Path:
    stage0 = repo_root / STAGE0_REL
    stage1b = repo_root / STAGE1B_REL
    stage1c = repo_root / STAGE1C_REL
    manifest = _load(stage1c / "manifest.json")
    contract_path = stage1c / "experiment/readiness_veto_experiment_v1.py"
    checks = {
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256.upper(),
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256.upper(),
        "contract_file_sha256": _sha(contract_path),
        "heldout_cases_sha256": _sha(stage1c / manifest["heldout_cases"]),
        "heldout_expectations_sha256": _sha(stage1c / manifest["heldout_expectations"]),
        "heldout_critical_answers_sha256": _sha(stage1c / manifest["heldout_critical_answers"]),
    }
    for key, actual in checks.items():
        if manifest[key].upper() != actual:
            raise RuntimeError(f"frozen hash mismatch: {key}")
    run_marker = stage1c / "runs" / "stage1c_run_started.json"
    if run_marker.exists() or list((stage1c / "runs").glob("stage1c_single_run_*.json")):
        raise RuntimeError("Stage 1C heldout has already been run")

    _write(
        run_marker,
        {
            "started_at": datetime.now(UTC).isoformat(),
            "scope": "STAGE1C_SINGLE_FROZEN_RUN",
            "model": model,
            "contract_version": CONTRACT_VERSION,
            "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256,
            "critic_prompt_sha256": CRITIC_PROMPT_SHA256,
            "contract_file_sha256": _sha(contract_path),
            "retry_permitted": False,
        },
    )

    stage0_inputs = _load(stage0 / "guided_intake_synthetic_inputs.json")
    stage0_baselines_raw = _load(stage0 / "baselines/current_guided_intake_snapshots.json")
    baselines = {item["case_id"]: item for item in stage0_baselines_raw["cases"]}
    heldout = _load(stage1c / manifest["heldout_cases"])
    heldout_expectations = _load(stage1c / manifest["heldout_expectations"])
    heldout_answers = _load(stage1c / manifest["heldout_critical_answers"])
    development_answers = _load(stage1b / "cases/development_critical_answers.json")
    stage1b_run = _load(
        stage1b / "runs/stage1b_six_case_guanxiang_stage1b_20260806t141839z.json"
    )
    stage1b_by_id = {item["case_id"]: item for item in stage1b_run["cases"]}

    cases = stage0_inputs["cases"] + heldout["cases"]
    critical_by_id = {
        item["case_id"]: item
        for item in development_answers["cases"] + heldout_answers["cases"]
    }
    heldout_expected_by_id = {
        item["case_id"]: item for item in heldout_expectations["expectations"]
    }
    proposer_live = OpenAIProposer(model=model)
    critic_live = OpenAICritic(model=model)
    results: list[dict[str, Any]] = []

    for case in cases:
        case_id = case["case_id"]
        turns = _initial_turns(case_id, baselines, case["answer_pool"])
        is_core = case_id in stage1b_by_id
        initial_proposer = (
            FrozenProposer(_stage1b_proposal(stage1b_by_id[case_id])) if is_core else proposer_live
        )
        result: dict[str, Any] = {
            "case_id": case_id,
            "set": "CORE" if is_core else "HELDOUT",
            "synthetic": True,
            "question_text": case["question_text"],
            "frozen_answers": case["answer_pool"],
            "initial_proposal_source": "FROZEN_STAGE1B" if is_core else "LIVE_STAGE1C_PROPOSER",
            "initial": None,
            "critical_answer": critical_by_id[case_id].get("critical_answer"),
            "after_critical": None,
        }
        initial = arbitrate_stage1c_request(
            _request_payload(f"{case_id}-initial", case["question_text"], turns),
            proposer=initial_proposer,
            critic=critic_live,
        )
        result["initial"] = initial
        if initial["status"] == "ASK_CRITICAL" and result["critical_answer"]:
            turns.append(
                {
                    "question": initial["next_question"],
                    "answer": result["critical_answer"],
                    "kind": "CRITICAL_ANSWER",
                }
            )
            result["after_critical"] = arbitrate_stage1c_request(
                _request_payload(f"{case_id}-after", case["question_text"], turns),
                proposer=proposer_live,
                critic=critic_live,
            )

        expected_initial = "ASK_CRITICAL" if is_core else (
            "CONFIRM"
            if "READY" in heldout_expected_by_id[case_id]["acceptable_critic_decision"]
            else "ASK_CRITICAL"
        )
        result["machine_gates"] = {
            "initial_status_matches_frozen_expectation": initial["status"] == expected_initial,
            "veto_has_exactly_one_question": (
                initial["status"] != "ASK_CRITICAL"
                or bool(initial["next_question"])
                and initial["next_question"].count("？") + initial["next_question"].count("?") == 1
            ),
            "veto_hides_hypothesis": initial["status"] != "ASK_CRITICAL" or initial["hypothesis"] is None,
            "review_error_fails_closed": initial["status"] != "REVIEW_ERROR" or initial["hypothesis"] is None,
            "after_one_answer_confirms_or_stops": (
                result["after_critical"] is None
                if initial["status"] != "ASK_CRITICAL"
                else result["after_critical"] is not None
                and result["after_critical"]["status"] in {"CONFIRM", "INSUFFICIENT_TO_CONFIRM"}
            ),
            "no_second_question": not result["after_critical"]
            or result["after_critical"].get("next_question") is None
            or result["after_critical"]["status"] == "CONFIRM",
        }
        results.append(result)

    metrics: list[dict[str, Any]] = []
    for result in results:
        for phase in ("initial", "after_critical"):
            response = result.get(phase)
            if not response:
                continue
            for metric_key in ("proposer_metrics", "critic_metrics"):
                metric = response.get(metric_key)
                if metric and metric.get("model") != "frozen-stage1b-no-new-call":
                    metrics.append(metric)
    gate_values = [
        value for result in results for value in result["machine_gates"].values()
    ]
    payload = {
        "run_id": f"GUANXIANG_STAGE1C_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "scope": "STAGE1C_SINGLE_FROZEN_RUN",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model,
        "contract_version": CONTRACT_VERSION,
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256,
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256,
        "contract_file_sha256": _sha(contract_path),
        "core_initial_proposal_policy": "REUSE_EXACT_STAGE1B_OUTPUT_NO_REGENERATION",
        "heldout_run_number": 1,
        "model_retry_count": 0,
        "cases": results,
        "aggregate": {
            "live_model_call_count": len(metrics),
            "input_tokens": sum(item.get("input_tokens") or 0 for item in metrics),
            "output_tokens": sum(item.get("output_tokens") or 0 for item in metrics),
            "total_tokens": sum(item.get("total_tokens") or 0 for item in metrics),
            "latency_total_ms": sum(item.get("latency_ms") or 0 for item in metrics),
            "estimated_cost_usd": None,
            "all_machine_gates_pass": bool(gate_values) and all(gate_values),
        },
    }
    path = stage1c / "runs" / f"stage1c_single_run_{payload['run_id'].lower()}.json"
    _write(path, payload)
    return path


def main() -> None:
    print(run(Path.cwd().resolve(), os.getenv("ABALO_STAGE1C_MODEL", DEFAULT_MODEL)))


if __name__ == "__main__":
    main()
