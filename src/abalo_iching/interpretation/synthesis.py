"""Deterministic relation assessment: season modifies strength, never direction."""

from __future__ import annotations

from abalo_iching.meihua.enums import (
    BodyUseRelation,
    EvidenceStrength,
    EvidenceType,
    SEASONAL_STRENGTH_RANK,
    SeasonalStrength,
)
from abalo_iching.meihua.models import Evidence, MeihuaChart

from .enums import ConclusionLevel, EvidenceSufficiency, RelationDirection, RelationPhase
from .models import KnowledgeSelection, RelationAssessment, SynthesisResult

RULE_BOTH_FAVORABLE_CLEAR = "MEIHUA-V2A-BOTH-FAVORABLE-CLEAR"
RULE_BOTH_FAVORABLE_CONDITIONAL = "MEIHUA-V2A-BOTH-FAVORABLE-CONDITIONAL"
RULE_FAVORABLE_MIXED = "MEIHUA-V2A-FAVORABLE-MIXED"
RULE_DIRECTION_CONFLICT = "MEIHUA-V2A-DIRECTION-CONFLICT"
RULE_BOTH_UNFAVORABLE_CLEAR = "MEIHUA-V2A-BOTH-UNFAVORABLE-CLEAR"
RULE_UNFAVORABLE_NOT_CLEAR = "MEIHUA-V2A-UNFAVORABLE-NOT-CLEAR"
RULE_BOTH_MIXED = "MEIHUA-V2A-BOTH-MIXED"
RULE_MISSING_RELATION = "MEIHUA-V2A-MISSING-RELATION"


def _by_type(items: tuple[Evidence, ...], evidence_type: EvidenceType) -> Evidence | None:
    return next((item for item in items if item.evidence_type is evidence_type), None)


def _weaken(strength: EvidenceStrength) -> EvidenceStrength:
    return {
        EvidenceStrength.STRONG: EvidenceStrength.MEDIUM,
        EvidenceStrength.MEDIUM: EvidenceStrength.WEAK,
        EvidenceStrength.WEAK: EvidenceStrength.WEAK,
    }[strength]


def _strength_name(value: SeasonalStrength) -> str:
    return value.value


class RelationAssessor:
    """Assess one body/use phase without treating seasonal facts as votes."""

    def assess(self, chart: MeihuaChart, phase: RelationPhase) -> RelationAssessment | None:
        if phase is RelationPhase.INITIAL:
            relation = chart.initial_body_use_relation
            relation_type = EvidenceType.INITIAL_BODY_USE_RELATION
            use_type = EvidenceType.INITIAL_USE_SEASONAL_STRENGTH
            use_strength = chart.season_context.initial_use_strength
        else:
            relation = chart.changed_body_use_relation
            relation_type = EvidenceType.CHANGED_BODY_USE_RELATION
            use_type = EvidenceType.CHANGED_USE_SEASONAL_STRENGTH
            use_strength = chart.season_context.changed_use_strength
        relation_evidence = _by_type(chart.evidence, relation_type)
        if relation_evidence is None:
            return None
        body_evidence = _by_type(chart.evidence, EvidenceType.BODY_SEASONAL_STRENGTH)
        use_evidence = _by_type(chart.evidence, use_type)
        evidence_ids = [relation_evidence.evidence_id]
        if body_evidence:
            evidence_ids.append(body_evidence.evidence_id)
        if use_evidence:
            evidence_ids.append(use_evidence.evidence_id)

        body_strength = chart.season_context.body_strength
        body_rank = SEASONAL_STRENGTH_RANK[body_strength]
        use_rank = SEASONAL_STRENGTH_RANK[use_strength]
        strength = relation_evidence.strength
        conditions: list[str] = []
        warnings: list[str] = []
        modifiers: list[str] = []

        if relation is BodyUseRelation.USE_GENERATES_BODY:
            direction = RelationDirection.FAVORABLE
            if use_rank < body_rank:
                strength = _weaken(strength)
                conditions.append("用方生助能力弱于体方当前承接能力，利向需要现实条件确认。")
                modifiers.append("SEASON-WEAKENS-USE-GENERATES-BODY")
            else:
                modifiers.append("SEASON-SUPPORTS-USE-GENERATES-BODY")
        elif relation is BodyUseRelation.BODY_CONTROLS_USE:
            if body_rank >= use_rank:
                direction = RelationDirection.FAVORABLE
                conditions.append("体方需要持续具备控制和执行条件。")
                modifiers.append("BODY-CONTROL-CAPACITY-SUFFICIENT")
            else:
                direction = RelationDirection.MIXED
                strength = EvidenceStrength.WEAK
                conditions.append("体方弱于用方，体克用的执行条件不足。")
                modifiers.append("BODY-CONTROL-CAPACITY-INSUFFICIENT")
        elif relation is BodyUseRelation.SAME_ELEMENT:
            direction = RelationDirection.MIXED
            modifiers.append("SAME-ELEMENT-NEVER-DIRECTIONAL")
            warnings.append("比和表示同类互动，不因双方旺衰直接转成有利或不利。")
        elif relation is BodyUseRelation.BODY_GENERATES_USE:
            direction = RelationDirection.UNFAVORABLE
            modifiers.append("BODY-GENERATES-USE-REMAINS-CONSUMPTIVE")
            if body_rank > use_rank:
                strength = _weaken(strength)
                conditions.append("体强用弱可降低消耗风险，但不能翻转方向。")
        else:  # USE_CONTROLS_BODY
            direction = RelationDirection.UNFAVORABLE
            modifiers.append("USE-CONTROLS-BODY-REMAINS-UNFAVORABLE")
            if body_rank >= use_rank:
                strength = _weaken(strength)
                conditions.append("体方承压能力不弱于用方，可降低风险强度但不能翻转方向。")

        return RelationAssessment(
            phase=phase,
            relation=relation,
            direction=direction,
            strength=strength,
            body_strength=_strength_name(body_strength),
            use_strength=_strength_name(use_strength),
            modifier_rule_ids=modifiers,
            evidence_ids=evidence_ids,
            conditions=conditions,
            warnings=warnings,
        )


class ConclusionSynthesizer:
    def __init__(self, assessor: RelationAssessor | None = None) -> None:
        self.assessor = assessor or RelationAssessor()

    def synthesize(self, chart: MeihuaChart, knowledge: KnowledgeSelection) -> SynthesisResult:
        initial = self.assessor.assess(chart, RelationPhase.INITIAL)
        changed = self.assessor.assess(chart, RelationPhase.CHANGED)
        assessments = [item for item in (initial, changed) if item is not None]
        warnings = [warning for item in assessments for warning in item.warnings]
        if knowledge.unreviewed_notice:
            warnings.append(knowledge.unreviewed_notice)
        if initial is None or changed is None:
            return SynthesisResult(
                conclusion_level=ConclusionLevel.INSUFFICIENT_EVIDENCE,
                evidence_sufficiency=EvidenceSufficiency.INSUFFICIENT,
                supporting_evidence_ids=[],
                blocking_evidence_ids=[],
                conflicting_evidence_ids=[],
                required_conditions=["必须同时具备初始与变化后体用关系证据。"],
                synthesis_rule_ids=[RULE_MISSING_RELATION],
                warnings=warnings + ["核心关系证据缺失，旺衰证据不能替代体用关系。"],
                relation_assessments=assessments,
            )

        supporting = [a.evidence_ids[0] for a in assessments if a.direction is RelationDirection.FAVORABLE]
        blocking = [a.evidence_ids[0] for a in assessments if a.direction is RelationDirection.UNFAVORABLE]
        conditions = [condition for item in assessments for condition in item.conditions]
        directions = {initial.direction, changed.direction}
        conflicts: list[str] = []

        if directions == {RelationDirection.FAVORABLE}:
            clear = any(a.strength is EvidenceStrength.STRONG for a in assessments) and not conditions
            level = ConclusionLevel.CLEARLY_FAVORABLE if clear else ConclusionLevel.CONDITIONALLY_FAVORABLE
            sufficiency = EvidenceSufficiency.SUFFICIENT if clear else EvidenceSufficiency.LIMITED
            rule = RULE_BOTH_FAVORABLE_CLEAR if clear else RULE_BOTH_FAVORABLE_CONDITIONAL
        elif directions == {RelationDirection.FAVORABLE, RelationDirection.MIXED}:
            level = ConclusionLevel.CONDITIONALLY_FAVORABLE
            sufficiency = EvidenceSufficiency.LIMITED
            rule = RULE_FAVORABLE_MIXED
        elif directions == {RelationDirection.FAVORABLE, RelationDirection.UNFAVORABLE}:
            level = ConclusionLevel.MIXED_OR_UNSETTLED
            sufficiency = EvidenceSufficiency.LIMITED
            rule = RULE_DIRECTION_CONFLICT
            conflicts = [initial.evidence_ids[0], changed.evidence_ids[0]]
        elif directions == {RelationDirection.UNFAVORABLE}:
            clear = any(a.strength is EvidenceStrength.STRONG for a in assessments)
            level = ConclusionLevel.CLEARLY_UNFAVORABLE if clear else ConclusionLevel.MIXED_OR_UNSETTLED
            sufficiency = EvidenceSufficiency.SUFFICIENT if clear else EvidenceSufficiency.LIMITED
            rule = RULE_BOTH_UNFAVORABLE_CLEAR if clear else RULE_UNFAVORABLE_NOT_CLEAR
        elif RelationDirection.UNFAVORABLE in directions:
            level = ConclusionLevel.MIXED_OR_UNSETTLED
            sufficiency = EvidenceSufficiency.LIMITED
            rule = RULE_UNFAVORABLE_NOT_CLEAR
        else:
            level = ConclusionLevel.MIXED_OR_UNSETTLED
            sufficiency = EvidenceSufficiency.LIMITED
            rule = RULE_BOTH_MIXED

        if level is ConclusionLevel.MIXED_OR_UNSETTLED and not conflicts:
            conflicts = [initial.evidence_ids[0], changed.evidence_ids[0]]

        return SynthesisResult(
            conclusion_level=level,
            evidence_sufficiency=sufficiency,
            supporting_evidence_ids=supporting,
            blocking_evidence_ids=blocking,
            conflicting_evidence_ids=conflicts,
            required_conditions=conditions,
            synthesis_rule_ids=[rule],
            warnings=warnings,
            relation_assessments=assessments,
        )
