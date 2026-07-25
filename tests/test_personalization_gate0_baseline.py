import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_personalization_gate0_baseline import EVAL_DIR, build_bundle


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def gate0_summary(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return build_bundle(tmp_path_factory.mktemp("personalization-gate0"))


def test_gate0_bundle_proves_chart_changes_do_not_change_action(
    gate0_summary: dict[str, object],
) -> None:
    summary = gate0_summary
    chart = summary["chart_sensitivity"]
    assert chart["sweep_case_count"] == 384
    assert chart["distinct_chart_signatures"] == 384
    assert chart["distinct_base_hexagrams"] == 64
    assert chart["all_charts_share_one_next_action"] is True
    assert chart["all_charts_share_one_continue_signal_set"] is True
    assert chart["all_charts_share_one_pause_signal_set"] is True
    assert len(chart["complete_sweep_sha256"]) == 64


def test_gate0_bundle_proves_free_text_does_not_change_clarity_report(
    gate0_summary: dict[str, object],
) -> None:
    summary = gate0_summary
    question = summary["question_text_sensitivity"]
    assert question["pair_count"] == 4
    assert question["identical_clarity_report_pair_count"] == 4
    assert question["all_question_changes_leave_clarity_report_unchanged"] is True
    assert all(item["request_hashes_different"] for item in question["pairs"])


def test_gate0_bundle_quantifies_structured_context_variation(
    gate0_summary: dict[str, object],
) -> None:
    structured = gate0_summary["structured_context_sensitivity"]
    assert structured["valid_structured_context_count"] == 1088
    assert structured["distinct_next_actions"] == 256
    assert structured["distinct_continue_signal_sets"] == 4
    assert structured["distinct_pause_signal_sets"] == 4
    assert structured["decision_goal_changes_next_action"] is False


def test_gate0_bundle_is_synthetic_offline_and_freezes_product_boundaries(
    gate0_summary: dict[str, object], tmp_path: Path
) -> None:
    summary = build_bundle(tmp_path)
    assert summary["synthetic_only"] is True
    assert summary["external_model_calls"] == 0
    assert summary["api_cost_usd"] == 0
    assert not any(summary["frozen_boundaries"].values())
    manifest = json.loads((tmp_path / "baseline_manifest.json").read_text(encoding="utf-8"))
    assert manifest["narrative_release_status"] == "UNVERIFIED"
    assert manifest["should_charge"] is False
    assert manifest["formal_report_persistence_allowed"] is False
    assert manifest["divination_reviewer_status"] == "UNASSIGNED"
    assert manifest["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    pair_outputs = json.loads(
        (tmp_path / "question_text_pair_outputs.json").read_text(encoding="utf-8")
    )
    assert pair_outputs["pair_count"] == 4
    assert all(
        pair["clarity_report_a"] == pair["clarity_report_b"]
        for pair in pair_outputs["pairs"]
    )


def test_checked_in_gate0_artifacts_exist() -> None:
    for name in (
        "fixed_cases.json",
        "baseline_outputs.json",
        "question_text_pair_outputs.json",
        "audit_summary.json",
        "baseline_manifest.json",
    ):
        assert (EVAL_DIR / name).is_file()


def test_manifest_hashes_match_generated_file_bytes(tmp_path: Path) -> None:
    build_bundle(tmp_path)
    manifest = json.loads((tmp_path / "baseline_manifest.json").read_text(encoding="utf-8"))
    for name, expected_hash in manifest["files"].items():
        path = EVAL_DIR / name if name == "fixed_cases.json" else tmp_path / name
        assert _sha256(path) == expected_hash


def test_independent_gate0_generations_have_identical_hashes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_bundle(first)
    build_bundle(second)
    generated_names = (
        "baseline_outputs.json",
        "question_text_pair_outputs.json",
        "audit_summary.json",
        "baseline_manifest.json",
    )
    assert {_sha256(first / name) for name in generated_names} == {
        _sha256(second / name) for name in generated_names
    }
    assert all(_sha256(first / name) == _sha256(second / name) for name in generated_names)
