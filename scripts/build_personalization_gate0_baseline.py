"""Build the deterministic Gate 0 personalization baseline; never calls a model."""

from __future__ import annotations

import hashlib
import json
import platform
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_question_context_v1 import DecisionStage, KeyUncertainty
from abalo_iching.application.sites_structured_question_v1 import ALLOWED_GOALS, TimeHorizon
from abalo_iching.application.sites_meihua_service_v3 import process_sites_meihua_v3_request

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals" / "meihua" / "personalization_gate0_v001"
DATASET_PATH = EVAL_DIR / "fixed_cases.json"
GENERATOR_VERSION = "GUANXIANG_PERSONALIZATION_GATE0_BUILDER_V001"
PRODUCT_BEHAVIOR_BASELINE_COMMIT = "7e96712c1ffc2c3209063c0efd60c33f8f1916ef"
GOVERNANCE_WORKING_HEAD_COMMIT = "e75594208643232ae35134a70b41be1aeea74229"
SOURCE_BRANCH = "codex/mvp-runnable-baseline"
SITES_BASELINE_VERSION = "v16"

REPORT_FIELDS = (
    "answer",
    "what_it_means",
    "priority",
    "continue_signals",
    "pause_signals",
    "next_action",
    "evidence_path",
    "boundary_note",
)
CONCEPTS = (
    "观察",
    "验证",
    "反馈",
    "可逆",
    "最小",
    "投入",
    "边界",
    "调整空间",
    "复盘",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        stream.write("\n")


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_value(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixed_clock(dataset: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(dataset["fixed_clock"])


def _request(
    dataset: dict[str, Any],
    *,
    request_id: str,
    question_text: str,
    question_domain: str,
    decision_goal: str,
    time_horizon: str,
    decision_stage: str,
    key_uncertainty: str,
    numbers: list[int],
) -> dict[str, Any]:
    return {
        "contract_version": dataset["contract_version"],
        "request_id": request_id,
        "question_text": question_text,
        "question_domain": question_domain,
        "decision_goal": decision_goal,
        "time_horizon": time_horizon,
        "decision_stage": decision_stage,
        "key_uncertainty": key_uncertainty,
        "numbers": numbers,
        "locale": "zh-CN",
        "client_timestamp": dataset["fixed_clock"],
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "question_text_not_evidence": True,
        },
    }


def _process(dataset: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    fixed_now = _fixed_clock(dataset)
    response = process_sites_meihua_v3_request(request, clock=lambda: fixed_now)
    if response["status"] != "SUCCESS":
        raise RuntimeError(f"Gate 0 fixture failed: {request['request_id']}")
    return response


def _sweep_requests(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    sweep = dataset["chart_sensitivity_sweep"]
    upper_start, upper_end = sweep["upper_number_range"]
    lower_start, lower_end = sweep["lower_number_range"]
    moving_start, moving_end = sweep["moving_number_range"]
    requests: list[dict[str, Any]] = []
    for upper in range(upper_start, upper_end + 1):
        for lower in range(lower_start, lower_end + 1):
            for moving in range(moving_start, moving_end + 1):
                requests.append(
                    _request(
                        dataset,
                        request_id=f"{sweep['case_id_prefix']}-{upper}-{lower}-{moving}",
                        question_text=sweep["question_text"],
                        question_domain=sweep["question_domain"],
                        decision_goal=sweep["decision_goal"],
                        time_horizon=sweep["time_horizon"],
                        decision_stage=sweep["decision_stage"],
                        key_uncertainty=sweep["key_uncertainty"],
                        numbers=[upper, lower, moving],
                    )
                )
    return requests


def _field_key(report: dict[str, Any], field: str) -> str:
    return _stable_json(report[field])


def _chart_sensitivity(dataset: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    responses = [_process(dataset, request) for request in _sweep_requests(dataset)]
    results = [response["deterministic_result"] for response in responses]
    reports = [result["clarity_report"] for result in results]
    field_counts = {
        field: len({_field_key(report, field) for report in reports})
        for field in REPORT_FIELDS
    }
    conclusion_distribution = Counter(
        result["deterministic_conclusion"]["conclusion_level"] for result in results
    )
    priority_distribution = Counter(report["priority"] for report in reports)
    next_action_distribution = Counter(report["next_action"] for report in reports)
    report_texts = [_stable_json(report) for report in reports]
    concept_report_counts = {
        concept: sum(concept in text for text in report_texts) for concept in CONCEPTS
    }
    chart_signatures = {
        (
            result["base_hexagram"]["king_wen_number"],
            result["changed_hexagram"]["king_wen_number"],
            result["moving_line"],
        )
        for result in results
    }
    summary = {
        "sweep_case_count": len(results),
        "distinct_chart_signatures": len(chart_signatures),
        "distinct_base_hexagrams": len(
            {result["base_hexagram"]["king_wen_number"] for result in results}
        ),
        "distinct_changed_hexagrams": len(
            {result["changed_hexagram"]["king_wen_number"] for result in results}
        ),
        "field_distinct_counts": field_counts,
        "conclusion_distribution": dict(sorted(conclusion_distribution.items())),
        "priority_distribution": dict(sorted(priority_distribution.items())),
        "next_action_distribution": dict(sorted(next_action_distribution.items())),
        "concept_report_counts": concept_report_counts,
        "all_charts_share_one_next_action": field_counts["next_action"] == 1,
        "all_charts_share_one_continue_signal_set": field_counts["continue_signals"] == 1,
        "all_charts_share_one_pause_signal_set": field_counts["pause_signals"] == 1,
        "complete_sweep_sha256": _sha256_value(results),
    }
    return summary, results


def _question_text_sensitivity(
    dataset: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pair_results: list[dict[str, Any]] = []
    pair_outputs: list[dict[str, Any]] = []
    for pair in dataset["question_text_pairs"]:
        common = {
            "question_domain": pair["question_domain"],
            "decision_goal": pair["decision_goal"],
            "time_horizon": pair["time_horizon"],
            "decision_stage": pair["decision_stage"],
            "key_uncertainty": pair["key_uncertainty"],
            "numbers": pair["numbers"],
        }
        response_a = _process(
            dataset,
            _request(
                dataset,
                request_id=f"{pair['pair_id']}-A",
                question_text=pair["question_a"],
                **common,
            ),
        )
        response_b = _process(
            dataset,
            _request(
                dataset,
                request_id=f"{pair['pair_id']}-B",
                question_text=pair["question_b"],
                **common,
            ),
        )
        report_a = response_a["deterministic_result"]["clarity_report"]
        report_b = response_b["deterministic_result"]["clarity_report"]
        pair_results.append(
            {
                "pair_id": pair["pair_id"],
                "question_a": pair["question_a"],
                "question_b": pair["question_b"],
                "clarity_report_a_sha256": _sha256_value(report_a),
                "clarity_report_b_sha256": _sha256_value(report_b),
                "clarity_reports_identical": report_a == report_b,
                "request_hashes_different": response_a["audit"]["request_hash"]
                != response_b["audit"]["request_hash"],
                "question_text_used_for_calculation": response_a["audit"][
                    "question_text_used_for_calculation"
                ],
            }
        )
        pair_outputs.append(
            {
                "pair_id": pair["pair_id"],
                "request_a": {
                    "question_text": pair["question_a"],
                    **common,
                },
                "request_b": {
                    "question_text": pair["question_b"],
                    **common,
                },
                "request_hash_a": response_a["audit"]["request_hash"],
                "request_hash_b": response_b["audit"]["request_hash"],
                "clarity_report_a": report_a,
                "clarity_report_b": report_b,
            }
        )
    summary = {
        "pair_count": len(pair_results),
        "identical_clarity_report_pair_count": sum(
            item["clarity_reports_identical"] for item in pair_results
        ),
        "all_question_changes_leave_clarity_report_unchanged": all(
            item["clarity_reports_identical"] for item in pair_results
        ),
        "pairs": pair_results,
    }
    details = {
        "dataset_version": dataset["dataset_version"],
        "pair_count": len(pair_outputs),
        "pairs": pair_outputs,
    }
    return summary, details


def _structured_context_sensitivity(dataset: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for domain, goals in ALLOWED_GOALS.items():
        for goal in sorted(goals, key=lambda item: item.value):
            for horizon in TimeHorizon:
                for stage in DecisionStage:
                    for uncertainty in KeyUncertainty:
                        request = _request(
                            dataset,
                            request_id=(
                                f"G0-CONTEXT-{domain.value}-{goal.value}-{horizon.value}-"
                                f"{stage.value}-{uncertainty.value}"
                            ),
                            question_text="我现在应该怎样判断下一步行动？",
                            question_domain=domain.value,
                            decision_goal=goal.value,
                            time_horizon=horizon.value,
                            decision_stage=stage.value,
                            key_uncertainty=uncertainty.value,
                            numbers=[7, 8, 9],
                        )
                        response = _process(dataset, request)
                        report = response["deterministic_result"]["clarity_report"]
                        records.append(
                            {
                                "domain": domain.value,
                                "goal": goal.value,
                                "horizon": horizon.value,
                                "stage": stage.value,
                                "uncertainty": uncertainty.value,
                                "next_action": report["next_action"],
                                "continue_signals": report["continue_signals"],
                                "pause_signals": report["pause_signals"],
                            }
                        )
    action_by_non_goal_key: dict[tuple[str, str, str, str], set[str]] = {}
    for record in records:
        key = (
            record["domain"],
            record["horizon"],
            record["stage"],
            record["uncertainty"],
        )
        action_by_non_goal_key.setdefault(key, set()).add(record["next_action"])
    return {
        "valid_structured_context_count": len(records),
        "distinct_next_actions": len({record["next_action"] for record in records}),
        "distinct_continue_signal_sets": len(
            {_stable_json(record["continue_signals"]) for record in records}
        ),
        "distinct_pause_signal_sets": len(
            {_stable_json(record["pause_signals"]) for record in records}
        ),
        "decision_goal_changes_next_action": any(
            len(actions) > 1 for actions in action_by_non_goal_key.values()
        ),
        "next_action_dependency": [
            "question_domain",
            "decision_stage",
            "key_uncertainty",
            "time_horizon",
        ],
        "next_action_excluded_inputs": [
            "question_text",
            "decision_goal",
            "base_hexagram",
            "changed_hexagram",
            "mutual_hexagram",
            "moving_line",
            "body_use",
            "seasonal_strength",
        ],
    }


def _representative_outputs(
    dataset: dict[str, Any], sweep_results: list[dict[str, Any]]
) -> dict[str, Any]:
    by_numbers = {
        tuple(result["input_numbers"]): result
        for result in sweep_results
    }
    cases: list[dict[str, Any]] = []
    for item in dataset["representative_cases"]:
        numbers = tuple(item["numbers"])
        result = by_numbers[numbers]
        cases.append(
            {
                "case_id": item["case_id"],
                "numbers": item["numbers"],
                "base_hexagram": result["base_hexagram"],
                "changed_hexagram": result["changed_hexagram"],
                "moving_line": result["moving_line"],
                "body_use": result["body_use"],
                "seasonal_strength": result["seasonal_strength"],
                "deterministic_conclusion": result["deterministic_conclusion"],
                "clarity_report": result["clarity_report"],
            }
        )
    return {
        "dataset_version": dataset["dataset_version"],
        "product_behavior_baseline_commit": PRODUCT_BEHAVIOR_BASELINE_COMMIT,
        "governance_working_head_commit": GOVERNANCE_WORKING_HEAD_COMMIT,
        "representative_case_count": len(cases),
        "cases": cases,
    }


def build_bundle(output_dir: Path = EVAL_DIR) -> dict[str, Any]:
    dataset = _read_json(DATASET_PATH)
    chart_summary, sweep_results = _chart_sensitivity(dataset)
    question_summary, question_outputs = _question_text_sensitivity(dataset)
    structured_context_summary = _structured_context_sensitivity(dataset)
    outputs = _representative_outputs(dataset, sweep_results)
    summary = {
        "audit_version": GENERATOR_VERSION,
        "dataset_version": dataset["dataset_version"],
        "product_behavior_baseline_commit": PRODUCT_BEHAVIOR_BASELINE_COMMIT,
        "governance_working_head_commit": GOVERNANCE_WORKING_HEAD_COMMIT,
        "source_branch": SOURCE_BRANCH,
        "sites_baseline_version": SITES_BASELINE_VERSION,
        "synthetic_only": True,
        "external_model_calls": 0,
        "api_cost_usd": 0,
        "chart_sensitivity": chart_summary,
        "question_text_sensitivity": question_summary,
        "structured_context_sensitivity": structured_context_summary,
        "frozen_boundaries": {
            "deterministic_engine_modified": False,
            "sites_v3_contract_modified": False,
            "official_prompt_modified": False,
            "validator_modified": False,
            "release_gate_modified": False,
            "site_visuals_modified": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = output_dir / "baseline_outputs.json"
    question_outputs_path = output_dir / "question_text_pair_outputs.json"
    summary_path = output_dir / "audit_summary.json"
    _write_json(outputs_path, outputs)
    _write_json(question_outputs_path, question_outputs)
    _write_json(summary_path, summary)
    manifest = {
        "baseline_name": "GUANXIANG_V16_PERSONALIZATION_GATE0",
        "source_branch": SOURCE_BRANCH,
        "product_behavior_baseline_commit": PRODUCT_BEHAVIOR_BASELINE_COMMIT,
        "governance_working_head_commit": GOVERNANCE_WORKING_HEAD_COMMIT,
        "sites_baseline_version": SITES_BASELINE_VERSION,
        "dataset_version": dataset["dataset_version"],
        "generator_version": GENERATOR_VERSION,
        "fixed_clock": dataset["fixed_clock"],
        "python_version": platform.python_version(),
        "timezone": str(_fixed_clock(dataset).tzinfo),
        "synthetic_only": True,
        "external_model_calls": 0,
        "api_cost_usd": 0,
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "divination_reviewer_status": "UNASSIGNED",
        "locked_test_set_status": "NOT_CREATED_OR_EXPOSED",
        "files": {
            "fixed_cases.json": _sha256_file(DATASET_PATH),
            "baseline_outputs.json": _sha256_file(outputs_path),
            "question_text_pair_outputs.json": _sha256_file(question_outputs_path),
            "audit_summary.json": _sha256_file(summary_path),
        },
    }
    _write_json(output_dir / "baseline_manifest.json", manifest)
    return summary


def main() -> None:
    summary = build_bundle()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
