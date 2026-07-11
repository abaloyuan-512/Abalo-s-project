"""Render all chart facts, directions, conclusions, evidence, and timing in code."""

from __future__ import annotations

from .enums import ConclusionLevel
from .models import (
    InterpretationRequest,
    KnowledgeSelection,
    ProgramChartFacts,
    ProgramEvidenceItem,
    ProgramOwnedInterpretation,
    ProgramTiming,
    SynthesisResult,
    TIMING_DISCLAIMER,
)

PROGRAM_TEMPLATE_VERSION = "MEIHUA_PROGRAM_INTERPRETATION_V1"

_CONCLUSION_TEMPLATES = {
    ConclusionLevel.CLEARLY_FAVORABLE: "当前证据整体指向有利，但仍需结合现实条件验证。",
    ConclusionLevel.CONDITIONALLY_FAVORABLE: "当前存在推进空间，但结果取决于若干明确条件。",
    ConclusionLevel.MIXED_OR_UNSETTLED: "当前正反因素并存，局势尚未稳定。",
    ConclusionLevel.CLEARLY_UNFAVORABLE: "当前主要证据指向阻力较强，不宜忽略风险直接推进。",
    ConclusionLevel.INSUFFICIENT_EVIDENCE: "当前依据不足，不能可靠给出明确方向。",
}


def direct_conclusion_for(level: ConclusionLevel) -> str:
    return _CONCLUSION_TEMPLATES[level]


class ProgramInterpretationRenderer:
    def render(
        self,
        request: InterpretationRequest,
        knowledge: KnowledgeSelection,
        synthesis: SynthesisResult,
    ) -> ProgramOwnedInterpretation:
        chart = request.chart
        evidence_by_id = {item.evidence_id: item for item in chart.evidence}

        def evidence_items(ids: list[str]) -> list[ProgramEvidenceItem]:
            return [
                ProgramEvidenceItem(
                    evidence_id=item.evidence_id,
                    fact=item.fact,
                    rule_statement=item.rule_statement,
                    polarity=item.polarity,
                    strength=item.strength,
                )
                for evidence_id in ids
                if (item := evidence_by_id.get(evidence_id)) is not None
            ]

        uncertainties = list(synthesis.warnings)
        if knowledge.unreviewed_notice and knowledge.unreviewed_notice not in uncertainties:
            uncertainties.append(knowledge.unreviewed_notice)
        uncertainties.append("程序未启用具体日期，应期仅保留动爻阶段和用户确认的时间范围。")
        if synthesis.evidence_sufficiency.value != "SUFFICIENT":
            uncertainties.append("当前核心证据完整度有限，结论需要现实反馈复核。")

        return ProgramOwnedInterpretation(
            template_version=PROGRAM_TEMPLATE_VERSION,
            direct_conclusion=direct_conclusion_for(synthesis.conclusion_level),
            conclusion_level=synthesis.conclusion_level,
            current_situation=[
                f"本卦为第{chart.base_hexagram.king_wen_number}卦{chart.base_hexagram.full_name_zh}。",
                f"初始体用关系为{chart.initial_body_use_relation.value}。",
                f"变化后体用关系为{chart.changed_body_use_relation.value}。",
            ],
            main_conflict=evidence_items(synthesis.conflicting_evidence_ids),
            supporting_factors=evidence_items(synthesis.supporting_evidence_ids),
            blocking_factors=evidence_items(synthesis.blocking_evidence_ids),
            chart_facts=ProgramChartFacts(
                base_hexagram_number=chart.base_hexagram.king_wen_number,
                base_hexagram_name=chart.base_hexagram.full_name_zh,
                mutual_hexagram_number=chart.mutual_hexagram.king_wen_number,
                mutual_hexagram_name=chart.mutual_hexagram.full_name_zh,
                changed_hexagram_number=chart.changed_hexagram.king_wen_number,
                changed_hexagram_name=chart.changed_hexagram.full_name_zh,
                moving_line=chart.moving_line,
                body_trigram=chart.body_trigram.name_zh,
                initial_use_trigram=chart.initial_use_trigram.name_zh,
                changed_use_trigram=chart.changed_use_trigram.name_zh,
                initial_relation=chart.initial_body_use_relation,
                changed_relation=chart.changed_body_use_relation,
                body_strength=chart.season_context.body_strength.value,
                initial_use_strength=chart.season_context.initial_use_strength.value,
                changed_use_strength=chart.season_context.changed_use_strength.value,
                moving_line_stage=chart.moving_line_stage.value,
            ),
            timing=ProgramTiming(
                level=chart.timing.level,
                time_horizon=request.time_horizon,
                stage=chart.moving_line_stage.value,
                disclaimer=TIMING_DISCLAIMER,
            ),
            uncertainties=list(dict.fromkeys(uncertainties)),
            evidence_trace=evidence_items([item.evidence_id for item in chart.evidence]),
            knowledge_evidence_trace=knowledge.knowledge_evidence,
        )
