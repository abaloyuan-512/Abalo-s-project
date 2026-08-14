"""Run the frozen three-path Stage 1E service canary."""

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
    _validate_proposal,
    _validate_review,
)
from evals.meihua.intelligence_optimization_stage1e_v001.experiment.critic_first_wire_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_PROMPT_SHA256,
    CRITIC_WIRE_SCHEMA_SHA256,
    PROPOSER_PROMPT_SHA256,
    PROPOSER_WIRE_SCHEMA_SHA256,
    OpenAICritic,
    OpenAIProposer,
    Stage1ERequest,
    is_schema_compatibility_error,
)

STAGE1E_REL = Path("evals/meihua/intelligence_optimization_stage1e_v001")


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
        raise RuntimeError("Stage 1E canary has already been run") from exc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _request(case: dict[str, Any]) -> Stage1ERequest:
    return Stage1ERequest.model_validate(
        {
            "contract_version": CONTRACT_VERSION,
            "session_id": case["case_id"],
            "question_text": case["question_text"],
            "turns": [
                {
                    "question": f"冻结canary背景补充{index + 1}",
                    "answer": answer,
                    "kind": "FROZEN_CONTEXT",
                }
                for index, answer in enumerate(case["answer_pool"])
            ],
            "locale": "zh-CN",
        }
    )


def _validate_frozen(stage1e: Path, manifest: dict[str, Any]) -> None:
    checks = {
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256.upper(),
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256.upper(),
        "critic_wire_schema_sha256": CRITIC_WIRE_SCHEMA_SHA256.upper(),
        "proposer_wire_schema_sha256": PROPOSER_WIRE_SCHEMA_SHA256.upper(),
        "contract_file_sha256": _sha(stage1e / "experiment/critic_first_wire_experiment_v1.py"),
        "canary_runner_sha256": _sha(stage1e / "experiment/run_stage1e_canary.py"),
        "canary_inputs_sha256": _sha(stage1e / "canary/canary_inputs.json"),
        "test_file_sha256": _sha(stage1e.parent.parent.parent / "tests/test_stage1e_wire_experiment_v1.py"),
    }
    for key, actual in checks.items():
        if str(manifest[key]).upper() != actual:
            raise RuntimeError(f"frozen canary hash mismatch: {key}")


def _usage_complete(record: dict[str, Any]) -> bool:
    usage = record.get("usage")
    return bool(usage) and all(
        usage.get(key) is not None for key in ("input_tokens", "output_tokens", "total_tokens")
    )


def _validate_canary_inputs(document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("synthetic") is not True:
        raise RuntimeError("canary inputs must be explicitly synthetic")
    if document.get("not_for_capability_scoring") is not True:
        raise RuntimeError("canary inputs must be excluded from capability scoring")
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("canary inputs require a cases list")
    expected = [
        ("CANARY-CRITIC-ASK", "CRITIC", "ASK_ONE"),
        ("CANARY-CRITIC-READY", "CRITIC", "READY"),
        ("CANARY-PROPOSER", "PROPOSER", None),
    ]
    actual = [
        (case.get("case_id"), case.get("role"), case.get("expected_verdict"))
        for case in cases
    ]
    if actual != expected:
        raise RuntimeError("canary inputs must contain the frozen three paths in order")
    if any(len(case.get("answer_pool") or []) != 4 for case in cases):
        raise RuntimeError("every canary path requires four frozen answers")
    if any(not str(case.get("question_text") or "").strip() for case in cases):
        raise RuntimeError("every canary path requires a question")
    return cases


def run(repo_root: Path, model: str) -> Path:
    stage1e = repo_root / STAGE1E_REL
    manifest = _load(stage1e / "manifest.json")
    _validate_frozen(stage1e, manifest)
    if model != manifest["canary_model"]:
        raise RuntimeError("canary model differs from frozen model")
    inputs = _validate_canary_inputs(_load(stage1e / "canary/canary_inputs.json"))
    canary_dir = stage1e / "canary"
    marker = canary_dir / "stage1e_canary_started.json"
    if list(canary_dir.glob("stage1e_canary_run_*.json")):
        raise RuntimeError("Stage 1E canary has already been run")
    now = datetime.now(UTC)
    run_id = f"GUANXIANG_STAGE1E_CANARY_{now.strftime('%Y%m%dT%H%M%SZ')}"
    result_path = canary_dir / f"stage1e_canary_run_{run_id.lower()}.json"
    _write_exclusive(
        marker,
        {
            "run_id": run_id,
            "started_at": now.isoformat(),
            "model": model,
            "retry_permitted": False,
        },
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "run_status": "IN_PROGRESS",
        "model": model,
        "model_retry_count": 0,
        "critic_prompt_sha256": CRITIC_PROMPT_SHA256,
        "proposer_prompt_sha256": PROPOSER_PROMPT_SHA256,
        "critic_wire_schema_sha256": CRITIC_WIRE_SCHEMA_SHA256,
        "proposer_wire_schema_sha256": PROPOSER_WIRE_SCHEMA_SHA256,
        "steps": [],
    }
    _write(result_path, payload)
    critic = OpenAICritic(model=model)
    proposer = OpenAIProposer(model=model)
    sequence = 1

    for case in inputs:
        request = _request(case)
        if case["role"] == "CRITIC":
            attempt = critic.generate(request, call_sequence=sequence)
            step = {"case_id": case["case_id"], "role": "CRITIC"}
            sequence += 1
            if attempt.output is None:
                record = attempt.record.model_dump(mode="json")
                step["record"] = record
                step["passed"] = False
                step["failure"] = attempt.record.outcome
                payload["steps"].append(step)
                payload["run_status"] = (
                    "CANARY_SCHEMA_FAILED"
                    if is_schema_compatibility_error(attempt.record)
                    else "CANARY_FAILED"
                )
                payload["global_short_circuit"] = True
                break
            review = attempt.output.to_internal()
            try:
                _validate_review(review, request)
            except Exception as exc:
                attempt.record.outcome = "SEMANTIC_VALIDATION_ERROR"
                attempt.record.error_detail = f"{type(exc).__name__}:{exc}"
                step["validation_error"] = f"{type(exc).__name__}:{exc}"
            record = attempt.record.model_dump(mode="json")
            step["record"] = record
            verdict_matches = review.verdict == case["expected_verdict"]
            usage_complete = _usage_complete(record)
            passed = (
                attempt.record.outcome == "SUCCESS"
                and verdict_matches
                and usage_complete
            )
            if attempt.record.outcome == "SEMANTIC_VALIDATION_ERROR":
                step["failure"] = "SEMANTIC_VALIDATION_ERROR"
            elif not verdict_matches:
                step["failure"] = "VERDICT_MISMATCH"
            elif not usage_complete:
                step["failure"] = "USAGE_INCOMPLETE"
            step["wire_output"] = attempt.output.model_dump(mode="json")
            step["internal_verdict"] = review.verdict
            step["passed"] = passed
        else:
            attempt = proposer.generate(request, call_sequence=sequence)
            step = {"case_id": case["case_id"], "role": "PROPOSER"}
            sequence += 1
            if attempt.output is None:
                record = attempt.record.model_dump(mode="json")
                step["record"] = record
                step["passed"] = False
                step["failure"] = attempt.record.outcome
                payload["steps"].append(step)
                payload["run_status"] = (
                    "CANARY_SCHEMA_FAILED"
                    if is_schema_compatibility_error(attempt.record)
                    else "CANARY_FAILED"
                )
                payload["global_short_circuit"] = True
                break
            proposal = attempt.output.to_internal()
            try:
                _validate_proposal(proposal, request)
            except Exception as exc:
                attempt.record.outcome = "SEMANTIC_VALIDATION_ERROR"
                attempt.record.error_detail = f"{type(exc).__name__}:{exc}"
                step["validation_error"] = f"{type(exc).__name__}:{exc}"
            record = attempt.record.model_dump(mode="json")
            step["record"] = record
            usage_complete = _usage_complete(record)
            passed = attempt.record.outcome == "SUCCESS" and usage_complete
            if attempt.record.outcome == "SEMANTIC_VALIDATION_ERROR":
                step["failure"] = "SEMANTIC_VALIDATION_ERROR"
            elif not usage_complete:
                step["failure"] = "USAGE_INCOMPLETE"
            step["wire_output"] = attempt.output.model_dump(mode="json")
            step["hypothesis"] = proposal.candidate_hypothesis.model_dump(mode="json")
            step["passed"] = passed
        payload["steps"].append(step)
        _write(result_path, payload)
        if not step["passed"]:
            payload["run_status"] = "CANARY_FAILED"
            payload["global_short_circuit"] = True
            break

    if len(payload["steps"]) == 3 and all(step["passed"] for step in payload["steps"]):
        payload["run_status"] = "CANARY_PASSED"
        payload["global_short_circuit"] = False
    elif payload["run_status"] == "IN_PROGRESS":
        payload["run_status"] = "CANARY_FAILED"
        payload["global_short_circuit"] = True
    payload["completed_at"] = datetime.now(UTC).isoformat()
    payload["attempted_call_count"] = len(payload["steps"])
    payload["wire_successful_call_count"] = sum(
        step["record"]["outcome"] in {"SUCCESS", "SEMANTIC_VALIDATION_ERROR"}
        for step in payload["steps"]
    )
    payload["validated_path_success_count"] = sum(step["passed"] for step in payload["steps"])
    payload["successful_call_count"] = payload["validated_path_success_count"]
    payload["all_three_paths_pass"] = payload["run_status"] == "CANARY_PASSED"
    _write(result_path, payload)
    return result_path


def main() -> None:
    print(run(Path.cwd().resolve(), os.getenv("ABALO_STAGE1E_MODEL", DEFAULT_MODEL)))


if __name__ == "__main__":
    main()
