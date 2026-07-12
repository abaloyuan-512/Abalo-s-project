"""Shared Evidence-role contract for narrative prompting and validation."""

from __future__ import annotations

from dataclasses import dataclass

from abalo_iching.meihua.enums import EvidenceType

from .enums import KnowledgeReviewStatus
from .models import InterpretationRequest, KnowledgeEvidence, KnowledgeSelection, SynthesisResult


@dataclass(frozen=True, slots=True)
class EvidenceRoleConstraints:
    explanation_ids: frozenset[str]
    action_option_ids: frozenset[str]
    condition_ids: frozenset[str]
    review_question_ids: frozenset[str]
    selected_knowledge_ids: frozenset[str]
    selected_knowledge_action_ids: frozenset[str]

    def as_prompt_payload(self) -> dict[str, list[str]]:
        return {
            "explanation_ids": sorted(self.explanation_ids),
            "action_option_ids": sorted(self.action_option_ids),
            "condition_ids": sorted(self.condition_ids),
            "review_question_ids": sorted(self.review_question_ids),
        }


_RELATION_TYPES = {
    EvidenceType.INITIAL_BODY_USE_RELATION,
    EvidenceType.CHANGED_BODY_USE_RELATION,
    EvidenceType.BODY_SEASONAL_STRENGTH,
    EvidenceType.INITIAL_USE_SEASONAL_STRENGTH,
    EvidenceType.CHANGED_USE_SEASONAL_STRENGTH,
    EvidenceType.MOVING_LINE_STAGE,
}

_ALLOWED_STATUSES = {
    "PRODUCTION": {KnowledgeReviewStatus.APPROVED},
    "INTERNAL_REVIEW": {KnowledgeReviewStatus.REVIEWED, KnowledgeReviewStatus.APPROVED},
    "INTERNAL_DRAFT_PREVIEW": {
        KnowledgeReviewStatus.DRAFT,
        KnowledgeReviewStatus.REVIEWED,
        KnowledgeReviewStatus.APPROVED,
    },
}


def _is_current_selected_knowledge(
    item: KnowledgeEvidence,
    request: InterpretationRequest,
    knowledge: KnowledgeSelection,
) -> bool:
    if item.evidence_id not in knowledge.allowed_knowledge_evidence_ids:
        return False
    if item.review_status not in _ALLOWED_STATUSES.get(knowledge.access_mode, set()):
        return False
    if knowledge.access_mode == "PRODUCTION" and (item.preview or not item.evidence_id.startswith("K-")):
        return False
    if item.king_wen_number != request.chart.base_hexagram.king_wen_number:
        return False
    return item.line_position is None or item.line_position == request.chart.moving_line


def evidence_role_constraints(
    request: InterpretationRequest,
    knowledge: KnowledgeSelection,
    synthesis: SynthesisResult,
) -> EvidenceRoleConstraints:
    relation_ids = {
        item.evidence_id for item in request.chart.evidence if item.evidence_type in _RELATION_TYPES
    }
    selected = {
        item.evidence_id
        for item in knowledge.knowledge_evidence
        if _is_current_selected_knowledge(item, request, knowledge)
    }
    action_knowledge = {
        item.evidence_id
        for item in knowledge.knowledge_evidence
        if item.evidence_id in selected and bool(item.action_tendency and item.action_tendency.strip())
    }
    action_ids = (
        set(synthesis.supporting_evidence_ids)
        | set(synthesis.blocking_evidence_ids)
        | action_knowledge
    )
    condition_ids = {
        item.evidence_ids[0]
        for item in synthesis.relation_assessments
        if item.conditions or item.warnings
    }
    return EvidenceRoleConstraints(
        explanation_ids=frozenset(relation_ids | selected),
        action_option_ids=frozenset(action_ids),
        condition_ids=frozenset(condition_ids),
        review_question_ids=frozenset(relation_ids | selected),
        selected_knowledge_ids=frozenset(selected),
        selected_knowledge_action_ids=frozenset(action_knowledge),
    )
