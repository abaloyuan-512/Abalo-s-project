from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE2_DIR = ROOT / "evals" / "meihua" / "personalization_gate2_v001"
PLAN = GATE2_DIR / "offline_experiment_contract_and_implementation_plan_candidate.md"
README = GATE2_DIR / "README.md"
STATUS = GATE2_DIR / "stage_ab_status.json"
STAGE_C_STATUS = GATE2_DIR / "stage_c_status.json"
STAGE_C_FAILURE = GATE2_DIR / "stage_c_failure_analysis.md"
STAGE_C1_PLAN = GATE2_DIR / "stage_c1_offline_hardening_plan.md"
STAGE_C1_STATUS = GATE2_DIR / "stage_c1_status.json"


def test_gate2_contains_only_the_approved_governance_assets() -> None:
    assert {path.name for path in GATE2_DIR.iterdir()} == {
        PLAN.name,
        README.name,
        STATUS.name,
        STAGE_C_STATUS.name,
        STAGE_C_FAILURE.name,
        STAGE_C1_PLAN.name,
        STAGE_C1_STATUS.name,
    }


def test_gate2_plan_records_stage_ab_authorization_and_keeps_live_work_closed() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "APPROVED_STAGE_A_B_IMPLEMENTATION" in text
    assert "本文不创建任何锁定案例" in text
    assert "真实模型调用授权" in text
    assert "API Key配置授权" in text
    assert "正式产品修改授权" in text
    assert "calls_per_result       1" in text
    assert "automatic_model_repair 0" in text
    assert "累计可支出上限为22美元" in text
    assert "不得动用至少7美元的预留余额" in text


def test_gate2_stage_ab_status_keeps_external_and_formal_boundaries_closed() -> None:
    status = __import__("json").loads(STATUS.read_text(encoding="utf-8"))

    assert status["stage_a_authorized"] is True
    assert status["stage_b_authorized"] is True
    assert status["external_model_calls"] == 0
    assert status["api_cost_usd"] == 0
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["next_stage_automatically_authorized"] is False


def test_gate2_stage_c_status_records_narrow_live_authorization() -> None:
    status = __import__("json").loads(STAGE_C_STATUS.read_text(encoding="utf-8"))

    assert status["stage_c_authorized"] is True
    assert status["stage_d_authorized"] is False
    assert status["authorized_spend_usd"] == 2
    assert status["required_reserve_usd"] == 7
    assert status["max_generation_calls"] == 6
    assert status["synthetic_data_only"] is True
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["next_stage_automatically_authorized"] is False
    assert status["external_model_calls"] == 2
    assert status["api_cost_usd"] is None
    assert status["diagnostic_retry_max_generation_calls"] == 1
    assert status["diagnostic_retry_external_model_calls"] == 1
    assert status["diagnostic_retry_automatic_model_repair_calls"] == 0
    assert status["diagnostic_retry_authorized_spend_usd"] == 0.35
    assert status["diagnostic_retry_status"] == "PROVIDER_FAILED_TIMEOUT"


def test_gate2_stage_c1_status_keeps_paid_retest_and_stage_d_closed() -> None:
    status = __import__("json").loads(STAGE_C1_STATUS.read_text(encoding="utf-8"))

    assert status["paid_retest_authorized"] is False
    assert status["external_model_calls"] == 0
    assert status["api_cost_usd"] == 0
    assert status["maximum_generation_calls_if_later_authorized"] == 1
    assert status["polling_creates_additional_generation"] is False
    assert status["resume_creates_additional_generation"] is False
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["stage_d_authorized"] is False
    assert status["next_stage_automatically_authorized"] is False


def test_gate2_plan_preserves_three_sources_and_four_arms() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for marker in ("REALITY_FACT", "CHART_FACT", "INTERPRETIVE_LINK"):
        assert marker in text
    for trace_field in (
        "trace_id",
        "link_mode",
        "REALITY_ONLY",
        "REALITY_AND_CHART",
        "reality_refs[]",
        "evidence_refs[]",
        "supports_fields[]",
        "interpretation_hypothesis",
    ):
        assert trace_field in text
    assert "B组使用`link_mode=REALITY_ONLY`" in text
    assert "C/D组使用`link_mode=REALITY_AND_CHART`" in text
    assert "`user_facing_reading`的五个字段都必须至少被一条`source_trace.supports_fields[]`覆盖" in text
    for arm in ("| A |", "| B |", "| C |", "| D |"):
        assert arm in text
    assert "question_text_used_for_calculation = false" in text
    assert "question_text_used_for_interpretation = true" in text


def test_gate2_plan_names_formal_systems_that_stay_unchanged() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for boundary in (
        "确定性排盘引擎",
        "正式网站和视觉v16",
        "V3接口与当前确定性报告",
        "meihua_interpretation_v1.txt",
        "InterpretationValidator",
        "Narrative Release Gate",
    ):
        assert boundary in text
