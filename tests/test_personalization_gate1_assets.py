from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE1_DIR = ROOT / "evals" / "meihua" / "personalization_gate1_v001"


def _load_json(name: str) -> dict[str, object]:
    return json.loads((GATE1_DIR / name).read_text(encoding="utf-8"))


def test_calibration_set_has_six_anonymous_three_variant_cases() -> None:
    dataset = _load_json("calibration_cases.json")
    cases = dataset["cases"]

    assert dataset["purpose"] == "product_taste_calibration_only"
    assert dataset["synthetic_cases_only"] is True
    assert dataset["canonical_divination_rules"] is False
    assert dataset["variant_order_discloses_archetype"] is False
    assert isinstance(cases, list)
    assert len(cases) == 6
    assert {case["case_id"] for case in cases} == {f"CAL-{index:03d}" for index in range(1, 7)}

    for case in cases:
        assert set(case["variants"]) == {"X", "Y", "Z"}
        assert all(case["variants"][key].strip() for key in ("X", "Y", "Z"))
        assert case["stated_facts"]
        assert case["unknowns"]
        assert case["experimental_interpretive_premise"]


def test_gate1_status_keeps_locked_set_and_models_closed() -> None:
    status = _load_json("gate1_status.json")

    assert status["status"] == "CALIBRATION_ROUND_4_TRANSFER_AWAITING_CONFIRMATION"
    assert status["independent_pre_review"] == "READY_FOR_PRODUCT_CALIBRATION"
    assert status["pre_reviewed_commit"] == "655ceebefcd34564e23ff8a7b49db8ccb042cccf"
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["divination_reviewer_status"] == "UNASSIGNED"
    assert status["model_calls"] == 0
    assert status["api_cost_usd"] == 0
    assert status["formal_product_changed"] is False
    assert status["next_gate_automatically_authorized"] is False
    assert status["product_calibration"]["round_1"] == "ALL_REJECTED"
    assert status["product_calibration"]["round_2"] == "DIRECTION_SELECTED_B_JUDGMENT_A_VOICE"
    assert status["product_calibration"]["round_2_fusion_candidate"] == "ACCEPTED_AS_70_POINT_BASELINE"
    assert status["product_calibration"]["round_3_refined_voice"] == "ACCEPTED_ABOVE_85_POINTS"
    assert status["product_calibration"]["round_4_cross_posture_transfer"] == "AWAITING_PRODUCT_RESPONSE"
    assert status["product_calibration"]["round_1_rejection_recorded_verbatim"] is True


def test_gate1_package_contains_only_declared_governance_assets() -> None:
    expected = {
        "README.md",
        "blind_review_rubric_v1_draft.md",
        "calibration_round1_result.md",
        "calibration_round2_fusion_feedback.md",
        "calibration_round2_result.md",
        "calibration_round3_result.md",
        "calibration_cases.json",
        "content_value_spec_v1_draft.md",
        "gate1_status.json",
        "locked_test_governance.md",
        "product_calibration_packet.md",
        "product_calibration_round2_fusion_candidate.md",
        "product_calibration_round2_single_case.md",
        "product_calibration_round3_refined_voice.md",
        "product_calibration_round4_transfer_packet.md",
    }

    assert {path.name for path in GATE1_DIR.iterdir()} == expected


def test_product_packet_matches_canonical_calibration_cases() -> None:
    dataset = _load_json("calibration_cases.json")
    packet = (GATE1_DIR / "product_calibration_packet.md").read_text(encoding="utf-8")

    for case in dataset["cases"]:
        assert case["case_id"] in packet
        assert case["question"] in packet
        for variant in case["variants"].values():
            assert variant in packet


def test_locked_test_governance_does_not_contain_case_payloads() -> None:
    governance = (GATE1_DIR / "locked_test_governance.md").read_text(encoding="utf-8")

    assert "NOT_CREATED_OR_EXPOSED" in governance
    assert "LOCK-" not in governance
    assert "question_text" not in governance
