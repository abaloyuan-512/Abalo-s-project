from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE2_DIR = ROOT / "evals" / "meihua" / "personalization_gate2_v001"
PLAN = GATE2_DIR / "offline_experiment_contract_and_implementation_plan_candidate.md"


def test_gate2_contains_only_the_unapproved_plan_candidate() -> None:
    assert {path.name for path in GATE2_DIR.iterdir()} == {PLAN.name}


def test_gate2_plan_keeps_execution_and_locked_set_closed() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "DRAFT_AWAITING_PRODUCT_OWNER_APPROVAL" in text
    assert "本文不创建任何锁定案例" in text
    assert "真实模型调用授权" in text
    assert "API Key配置授权" in text
    assert "正式产品修改授权" in text
    assert "calls_per_result       1" in text
    assert "automatic_model_repair 0" in text
    assert "累计可支出上限为22美元" in text
    assert "不得动用至少7美元的预留余额" in text


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
