"""Strict Pydantic contracts for deterministic synthesis and structured interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from abalo_iching.meihua.enums import BodyUseRelation, EvidencePolarity, EvidenceStrength, TimingLevel
from abalo_iching.meihua.models import MeihuaChart

from .enums import (
    ConclusionLevel,
    EpistemicBasis,
    EvidenceSufficiency,
    KnowledgeReviewStatus,
    KnowledgeEvidenceSourceType,
    NarrativeKind,
    NarrativeReleaseStatus,
    RelationDirection,
    RelationPhase,
    QuestionDomain,
    ServiceStatus,
    SubjectScope,
)

TIMING_DISCLAIMER = "时间判断是本次排盘形成的观察阶段，用于安排复盘和行动，不代表事件必然在某一天发生。"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InterpretationRequest(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, arbitrary_types_allowed=True)

    question_id: str = Field(min_length=1, max_length=128)
    question_domain: QuestionDomain
    normalized_question: str = Field(min_length=2, max_length=500)
    decision_goal: str = Field(min_length=2, max_length=300)
    time_horizon: str = Field(min_length=2, max_length=120)
    real_world_context: str = Field(default="", max_length=2000)
    chart: MeihuaChart
    language: str = "zh-CN"

    @field_validator("normalized_question")
    @classmethod
    def one_core_question(cls, value: str) -> str:
        if value.count("?") + value.count("？") > 1:
            raise ValueError("一个请求只能包含一个核心问题")
        return value

    @field_validator("language")
    @classmethod
    def simplified_chinese_only(cls, value: str) -> str:
        if value != "zh-CN":
            raise ValueError("Phase 2 only supports zh-CN")
        return value


class CanonicalLineText(StrictModel):
    king_wen_number: int = Field(ge=1, le=64)
    hexagram_name: str
    line_position: int = Field(ge=1, le=6)
    line_name: str
    canonical_line_text: str
    source_name: str
    source_reference: str
    canonical_data_version: str


class CanonicalHexagramText(StrictModel):
    king_wen_number: int = Field(ge=1, le=64)
    hexagram_name: str
    canonical_judgment_text: str
    source_name: str
    source_reference: str
    source_accessed_at: str
    canonical_data_version: str
    lines: list[CanonicalLineText]


class ReviewedKnowledgeModel(StrictModel):
    """Knowledge records revalidate updates so status cannot be forged with model_copy."""

    def model_copy(self, *, update: dict[str, Any] | None = None, deep: bool = False):
        if not update:
            return super().model_copy(deep=deep)
        payload = self.model_dump()
        payload.update(update)
        return type(self).model_validate(payload)


class HexagramKnowledge(ReviewedKnowledgeModel):
    king_wen_number: int = Field(ge=1, le=64)
    review_status: KnowledgeReviewStatus
    core_theme: str | None
    situation_pattern: str | None
    favorable_conditions: list[str]
    risk_conditions: list[str]
    action_tendency: str | None
    prohibited_inferences: list[str]
    reviewer: str | None = Field(default=None, min_length=3)
    reviewed_at: AwareDatetime | None
    approved_by: str | None = Field(default=None, min_length=3)
    approved_at: AwareDatetime | None
    review_notes: str | None
    approval_notes: str | None
    knowledge_version: str
    evidence_direction: EvidencePolarity | None = None
    evidence_strength: EvidenceStrength | None = None

    @model_validator(mode="after")
    def validate_review_state(self):
        explanation_values = (
            self.core_theme,
            self.situation_pattern,
            self.action_tendency,
            self.favorable_conditions,
            self.risk_conditions,
            self.prohibited_inferences,
        )
        _validate_review_state(
            self.review_status,
            explanation_values=explanation_values,
            required_content=(self.core_theme, self.situation_pattern, self.action_tendency),
            reviewer=self.reviewer,
            reviewed_at=self.reviewed_at,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
            review_notes=self.review_notes,
            approval_notes=self.approval_notes,
            prohibited_inferences=self.prohibited_inferences,
            evidence_direction=self.evidence_direction,
            evidence_strength=self.evidence_strength,
        )
        return self


class LineKnowledge(ReviewedKnowledgeModel):
    king_wen_number: int = Field(ge=1, le=64)
    line_position: int = Field(ge=1, le=6)
    review_status: KnowledgeReviewStatus
    literal_paraphrase: str | None
    core_theme: str | None
    favorable_conditions: list[str]
    risk_conditions: list[str]
    action_tendency: str | None
    relationship_boundaries: list[str]
    career_boundaries: list[str]
    cooperation_boundaries: list[str]
    prohibited_inferences: list[str]
    reviewer: str | None = Field(default=None, min_length=3)
    reviewed_at: AwareDatetime | None
    approved_by: str | None = Field(default=None, min_length=3)
    approved_at: AwareDatetime | None
    review_notes: str | None
    approval_notes: str | None
    knowledge_version: str
    evidence_direction: EvidencePolarity | None = None
    evidence_strength: EvidenceStrength | None = None

    @model_validator(mode="after")
    def validate_review_state(self):
        explanation_values = (
            self.literal_paraphrase,
            self.core_theme,
            self.action_tendency,
            self.favorable_conditions,
            self.risk_conditions,
            self.relationship_boundaries,
            self.career_boundaries,
            self.cooperation_boundaries,
            self.prohibited_inferences,
        )
        _validate_review_state(
            self.review_status,
            explanation_values=explanation_values,
            required_content=(self.literal_paraphrase, self.core_theme, self.action_tendency),
            reviewer=self.reviewer,
            reviewed_at=self.reviewed_at,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
            review_notes=self.review_notes,
            approval_notes=self.approval_notes,
            prohibited_inferences=self.prohibited_inferences,
            evidence_direction=self.evidence_direction,
            evidence_strength=self.evidence_strength,
        )
        return self


def _validate_review_state(
    status: KnowledgeReviewStatus,
    *,
    explanation_values: tuple[Any, ...],
    required_content: tuple[str | None, ...],
    reviewer: str | None,
    reviewed_at: AwareDatetime | None,
    approved_by: str | None,
    approved_at: AwareDatetime | None,
    review_notes: str | None,
    approval_notes: str | None,
    prohibited_inferences: list[str],
    evidence_direction: EvidencePolarity | None,
    evidence_strength: EvidenceStrength | None,
) -> None:
    if status is KnowledgeReviewStatus.CANONICAL_ONLY:
        if any(explanation_values) or any((reviewer, reviewed_at, approved_by, approved_at, review_notes, approval_notes)):
            raise ValueError("CANONICAL_ONLY records must contain no explanatory or review content")
        if evidence_direction is not None or evidence_strength is not None:
            raise ValueError("CANONICAL_ONLY records cannot define evidence direction or strength")
        return
    if status is KnowledgeReviewStatus.DRAFT:
        if approved_by or approved_at or approval_notes:
            raise ValueError("DRAFT records cannot contain approval metadata")
        return
    if not reviewer or not reviewed_at:
        raise ValueError("REVIEWED and APPROVED records require reviewer and reviewed_at")
    if not all(required_content) or not prohibited_inferences:
        raise ValueError("REVIEWED and APPROVED records require complete core content")
    if status is KnowledgeReviewStatus.REVIEWED:
        if approved_by or approved_at or approval_notes:
            raise ValueError("REVIEWED records cannot contain approval metadata")
        return
    if not approved_by or not approved_at:
        raise ValueError("APPROVED records require approved_by and approved_at")
    if evidence_direction is None or evidence_strength is None:
        raise ValueError("APPROVED records require evidence direction and strength")
    if approved_at < reviewed_at:
        raise ValueError("approved_at cannot be earlier than reviewed_at")


class KnowledgeSelection(StrictModel):
    canonical_hexagram: CanonicalHexagramText
    canonical_line: CanonicalLineText
    hexagram_knowledge: HexagramKnowledge | None
    line_knowledge: LineKnowledge | None
    allowed_knowledge_evidence_ids: list[str] = Field(default_factory=list)
    unreviewed_notice: str | None = None
    access_mode: str = "PRODUCTION"
    is_preview: bool = False
    knowledge_evidence: list["KnowledgeEvidence"] = Field(default_factory=list)


class KnowledgeEvidence(StrictModel):
    evidence_id: str
    source_type: KnowledgeEvidenceSourceType
    king_wen_number: int = Field(ge=1, le=64)
    line_position: int | None = Field(default=None, ge=1, le=6)
    review_status: KnowledgeReviewStatus
    core_theme: str | None
    literal_paraphrase: str | None
    favorable_conditions: list[str]
    risk_conditions: list[str]
    action_tendency: str | None
    prohibited_inferences: list[str]
    polarity: EvidencePolarity | None
    strength: EvidenceStrength | None
    knowledge_version: str
    reviewer: str | None
    reviewed_at: AwareDatetime | None
    approved_by: str | None
    approved_at: AwareDatetime | None
    preview: bool

    @model_validator(mode="after")
    def validate_prefix_and_status(self):
        prefix = self.evidence_id.split("-", 1)[0]
        expected = {
            KnowledgeReviewStatus.APPROVED: "K",
            KnowledgeReviewStatus.REVIEWED: "R",
            KnowledgeReviewStatus.DRAFT: "D",
        }.get(self.review_status)
        if expected is None or prefix != expected:
            raise ValueError("Knowledge Evidence prefix must match validated review status")
        is_line = self.line_position is not None
        expected_id = f"{expected}-{'L' if is_line else 'H'}-{self.king_wen_number}"
        if is_line:
            expected_id += f"-{self.line_position}"
        if self.evidence_id != expected_id:
            raise ValueError("Knowledge Evidence ID must match status, scope, number and line")
        expected_source = {
            (KnowledgeReviewStatus.APPROVED, False): KnowledgeEvidenceSourceType.APPROVED_HEXAGRAM_KNOWLEDGE,
            (KnowledgeReviewStatus.APPROVED, True): KnowledgeEvidenceSourceType.APPROVED_LINE_KNOWLEDGE,
            (KnowledgeReviewStatus.REVIEWED, False): KnowledgeEvidenceSourceType.REVIEWED_HEXAGRAM_PREVIEW,
            (KnowledgeReviewStatus.REVIEWED, True): KnowledgeEvidenceSourceType.REVIEWED_LINE_PREVIEW,
            (KnowledgeReviewStatus.DRAFT, False): KnowledgeEvidenceSourceType.DRAFT_HEXAGRAM_PREVIEW,
            (KnowledgeReviewStatus.DRAFT, True): KnowledgeEvidenceSourceType.DRAFT_LINE_PREVIEW,
        }[(self.review_status, is_line)]
        if self.source_type is not expected_source:
            raise ValueError("Knowledge Evidence source type must match status and scope")
        if (prefix in {"R", "D"}) is not self.preview:
            raise ValueError("R/D Knowledge Evidence must be preview and K must be production")
        return self


class RelationAssessment(StrictModel):
    phase: RelationPhase
    relation: BodyUseRelation
    direction: RelationDirection
    strength: EvidenceStrength
    body_strength: str
    use_strength: str
    modifier_rule_ids: list[str]
    evidence_ids: list[str] = Field(min_length=1)
    conditions: list[str]
    warnings: list[str]


class SynthesisResult(StrictModel):
    conclusion_level: ConclusionLevel
    evidence_sufficiency: EvidenceSufficiency
    supporting_evidence_ids: list[str]
    blocking_evidence_ids: list[str]
    conflicting_evidence_ids: list[str]
    required_conditions: list[str]
    synthesis_rule_ids: list[str]
    warnings: list[str]
    relation_assessments: list[RelationAssessment]


class ProgramTiming(StrictModel):
    level: TimingLevel
    time_horizon: str
    stage: str
    disclaimer: str = TIMING_DISCLAIMER


class ProgramChartFacts(StrictModel):
    base_hexagram_number: int
    base_hexagram_name: str
    mutual_hexagram_number: int
    mutual_hexagram_name: str
    changed_hexagram_number: int
    changed_hexagram_name: str
    moving_line: int
    body_trigram: str
    initial_use_trigram: str
    changed_use_trigram: str
    initial_relation: BodyUseRelation
    changed_relation: BodyUseRelation
    body_strength: str
    initial_use_strength: str
    changed_use_strength: str
    moving_line_stage: str


class ProgramEvidenceItem(StrictModel):
    evidence_id: str
    fact: str
    rule_statement: str
    polarity: EvidencePolarity
    strength: EvidenceStrength


class ProgramOwnedInterpretation(StrictModel):
    template_version: str
    direct_conclusion: str
    conclusion_level: ConclusionLevel
    current_situation: list[str]
    main_conflict: list[ProgramEvidenceItem]
    supporting_factors: list[ProgramEvidenceItem]
    blocking_factors: list[ProgramEvidenceItem]
    chart_facts: ProgramChartFacts
    timing: ProgramTiming
    uncertainties: list[str]
    evidence_trace: list[ProgramEvidenceItem]
    knowledge_evidence_trace: list[KnowledgeEvidence]


class AINarrativeClaim(StrictModel):
    text: str = Field(min_length=4, max_length=300)
    evidence_ids: list[str] = Field(min_length=1, max_length=6)
    narrative_kind: NarrativeKind
    subject_scope: SubjectScope
    epistemic_basis: EpistemicBasis

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Evidence IDs must be unique within a claim")
        return value


class AINarrativeContent(StrictModel):
    plain_language_explanation: list[AINarrativeClaim] = Field(min_length=1, max_length=4)
    real_world_advice: list[AINarrativeClaim] = Field(min_length=1, max_length=4)
    conditions_that_change_outcome: list[AINarrativeClaim] = Field(max_length=4)
    review_questions: list[AINarrativeClaim] = Field(min_length=1, max_length=4)


class ModelMetadata(StrictModel):
    provider_name: str = "UNSET"
    response_id: str | None = None
    model: str = "UNSET"
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    attempt_number: int = Field(default=1, ge=1, le=2)
    prompt_version: str = "MEIHUA_INTERPRETATION_PROMPT_V1"
    tzdata_package_version: str
    timezone_source: str
    system_tz_database_note: str


class MeihuaInterpretation(StrictModel):
    program_content: ProgramOwnedInterpretation
    ai_content: AINarrativeContent
    model_metadata: ModelMetadata
    narrative_release: "NarrativeReleaseSnapshot"


class NarrativeReleaseSnapshot(StrictModel):
    narrative_release_status: NarrativeReleaseStatus = NarrativeReleaseStatus.UNVERIFIED
    live_eval_version: str | None = None
    live_eval_model: str | None = None
    live_eval_completed_at: AwareDatetime | None = None
    live_eval_case_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def unverified_has_no_live_eval_claims(self):
        if self.narrative_release_status is NarrativeReleaseStatus.UNVERIFIED:
            if any((self.live_eval_version, self.live_eval_model, self.live_eval_completed_at)) or self.live_eval_case_count:
                raise ValueError("UNVERIFIED release snapshot cannot claim live evaluation")
        return self


@dataclass(frozen=True, slots=True)
class PromptPackage:
    system_prompt: str
    user_payload_json: str
    prompt_version: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    parsed_output: AINarrativeContent | dict[str, Any]
    response_id: str | None
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    attempt_number: int
    provider_name: str
    prompt_version: str


class ServiceResult(StrictModel):
    status: ServiceStatus
    interpretation: MeihuaInterpretation
    synthesis: SynthesisResult
    should_charge: bool
    not_a_live_openai_result: bool
    is_preview: bool = False
    persist_as_formal_report_allowed: bool = True
