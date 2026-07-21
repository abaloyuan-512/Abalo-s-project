from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RW_PATTERN = r"^RW\d{2}$"
EV_PATTERN = r"^EV\d{2}$"
TRACE_PATTERN = r"^(RW|EV|IL)\d{2}$"
CASE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
OUTPUT_SCHEMA_VERSION = "gate2_schema_v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ExperimentArm(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DatasetRole(StrEnum):
    CALIBRATION = "CALIBRATION"
    LOCKED = "LOCKED"


class QuestionDomain(StrEnum):
    WORK = "工作"
    COOPERATION = "合作"
    RELATIONSHIP = "关系"
    PERSONAL_PLAN = "个人规划"
    OTHER = "其他"


class KnowledgeReviewStatus(StrEnum):
    CANONICAL_ONLY = "CANONICAL_ONLY"
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"


class Direction(StrEnum):
    ADVANCE = "推进"
    WAIT = "等待"
    PROTECT = "守护"
    EXIT = "退出"
    CLOSE = "收尾"
    CHANGE = "转变"


class Method(StrEnum):
    CLARIFY = "澄清"
    REPAIR = "修复"
    NEGOTIATE = "谈判"
    BORROW_SUPPORT = "借力"
    DISCLOSE = "公开"
    CONCEAL = "隐藏"
    RESTRUCTURE = "重构"


class Agency(StrEnum):
    USER = "在用户"
    EXTERNAL = "在外部"
    SHARED = "双方共同"
    UNCLEAR = "尚不明确"


class MainConflict(StrEnum):
    TIMING = "时机"
    RESOURCE = "资源"
    ROLE = "角色"
    TRUST = "信任"
    RESPONSE = "回应"
    INVESTMENT = "投入"
    LEGACY = "旧问题"
    OTHER = "其他"


class ActionIntensity(StrEnum):
    LIGHT = "轻"
    MEDIUM = "中"
    STRONG = "强"


class SourceKind(StrEnum):
    REALITY_FACT = "REALITY_FACT"
    CHART_FACT = "CHART_FACT"
    INTERPRETIVE_LINK = "INTERPRETIVE_LINK"


class LinkMode(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REALITY_ONLY = "REALITY_ONLY"
    REALITY_AND_CHART = "REALITY_AND_CHART"


class RunMetadata(StrictModel):
    case_id: str = Field(pattern=CASE_ID_PATTERN)
    arm: ExperimentArm
    dataset_role: DatasetRole = DatasetRole.CALIBRATION
    contract_version: str = Field(min_length=1, max_length=80)
    prompt_version: str = Field(min_length=1, max_length=80)
    schema_version: str = Field(min_length=1, max_length=80)
    validator_version: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    reasoning_effort: str = Field(min_length=1, max_length=40)
    max_output_tokens: int = Field(ge=1, le=8000)
    store: Literal[False] = False
    tools: list[str] = Field(default_factory=list, max_length=0)

    @model_validator(mode="after")
    def validate_arm_metadata(self) -> RunMetadata:
        if self.arm is ExperimentArm.A:
            expected = (self.prompt_version, self.model, self.reasoning_effort)
            if expected != ("NOT_APPLICABLE",) * 3:
                raise ValueError("A 组的 prompt/model/reasoning 必须为 NOT_APPLICABLE")
        elif "NOT_APPLICABLE" in (
            self.prompt_version,
            self.model,
            self.reasoning_effort,
        ):
            raise ValueError("B/C/D 组必须声明实验 prompt、model 与 reasoning")
        return self


class RealityFact(StrictModel):
    ref: str = Field(pattern=RW_PATTERN)
    text: str = Field(min_length=1, max_length=600)


class UnknownItem(StrictModel):
    text: str = Field(min_length=1, max_length=400)


class SyntheticRealityContext(StrictModel):
    synthetic_data_confirmed: Literal[True]
    question_text: str = Field(min_length=1, max_length=1200)
    question_domain: QuestionDomain
    decision_goal: str = Field(min_length=1, max_length=400)
    explicit_facts: list[RealityFact] = Field(min_length=1, max_length=20)
    unknowns: list[UnknownItem] = Field(default_factory=list, max_length=20)
    options: list[RealityFact] = Field(default_factory=list, max_length=12)
    hard_constraints: list[RealityFact] = Field(default_factory=list, max_length=12)
    actions_already_taken: list[RealityFact] = Field(default_factory=list, max_length=12)
    observable_responses: list[RealityFact] = Field(default_factory=list, max_length=12)

    def reality_facts(self) -> tuple[RealityFact, ...]:
        return tuple(
            self.explicit_facts
            + self.options
            + self.hard_constraints
            + self.actions_already_taken
            + self.observable_responses
        )

    def reality_refs(self) -> set[str]:
        return {item.ref for item in self.reality_facts()}

    @model_validator(mode="after")
    def validate_reality_refs(self) -> SyntheticRealityContext:
        refs = [item.ref for item in self.reality_facts()]
        if len(refs) != len(set(refs)):
            raise ValueError("现实事实引用 RWxx 必须唯一")
        return self


class ChartEvidence(StrictModel):
    ref: str = Field(pattern=EV_PATTERN)
    canonical_evidence_id: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1, max_length=800)
    knowledge_review_status: KnowledgeReviewStatus


class ChartContext(StrictModel):
    chart_mapping_id: str = Field(min_length=1, max_length=120)
    is_mismatched_control: bool
    evidence: list[ChartEvidence] = Field(min_length=1, max_length=40)

    def evidence_refs(self) -> set[str]:
        return {item.ref for item in self.evidence}

    @model_validator(mode="after")
    def validate_evidence_refs(self) -> ChartContext:
        refs = [item.ref for item in self.evidence]
        if len(refs) != len(set(refs)):
            raise ValueError("卦象事实引用 EVxx 必须唯一")
        return self


class Gate2ExperimentRequest(StrictModel):
    metadata: RunMetadata
    reality: SyntheticRealityContext
    chart_context: ChartContext | None = None
    deterministic_v16_output: str | None = Field(default=None, max_length=12000)
    question_text_used_for_calculation: Literal[False] = False
    question_text_used_for_interpretation: Literal[True] = True

    @model_validator(mode="after")
    def validate_arm_payload(self) -> Gate2ExperimentRequest:
        arm = self.metadata.arm
        if arm is ExperimentArm.A:
            if self.chart_context is not None or not self.deterministic_v16_output:
                raise ValueError("A 组只能携带 v16 确定性基线，不得携带卦象上下文")
        elif arm is ExperimentArm.B:
            if self.chart_context is not None or self.deterministic_v16_output is not None:
                raise ValueError("B 组不得携带卦象或 v16 基线")
        elif arm is ExperimentArm.C:
            if self.chart_context is None or self.chart_context.is_mismatched_control:
                raise ValueError("C 组必须携带真实、非错配卦象")
        elif arm is ExperimentArm.D:
            if self.chart_context is None or not self.chart_context.is_mismatched_control:
                raise ValueError("D 组必须携带预先冻结的错配卦象")
        return self


class ContextFact(StrictModel):
    fact_text: str = Field(min_length=1, max_length=700)
    reality_refs: list[str] = Field(min_length=1, max_length=20)


class OutputUnknown(StrictModel):
    unknown_text: str = Field(min_length=1, max_length=500)
    must_not_infer: Literal[True] = True


class ChartSignal(StrictModel):
    signal_text: str = Field(min_length=1, max_length=800)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    knowledge_review_status: KnowledgeReviewStatus


class CoreConflict(StrictModel):
    text: str = Field(min_length=1, max_length=800)
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    interpretation_hypothesis: Literal[True] = True


class JudgmentSignature(StrictModel):
    direction: Direction
    method: Method
    agency: Agency
    main_conflict: MainConflict
    action_intensity: ActionIntensity


class OppositePostureAndReason(StrictModel):
    opposite_posture: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=800)
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class OneAction(StrictModel):
    action_text: str = Field(min_length=1, max_length=700)
    target_or_person: str = Field(min_length=1, max_length=240)
    observable_result: str = Field(min_length=1, max_length=500)
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class SwitchCondition(StrictModel):
    condition_text: str = Field(min_length=1, max_length=600)
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class SourceTrace(StrictModel):
    trace_id: str = Field(pattern=TRACE_PATTERN)
    source_kind: SourceKind
    source_ref: str = Field(pattern=TRACE_PATTERN)
    supports_fields: list[str] = Field(min_length=1, max_length=40)
    link_mode: LinkMode
    reality_refs: list[str] = Field(default_factory=list, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    interpretation_hypothesis: bool

    @model_validator(mode="after")
    def validate_source_kind_contract(self) -> SourceTrace:
        if self.trace_id != self.source_ref:
            raise ValueError("trace_id 与 source_ref 必须一致")
        if self.source_kind is SourceKind.REALITY_FACT:
            if not self.trace_id.startswith("RW"):
                raise ValueError("REALITY_FACT 必须使用 RWxx")
            if (
                self.link_mode is not LinkMode.NOT_APPLICABLE
                or self.reality_refs
                or self.evidence_refs
                or self.interpretation_hypothesis
            ):
                raise ValueError("REALITY_FACT 不得携带解释接榫字段")
        elif self.source_kind is SourceKind.CHART_FACT:
            if not self.trace_id.startswith("EV"):
                raise ValueError("CHART_FACT 必须使用 EVxx")
            if (
                self.link_mode is not LinkMode.NOT_APPLICABLE
                or self.reality_refs
                or self.evidence_refs
                or self.interpretation_hypothesis
            ):
                raise ValueError("CHART_FACT 不得携带解释接榫字段")
        else:
            if not self.trace_id.startswith("IL") or not self.interpretation_hypothesis:
                raise ValueError("INTERPRETIVE_LINK 必须使用 ILxx 并标记为解释假设")
            if self.link_mode is LinkMode.REALITY_ONLY:
                if not self.reality_refs or self.evidence_refs:
                    raise ValueError("REALITY_ONLY 必须引用现实事实且不得引用卦象事实")
            elif self.link_mode is LinkMode.REALITY_AND_CHART:
                if not self.reality_refs or not self.evidence_refs:
                    raise ValueError("REALITY_AND_CHART 必须同时引用现实与卦象事实")
            else:
                raise ValueError("INTERPRETIVE_LINK 不得使用 NOT_APPLICABLE")
        return self


class UserFacingReading(StrictModel):
    core_judgment: str = Field(min_length=1, max_length=900)
    explanation: str = Field(min_length=1, max_length=2400)
    reality_application: str = Field(min_length=1, max_length=1600)
    action: str = Field(min_length=1, max_length=1000)
    switch_condition: str = Field(min_length=1, max_length=900)


class Gate2ExperimentOutput(StrictModel):
    context_facts: list[ContextFact] = Field(min_length=1, max_length=20)
    unknowns: list[OutputUnknown] = Field(default_factory=list, max_length=20)
    chart_signals: list[ChartSignal] = Field(default_factory=list, max_length=30)
    core_conflict: CoreConflict
    judgment_signature: JudgmentSignature
    opposite_posture_and_reason: OppositePostureAndReason
    one_action: OneAction
    switch_conditions: list[SwitchCondition] = Field(min_length=1, max_length=10)
    source_trace: list[SourceTrace] = Field(min_length=1, max_length=80)
    user_facing_reading: UserFacingReading

    @model_validator(mode="after")
    def validate_unique_trace_ids(self) -> Gate2ExperimentOutput:
        trace_ids = [item.trace_id for item in self.source_trace]
        if len(trace_ids) != len(set(trace_ids)):
            raise ValueError("source_trace.trace_id 必须唯一")
        return self


class Gate2PromptPackage(StrictModel):
    prompt_version: str
    system_instructions: str
    input_payload: dict[str, Any]
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class Gate2Usage(StrictModel):
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class Gate2ProviderResult(StrictModel):
    response_id: str = Field(min_length=1, max_length=160)
    provider_name: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    raw_output: dict[str, Any]
    usage: Gate2Usage = Field(default_factory=Gate2Usage)
    latency_ms: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)


class ValidationFailure(StrictModel):
    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=800)
    field_path: str | None = Field(default=None, max_length=240)


class Gate2ValidationReport(StrictModel):
    hard_failures: list[ValidationFailure] = Field(default_factory=list)
    quality_failures: list[ValidationFailure] = Field(default_factory=list)

    @property
    def hard_passed(self) -> bool:
        return not self.hard_failures

    @property
    def quality_passed(self) -> bool:
        return not self.quality_failures


class RunManifestEntry(StrictModel):
    case_id: str = Field(pattern=CASE_ID_PATTERN)
    dataset_role: DatasetRole = DatasetRole.CALIBRATION
    arm_order: tuple[ExperimentArm, ExperimentArm, ExperimentArm, ExperimentArm]
    real_chart_mapping_id: str = Field(min_length=1, max_length=120)
    mismatched_chart_mapping_id: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_arm_order(self) -> RunManifestEntry:
        if set(self.arm_order) != set(ExperimentArm):
            raise ValueError("arm_order 必须且只能包含 A/B/C/D 各一次")
        if self.real_chart_mapping_id == self.mismatched_chart_mapping_id:
            raise ValueError("C 与 D 组的卦象映射必须不同")
        return self


class ExperimentRunManifest(StrictModel):
    manifest_version: str = Field(min_length=1, max_length=80)
    locked_payload_included: Literal[False] = False
    entries: list[RunManifestEntry] = Field(min_length=1, max_length=200)


class Gate2EvidenceRecord(StrictModel):
    case_id: str = Field(pattern=CASE_ID_PATTERN)
    arm: ExperimentArm
    dataset_role: DatasetRole
    synthetic_data_confirmed: Literal[True]
    chart_mapping_id: str
    contract_version: str
    prompt_version: str
    prompt_sha256: str | None = None
    schema_version: str
    schema_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    validator_version: str
    validator_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reality_reference_map: dict[str, str]
    evidence_reference_map: dict[str, str]
    provider_name: str
    model: str
    reasoning_effort: str
    store: Literal[False]
    tools: list[str] = Field(max_length=0)
    first_raw_output: dict[str, Any] | None
    parsed_output: Gate2ExperimentOutput | None
    validation: Gate2ValidationReport
    usage: Gate2Usage
    latency_ms: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    response_id: str | None
    human_review: dict[str, Any] | None = None
    included_in_formal_comparison: Literal[False] = False


class DryRunStatus(StrEnum):
    BASELINE = "BASELINE"
    VALIDATED = "VALIDATED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    SCHEMA_FAILED = "SCHEMA_FAILED"
    PROVIDER_FAILED = "PROVIDER_FAILED"


class Gate2DryRunResult(StrictModel):
    status: DryRunStatus
    request: Gate2ExperimentRequest
    output: Gate2ExperimentOutput | None
    validation: Gate2ValidationReport
    evidence_record: Gate2EvidenceRecord
    evidence_directory: str | None = None


def gate2_output_schema_sha256() -> str:
    payload = json.dumps(
        Gate2ExperimentOutput.model_json_schema(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
