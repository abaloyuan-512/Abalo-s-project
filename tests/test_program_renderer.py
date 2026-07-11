import pytest

from abalo_iching.interpretation.enums import ConclusionLevel
from abalo_iching.interpretation.renderer import (
    PROGRAM_TEMPLATE_VERSION,
    ProgramInterpretationRenderer,
    direct_conclusion_for,
)


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (ConclusionLevel.CLEARLY_FAVORABLE, "当前证据整体指向有利，但仍需结合现实条件验证。"),
        (ConclusionLevel.CONDITIONALLY_FAVORABLE, "当前存在推进空间，但结果取决于若干明确条件。"),
        (ConclusionLevel.MIXED_OR_UNSETTLED, "当前正反因素并存，局势尚未稳定。"),
        (ConclusionLevel.CLEARLY_UNFAVORABLE, "当前主要证据指向阻力较强，不宜忽略风险直接推进。"),
        (ConclusionLevel.INSUFFICIENT_EVIDENCE, "当前依据不足，不能可靠给出明确方向。"),
    ],
)
def test_direct_conclusion_templates_are_one_to_one(level, expected):
    assert direct_conclusion_for(level) == expected


def test_renderer_owns_chart_facts_evidence_timing_and_uncertainty(
    phase2_request, phase2_knowledge, phase2_synthesis
):
    result = ProgramInterpretationRenderer().render(phase2_request, phase2_knowledge, phase2_synthesis)
    chart = phase2_request.chart
    assert result.template_version == PROGRAM_TEMPLATE_VERSION
    assert result.conclusion_level is phase2_synthesis.conclusion_level
    assert result.direct_conclusion == direct_conclusion_for(phase2_synthesis.conclusion_level)
    assert result.chart_facts.base_hexagram_name == chart.base_hexagram.full_name_zh
    assert result.chart_facts.moving_line == chart.moving_line
    assert result.timing.time_horizon == phase2_request.time_horizon
    assert result.timing.stage == chart.moving_line_stage.value
    assert [item.evidence_id for item in result.blocking_factors] == phase2_synthesis.blocking_evidence_ids
    assert [item.evidence_id for item in result.supporting_factors] == phase2_synthesis.supporting_evidence_ids
    assert len(result.evidence_trace) == len(chart.evidence)


def test_ai_narrative_model_has_no_program_owned_fields(valid_interpretation):
    fields = set(type(valid_interpretation).model_fields)
    assert fields == {
        "plain_language_explanation",
        "real_world_advice",
        "conditions_that_change_outcome",
        "review_questions",
    }
    assert "summary" not in valid_interpretation.model_dump_json()
