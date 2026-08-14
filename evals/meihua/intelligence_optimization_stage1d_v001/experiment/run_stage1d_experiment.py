"""Run the only frozen Stage 1D critic-first experiment."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
)
from evals.meihua.intelligence_optimization_stage1d_v001.experiment.critic_first_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_PROMPT_SHA256,
    PROPOSER_PROMPT_SHA256,
    OpenAICritic,
    OpenAIProposer,
    arbitrate_stage1d_request,
)

STAGE0_REL = Path("evals/meihua/intelligence_diagnostic_v001")
STAGE1B_REL = Path("evals/meihua/intelligence_optimization_stage1b_v001")
STAGE1D_REL = Path("evals/meihua/intelligence_optimization_stage1d_v001")
MAX_EXPERIMENT_CALLS = 30

CORE_DIMENSIONS = {
    "GXID-M01": "DECISION_AXIS",
    "GXID-M02": "DECISION_AXIS",
    "GXID-M03": "AGENCY_AUTHORITY",
    "GXID-M04": "MOTIVE_COST",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError as exc:
        raise RuntimeError("Stage 1D has already been run") from exc


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


def _request_payload(case_id: str, question_text: str, turns: list[dict[str, Any]]):
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": case_id,
        "question_text": question_text,
        "turns": turns,
        "locale": "zh-CN",
    }


def _expected_verdict(expectation: dict[str, Any]) -> str:
    values = {str(value).strip().upper() for value in expectation["acceptable_critic_decision"]}
    ready_values = {"READY", "ALLOW", "ALLOW_CONFIRM"}
    ask_values = {"ASK_ONE", "VETO", "VETO_ASK"}
    categories = set()
    if values and values <= ready_values:
        categories.add("READY")
    if values and values <= ask_values:
        categories.add("ASK_ONE")
    if len(categories) != 1:
        raise RuntimeError(f"invalid acceptable_critic_decision: {sorted(values)}")
    return categories.pop()


def _review_verdict(response: dict[str, Any]) -> str | None:
    review = response.get("review")
    return review.get("verdict") if review else None


def _review_dimension(response: dict[str, Any]) -> str | None:
    review = response.get("review")
    return review.get("dimension") if review else None


def _records(response: dict[str, Any]) -> list[dict[str, Any]]:
    return response.get("call_records") or []


def _validate_frozen_assets(stage1d: Path, manifest: dict[str, Any]) -> None:
    contract = stage1d / "experiment/critic_first_experiment_v1.py"
    runner = stage1d / "experiment/run_stage1d_experiment.py"
    checks = {
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256.upper(),
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256.upper(),
        "contract_file_sha256": _sha(contract),
        "runner_file_sha256": _sha(runner),
        "core_inputs_sha256": _sha(stage1d.parent / manifest["core_inputs"]),
        "core_critical_answers_sha256": _sha(
            stage1d.parent / manifest["core_critical_answers"]
        ),
        "heldout_cases_sha256": _sha(stage1d / manifest["heldout_cases"]),
        "heldout_expectations_sha256": _sha(stage1d / manifest["heldout_expectations"]),
        "heldout_critical_answers_sha256": _sha(
            stage1d / manifest["heldout_critical_answers"]
        ),
    }
    for key, actual in checks.items():
        if str(manifest[key]).upper() != actual:
            raise RuntimeError(f"frozen hash mismatch: {key}")


def _validate_dataset_assets(
    stage0: Path,
    stage1b: Path,
    stage1d: Path,
    manifest: dict[str, Any],
) -> None:
    core = _load(stage0 / "guided_intake_synthetic_inputs.json")["cases"]
    core_ids = [item["case_id"] for item in core]
    if set(core_ids) != set(CORE_DIMENSIONS) or len(core_ids) != len(set(core_ids)):
        raise RuntimeError("core cases must be exactly unique M01-M04")
    if any(len(item.get("answer_pool") or []) != 4 for item in core):
        raise RuntimeError("every core case must have four frozen answers")
    core_answers = _load(stage1b / "cases/development_critical_answers.json")["cases"]
    core_answer_ids = [item["case_id"] for item in core_answers]
    if set(core_answer_ids) != set(core_ids) or len(core_answer_ids) != len(set(core_answer_ids)):
        raise RuntimeError("core critical answers must cover M01-M04 exactly once")
    if any(not str(item.get("critical_answer") or "").strip() for item in core_answers):
        raise RuntimeError("every core case requires a frozen critical answer")

    heldout = _load(stage1d / manifest["heldout_cases"])["cases"]
    expectations = _load(stage1d / manifest["heldout_expectations"])["expectations"]
    heldout_answers = _load(stage1d / manifest["heldout_critical_answers"])["cases"]
    heldout_ids = [item["case_id"] for item in heldout]
    expectation_ids = [item["case_id"] for item in expectations]
    answer_ids = [item["case_id"] for item in heldout_answers]
    if len(heldout_ids) != 6 or len(heldout_ids) != len(set(heldout_ids)):
        raise RuntimeError("heldout must contain exactly six unique cases")
    if set(heldout_ids) & set(core_ids):
        raise RuntimeError("heldout ids overlap core ids")
    if set(expectation_ids) != set(heldout_ids) or len(expectation_ids) != len(set(expectation_ids)):
        raise RuntimeError("heldout expectations must cover every case exactly once")
    if set(answer_ids) != set(heldout_ids) or len(answer_ids) != len(set(answer_ids)):
        raise RuntimeError("heldout answer records must cover every case exactly once")
    if any(len(item.get("answer_pool") or []) != 4 for item in heldout):
        raise RuntimeError("every heldout case must have four frozen answers")

    answers_by_id = {item["case_id"]: item for item in heldout_answers}
    verdicts = []
    allowed_dimensions = {"DECISION_AXIS", "STATED_PREMISE", "AGENCY_AUTHORITY", "MOTIVE_COST"}
    for expectation in expectations:
        verdict = _expected_verdict(expectation)
        verdicts.append(verdict)
        answer = answers_by_id[expectation["case_id"]]
        dimension = expectation.get("expected_dimension")
        if verdict == "ASK_ONE":
            if dimension not in allowed_dimensions:
                raise RuntimeError("ASK_ONE heldout requires a valid expected dimension")
            if not str(answer.get("critical_answer") or "").strip():
                raise RuntimeError("ASK_ONE heldout requires a sealed critical answer")
        elif answer.get("critical_answer") is not None:
            raise RuntimeError("READY heldout cannot have a critical answer")
    if verdicts.count("ASK_ONE") != 3 or verdicts.count("READY") != 3:
        raise RuntimeError("heldout must balance exactly three ASK_ONE and three READY cases")


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    usages = [record.get("usage") for record in records if record.get("usage")]
    sequences = [record["sequence"] for record in records]
    return {
        "attempted_call_count": len(records),
        "successful_call_count": sum(record["outcome"] == "SUCCESS" for record in records),
        "failed_call_count": sum(record["outcome"] != "SUCCESS" for record in records),
        "input_tokens": sum(usage.get("input_tokens") or 0 for usage in usages),
        "output_tokens": sum(usage.get("output_tokens") or 0 for usage in usages),
        "total_tokens": sum(usage.get("total_tokens") or 0 for usage in usages),
        "latency_total_ms": sum(record.get("latency_ms") or 0 for record in records),
        "usage_missing_count": sum(
            record.get("usage") is None
            or any(
                record["usage"].get(key) is None
                for key in ("input_tokens", "output_tokens", "total_tokens")
            )
            for record in records
        ),
        "sequence_is_contiguous": sequences == list(range(1, len(records) + 1)),
        "within_call_budget": len(records) <= MAX_EXPERIMENT_CALLS,
        "estimated_cost_usd": None,
    }


def run(repo_root: Path, model: str) -> Path:
    stage0 = repo_root / STAGE0_REL
    stage1b = repo_root / STAGE1B_REL
    stage1d = repo_root / STAGE1D_REL
    manifest = _load(stage1d / "manifest.json")
    _validate_frozen_assets(stage1d, manifest)
    _validate_dataset_assets(stage0, stage1b, stage1d, manifest)

    runs_dir = stage1d / "runs"
    marker = runs_dir / "stage1d_run_started.json"
    if list(runs_dir.glob("stage1d_single_run_*.json")):
        raise RuntimeError("Stage 1D has already been run")

    now = datetime.now(UTC)
    run_id = f"GUANXIANG_STAGE1D_{now.strftime('%Y%m%dT%H%M%SZ')}"
    result_path = runs_dir / f"stage1d_single_run_{run_id.lower()}.json"
    _write_exclusive(
        marker,
        {
            "run_id": run_id,
            "started_at": now.isoformat(),
            "model": model,
            "contract_version": CONTRACT_VERSION,
            "retry_permitted": False,
            "max_experiment_calls": MAX_EXPERIMENT_CALLS,
        },
    )

    payload: dict[str, Any] = {
        "run_id": run_id,
        "scope": "STAGE1D_SINGLE_FROZEN_RUN",
        "generated_at": now.isoformat(),
        "run_status": "IN_PROGRESS",
        "model": model,
        "contract_version": CONTRACT_VERSION,
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256,
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256,
        "contract_file_sha256": _sha(stage1d / "experiment/critic_first_experiment_v1.py"),
        "runner_file_sha256": _sha(stage1d / "experiment/run_stage1d_experiment.py"),
        "heldout_run_number": 1,
        "model_retry_count": 0,
        "max_experiment_calls": MAX_EXPERIMENT_CALLS,
        "cases": [],
        "aggregate": _aggregate([]),
    }
    _write(result_path, payload)

    try:
        stage0_inputs = _load(stage0 / "guided_intake_synthetic_inputs.json")
        stage0_baselines = _load(stage0 / "baselines/current_guided_intake_snapshots.json")
        baselines = {item["case_id"]: item for item in stage0_baselines["cases"]}
        core_answers_raw = _load(stage1b / "cases/development_critical_answers.json")
        core_answers = {item["case_id"]: item for item in core_answers_raw["cases"]}
        heldout = _load(stage1d / manifest["heldout_cases"])
        heldout_expectations_raw = _load(stage1d / manifest["heldout_expectations"])
        heldout_expectations = {
            item["case_id"]: item for item in heldout_expectations_raw["expectations"]
        }
        heldout_answers_raw = _load(stage1d / manifest["heldout_critical_answers"])
        heldout_answers = {item["case_id"]: item for item in heldout_answers_raw["cases"]}
        cases = stage0_inputs["cases"] + heldout["cases"]
        critic = OpenAICritic(model=model)
        proposer = OpenAIProposer(model=model)
        all_records: list[dict[str, Any]] = []

        for case in cases:
            case_id = case["case_id"]
            is_core = case_id in CORE_DIMENSIONS
            expectation = None if is_core else heldout_expectations[case_id]
            expected_verdict = "ASK_ONE" if is_core else _expected_verdict(expectation)
            expected_dimension = (
                CORE_DIMENSIONS[case_id] if is_core else expectation.get("expected_dimension")
            )
            critical_answer = (
                core_answers[case_id].get("critical_answer")
                if is_core
                else heldout_answers.get(case_id, {}).get("critical_answer")
            )
            turns = _initial_turns(case_id, baselines, case["answer_pool"])
            if len(all_records) + 2 > MAX_EXPERIMENT_CALLS:
                raise RuntimeError("insufficient call budget before initial arbitration")
            initial = arbitrate_stage1d_request(
                _request_payload(f"{case_id}-initial", case["question_text"], turns),
                call_sequence_start=len(all_records) + 1,
                critic=critic,
                proposer=proposer,
            )
            initial_records = _records(initial)
            all_records.extend(initial_records)
            after_critical = None
            if is_core and initial["status"] == "ASK_CRITICAL" and critical_answer:
                turns.append(
                    {
                        "question": initial["next_question"],
                        "answer": critical_answer,
                        "kind": "CRITICAL_ANSWER",
                    }
                )
                if len(all_records) + 2 > MAX_EXPERIMENT_CALLS:
                    raise RuntimeError("insufficient call budget before critical-answer arbitration")
                after_critical = arbitrate_stage1d_request(
                    _request_payload(f"{case_id}-after", case["question_text"], turns),
                    call_sequence_start=len(all_records) + 1,
                    critic=critic,
                    proposer=proposer,
                )
                all_records.extend(_records(after_critical))

            result = {
                "case_id": case_id,
                "set": "CORE" if is_core else "HELDOUT",
                "synthetic": True,
                "question_text": case["question_text"],
                "frozen_answers": case["answer_pool"],
                "expected_initial_verdict": expected_verdict,
                "expected_dimension": expected_dimension,
                "initial": initial,
                "critical_answer": critical_answer if is_core else None,
                "after_critical": after_critical,
                "machine_gates": {
                    "initial_verdict_matches": _review_verdict(initial) == expected_verdict,
                    "initial_dimension_matches": (
                        expected_verdict != "ASK_ONE"
                        or _review_dimension(initial) == expected_dimension
                    ),
                    "veto_has_one_question": (
                        initial["status"] != "ASK_CRITICAL"
                        or bool(initial["next_question"])
                        and initial["next_question"].count("？")
                        + initial["next_question"].count("?")
                        == 1
                    ),
                    "veto_did_not_call_proposer": (
                        initial["status"] != "ASK_CRITICAL"
                        or all(record["role"] == "CRITIC" for record in initial_records)
                    ),
                    "no_review_error": initial["status"] != "REVIEW_ERROR"
                    and (
                        after_critical is None
                        or after_critical["status"] != "REVIEW_ERROR"
                    ),
                    "core_veto_resolves_to_confirm": (
                        not is_core
                        or after_critical is not None
                        and after_critical["status"] == "CONFIRM"
                    ),
                    "ready_confirms_without_question": (
                        expected_verdict != "READY"
                        or initial["status"] == "CONFIRM"
                    ),
                },
            }
            payload["cases"].append(result)
            payload["aggregate"] = _aggregate(all_records)
            if len(all_records) > MAX_EXPERIMENT_CALLS:
                raise RuntimeError("experiment call budget exceeded")
            _write(result_path, payload)

        gate_values = [
            value
            for case_result in payload["cases"]
            for value in case_result["machine_gates"].values()
        ]
        payload["aggregate"] = _aggregate(all_records)
        payload["aggregate"]["all_mechanical_gates_pass"] = (
            bool(gate_values)
            and all(gate_values)
            and payload["aggregate"]["within_call_budget"]
            and payload["aggregate"]["sequence_is_contiguous"]
            and payload["aggregate"]["usage_missing_count"] == 0
        )
        payload["aggregate"]["semantic_review_required"] = True
        payload["run_status"] = "COMPLETED"
        payload["completed_at"] = datetime.now(UTC).isoformat()
        _write(result_path, payload)
        return result_path
    except Exception as exc:
        payload["run_status"] = "INVALID_RUN_CLOSE_COMPLETE"
        payload["fatal_error"] = f"{type(exc).__name__}:{exc}"
        payload["completed_at"] = datetime.now(UTC).isoformat()
        _write(result_path, payload)
        raise


def main() -> None:
    print(run(Path.cwd().resolve(), os.getenv("ABALO_STAGE1D_MODEL", DEFAULT_MODEL)))


if __name__ == "__main__":
    main()
