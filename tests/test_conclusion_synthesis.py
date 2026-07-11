from dataclasses import replace

import pytest

from abalo_iching.interpretation.enums import ConclusionLevel, RelationDirection
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.meihua.enums import (
    BodyUseRelation,
    EvidencePolarity,
    EvidenceStrength,
    EvidenceType,
    SeasonalStrength,
)
from abalo_iching.meihua.models import Evidence


def evidence(evidence_id, evidence_type, strength=EvidenceStrength.MEDIUM, polarity=EvidencePolarity.NEUTRAL):
    return Evidence(evidence_id, evidence_type, "TEST", polarity, strength, "fact", "rule", "TEST")


def chart_for(
    chart,
    initial,
    changed,
    *,
    body=SeasonalStrength.RESTING,
    initial_use=SeasonalStrength.RESTING,
    changed_use=SeasonalStrength.RESTING,
    initial_relation_strength=EvidenceStrength.MEDIUM,
    changed_relation_strength=EvidenceStrength.MEDIUM,
    body_polarity=EvidencePolarity.NEUTRAL,
    initial_use_polarity=EvidencePolarity.NEUTRAL,
    changed_use_polarity=EvidencePolarity.NEUTRAL,
):
    season = replace(
        chart.season_context,
        body_strength=body,
        initial_use_strength=initial_use,
        changed_use_strength=changed_use,
    )
    items = (
        evidence("E02", EvidenceType.INITIAL_BODY_USE_RELATION, initial_relation_strength),
        evidence("E03", EvidenceType.CHANGED_BODY_USE_RELATION, changed_relation_strength),
        evidence("E06", EvidenceType.BODY_SEASONAL_STRENGTH, polarity=body_polarity),
        evidence("E07", EvidenceType.INITIAL_USE_SEASONAL_STRENGTH, polarity=initial_use_polarity),
        evidence("E08", EvidenceType.CHANGED_USE_SEASONAL_STRENGTH, polarity=changed_use_polarity),
    )
    return replace(
        chart,
        initial_body_use_relation=initial,
        changed_body_use_relation=changed,
        season_context=season,
        evidence=items,
    )


def synthesize(chart, knowledge):
    return ConclusionSynthesizer().synthesize(chart, knowledge)


def test_both_favorable_with_one_strong_and_no_major_condition_is_clear(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.USE_GENERATES_BODY,
        BodyUseRelation.USE_GENERATES_BODY,
        initial_relation_strength=EvidenceStrength.STRONG,
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.CLEARLY_FAVORABLE


def test_both_favorable_without_strong_is_conditional(phase2_chart, phase2_knowledge):
    chart = chart_for(phase2_chart, BodyUseRelation.USE_GENERATES_BODY, BodyUseRelation.USE_GENERATES_BODY)
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.CONDITIONALLY_FAVORABLE


def test_use_generates_body_can_be_weakened_but_not_reversed(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.USE_GENERATES_BODY,
        BodyUseRelation.USE_GENERATES_BODY,
        body=SeasonalStrength.PROSPEROUS,
        initial_use=SeasonalStrength.DEAD,
        changed_use=SeasonalStrength.DEAD,
        initial_relation_strength=EvidenceStrength.STRONG,
    )
    result = synthesize(chart, phase2_knowledge)
    assert all(item.direction is RelationDirection.FAVORABLE for item in result.relation_assessments)
    assert result.conclusion_level is ConclusionLevel.CONDITIONALLY_FAVORABLE


def test_body_controls_use_capacity_creates_favorable_and_mixed_assessments(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.BODY_CONTROLS_USE,
        BodyUseRelation.BODY_CONTROLS_USE,
        body=SeasonalStrength.RESTING,
        initial_use=SeasonalStrength.DEAD,
        changed_use=SeasonalStrength.PROSPEROUS,
    )
    result = synthesize(chart, phase2_knowledge)
    assert [item.direction for item in result.relation_assessments] == [
        RelationDirection.FAVORABLE,
        RelationDirection.MIXED,
    ]
    assert result.conclusion_level is ConclusionLevel.CONDITIONALLY_FAVORABLE


def test_favorable_and_unfavorable_is_mixed(phase2_chart, phase2_knowledge):
    chart = chart_for(phase2_chart, BodyUseRelation.USE_GENERATES_BODY, BodyUseRelation.USE_CONTROLS_BODY)
    result = synthesize(chart, phase2_knowledge)
    assert result.conclusion_level is ConclusionLevel.MIXED_OR_UNSETTLED
    assert result.conflicting_evidence_ids == ["E02", "E03"]


def test_two_strong_unfavorable_relations_are_clear_unfavorable(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.BODY_GENERATES_USE,
        BodyUseRelation.USE_CONTROLS_BODY,
        initial_relation_strength=EvidenceStrength.STRONG,
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.CLEARLY_UNFAVORABLE


def test_missing_changed_relation_is_insufficient(phase2_chart, phase2_knowledge):
    chart = replace(
        phase2_chart,
        evidence=tuple(item for item in phase2_chart.evidence if item.evidence_type is not EvidenceType.CHANGED_BODY_USE_RELATION),
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.INSUFFICIENT_EVIDENCE


def test_two_positive_seasonal_facts_with_two_mixed_relations_never_clear_favorable(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.SAME_ELEMENT,
        BodyUseRelation.SAME_ELEMENT,
        body_polarity=EvidencePolarity.POSITIVE,
        initial_use_polarity=EvidencePolarity.POSITIVE,
        changed_use_polarity=EvidencePolarity.POSITIVE,
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.MIXED_OR_UNSETTLED


def test_negative_relation_with_positive_seasonal_facts_never_becomes_favorable(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.USE_CONTROLS_BODY,
        BodyUseRelation.SAME_ELEMENT,
        body=SeasonalStrength.PROSPEROUS,
        body_polarity=EvidencePolarity.POSITIVE,
        initial_use_polarity=EvidencePolarity.POSITIVE,
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.MIXED_OR_UNSETTLED


def test_two_negative_seasonal_facts_with_mixed_relations_never_clear_unfavorable(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.SAME_ELEMENT,
        BodyUseRelation.SAME_ELEMENT,
        body_polarity=EvidencePolarity.NEGATIVE,
        initial_use_polarity=EvidencePolarity.NEGATIVE,
        changed_use_polarity=EvidencePolarity.NEGATIVE,
    )
    assert synthesize(chart, phase2_knowledge).conclusion_level is ConclusionLevel.MIXED_OR_UNSETTLED


def test_same_element_both_prosperous_stays_mixed(phase2_chart, phase2_knowledge):
    chart = chart_for(
        phase2_chart,
        BodyUseRelation.SAME_ELEMENT,
        BodyUseRelation.SAME_ELEMENT,
        body=SeasonalStrength.PROSPEROUS,
        initial_use=SeasonalStrength.PROSPEROUS,
        changed_use=SeasonalStrength.PROSPEROUS,
    )
    assert all(a.direction is RelationDirection.MIXED for a in synthesize(chart, phase2_knowledge).relation_assessments)


@pytest.mark.parametrize("relation", [BodyUseRelation.USE_CONTROLS_BODY, BodyUseRelation.BODY_GENERATES_USE])
def test_unfavorable_relations_never_flip_when_body_is_strong_and_use_is_weak(
    relation, phase2_chart, phase2_knowledge
):
    chart = chart_for(
        phase2_chart,
        relation,
        relation,
        body=SeasonalStrength.PROSPEROUS,
        initial_use=SeasonalStrength.DEAD,
        changed_use=SeasonalStrength.DEAD,
    )
    result = synthesize(chart, phase2_knowledge)
    assert all(a.direction is RelationDirection.UNFAVORABLE for a in result.relation_assessments)
    assert result.conclusion_level is not ConclusionLevel.CLEARLY_FAVORABLE


def test_synthesis_contract_contains_no_score_percentage_or_accuracy(phase2_synthesis):
    keys = phase2_synthesis.model_dump().keys()
    assert not {"score", "percentage", "accuracy"} & set(keys)
