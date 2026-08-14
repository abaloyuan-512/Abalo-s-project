"""Stage 1D critic-first readiness experiment.

This module is evaluation-only.  A blind readiness critic runs before the
frame proposer.  Deterministic code owns all user-visible state transitions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from typing import Annotated, Any, Literal, Protocol

from openai import OpenAI
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
    BottleneckHypothesis,
    EvidenceRef,
    GenerationMetrics,
    _validate_evidence_ref,
    _validate_question,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    DecisionAxis,
    Stage1BExperimentRequest,
    StatedPremise,
)

CONTRACT_VERSION = "GUANXIANG_CRITIC_FIRST_EXPERIMENT_V1"
MAX_CALLS_PER_ARBITRATION = 2
_INDUCING_PATTERN = re.compile(
    r"(是不是因为|是否因为|你是不是其实|难道不是|其实你是|你真正害怕的是)"
)


class Stage1DError(RuntimeError):
    """Contract, evidence, or orchestration failure in Stage 1D."""


class Stage1DRequest(Stage1BExperimentRequest):
    contract_version: Literal[CONTRACT_VERSION]


class GroundedValue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["GROUNDED"]
    value: str = Field(min_length=1, max_length=180)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)


class UnknownValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["UNKNOWN"]


class NotRelevantValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["NOT_RELEVANT"]


FrameValue = Annotated[
    GroundedValue | UnknownValue | NotRelevantValue,
    Field(discriminator="status"),
]


class AgencyAndAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initiator: FrameValue
    authorizer: FrameValue
    decision_owner: FrameValue
    action_owner: FrameValue


class MotiveAndFearedCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_outcome: FrameValue
    feared_cost: FrameValue


class DecisionFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_axes: list[DecisionAxis] = Field(min_length=1, max_length=2)
    stated_premises: list[StatedPremise] = Field(default_factory=list, max_length=5)
    agency_and_authority: AgencyAndAuthority
    motive_and_feared_cost: MotiveAndFearedCost
    highest_value_unknown: None = None


class FrameProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frame: DecisionFrame
    candidate_hypothesis: BottleneckHypothesis
    proposal_note: str = Field(min_length=4, max_length=220)


class AskOneReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Literal["ASK_ONE"]
    dimension: Literal[
        "DECISION_AXIS",
        "STATED_PREMISE",
        "AGENCY_AUTHORITY",
        "MOTIVE_COST",
    ]
    definition_a: str = Field(min_length=4, max_length=220)
    definition_b: str = Field(min_length=4, max_length=220)
    why_answers_create_different_questions: str = Field(min_length=6, max_length=260)
    question: str = Field(min_length=4, max_length=220)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)


class ReadyReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Literal["READY"]
    resolved_problem_definition: str = Field(min_length=6, max_length=260)
    ready_reason: str = Field(min_length=6, max_length=260)
    non_blocking_unknowns: list[str] = Field(default_factory=list, max_length=2)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)


ReviewDecision = Annotated[
    AskOneReview | ReadyReview,
    Field(discriminator="verdict"),
]


class CriticOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision


class ModelCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    role: Literal["CRITIC", "PROPOSER"]
    attempted: bool = True
    model: str
    prompt_sha256: str
    latency_ms: int = Field(ge=0)
    response_id: str | None = None
    raw_output_text: str | None = None
    raw_parsed_output: dict[str, Any] | None = None
    usage: GenerationMetrics | None = None
    outcome: Literal[
        "SUCCESS",
        "TRANSPORT_ERROR",
        "PARSE_OR_SCHEMA_ERROR",
        "MISSING_PARSED_OUTPUT",
        "SEMANTIC_VALIDATION_ERROR",
    ]
    error_detail: str | None = None


class CriticAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: CriticOutput | None = None
    record: ModelCallRecord


class ProposerAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: FrameProposal | None = None
    record: ModelCallRecord


class Stage1DResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    session_id: str
    status: Literal[
        "ASK_CRITICAL",
        "CONFIRM",
        "INSUFFICIENT_TO_CONFIRM",
        "REVIEW_ERROR",
        "BUDGET_EXCEEDED",
    ]
    assistant_message: str
    next_question: str | None = None
    review: AskOneReview | ReadyReview | None = None
    proposal: FrameProposal | None = None
    hypothesis: BottleneckHypothesis | None = None
    call_records: list[ModelCallRecord] = Field(default_factory=list, max_length=MAX_CALLS_PER_ARBITRATION)
    review_error: str | None = None
    boundary_note: str = (
        "本结果仅用于阶段1D Critic-first就绪实验；不解卦、不排盘、不替用户决定。"
    )


class CriticProtocol(Protocol):
    def generate(self, request: Stage1DRequest, *, call_sequence: int) -> CriticAttempt: ...


class ProposerProtocol(Protocol):
    def generate(self, request: Stage1DRequest, *, call_sequence: int) -> ProposerAttempt: ...


CRITIC_INSTRUCTIONS = """你是观象阶段1D的独立问题定义就绪审查器。你只读取用户原问题和用户回答；你看不到、也不得假设任何Proposer答案、案例标签、标准答案或后续答案。

你只判断：现在是否仍存在两种都合理、但会产生实质不同卜题的问题定义。

按以下顺序审查：
1. 尊重用户明确给定的情境前提，不得用风险猜测替换前提。
2. 拆分复合行动表达中的“是否做”与“怎么做”，以及速度、时机、公开范围、规模等不同语义成分；不得静默合并。
3. 核对发起者、授权者、决定者和执行者；主动意愿不等于已获授权。
4. 核对动机、希望得到的结果和担心承担的代价；只有它们会改变真正判断对象时才阻断。
5. 只有缺口会改变卜题对象、选择轴、固定前提、决定主体或核心取舍时，才能ASK_ONE。

非阻断规则：更多数据、沟通渠道、执行步骤、普通次数或持续时长默认只是执行细节；除非用户明确把该参数本身设为决策对象，否则不得因此追问。问题中的时间范围是观察/决策窗口，不自动代表持续行动频率。

若存在kind=CRITICAL_ANSWER的最新回答，该回答优先于原问题的宽泛措辞。你只能判断首次关键缺口是否已解决，不得转而寻找新的、次优的或执行层缺口。

输出只能是判别联合中的一种：
- ASK_ONE：给出一个dimension、两种不同问题定义、为何会产生不同卜题、一个单句中性问题及逐字证据。
- READY：明确已经收束的问题定义、放行理由、最多两个不阻断未知及逐字证据。

不得生成瓶颈、卜题、建议或行动清单；不得心理诊断、读心、预埋答案；不得提出多个问题。quote必须逐字复制，turn_index从0开始。"""


PROPOSER_INSTRUCTIONS = """你是观象阶段1D的瓶颈提议者。独立Critic已经确认问题定义就绪；你只基于用户原问题和回答形成一个可审计决策框架与候选瓶颈。

权限：
- 只能输出frame、candidate_hypothesis、proposal_note。
- 不得提问、不得改变状态、不得重新做就绪审查、不得生成多个候选、不得生成卜题或建议。
- 不得把事实摘要冒充瓶颈。候选瓶颈必须说明：哪个尚未解决的核心取舍或条件使用户无法决定，以及为什么它会改变选择。

结构与证据：
- GROUNDED必须有非空value及逐字evidence_refs。
- UNKNOWN和NOT_RELEVANT结构中不得补写value或evidence_refs。
- 决策轴、前提、GROUNDED值和候选瓶颈必须引用原问题或单轮回答中的连续原文。
- turn_index从0开始；不跨轮拼接；不挑战用户明确前提；不补事实、不读心。
- frame.highest_value_unknown固定为null。

边界：不生成日期、不替用户决定、不占卜、不解卦、不排盘、不索取数字、不输出行动清单。"""


CRITIC_PROMPT_SHA256 = hashlib.sha256(CRITIC_INSTRUCTIONS.encode("utf-8")).hexdigest()
PROPOSER_PROMPT_SHA256 = hashlib.sha256(PROPOSER_INSTRUCTIONS.encode("utf-8")).hexdigest()


def _catalog(request: Stage1DRequest) -> list[dict[str, Any]]:
    return [
        {"source": "QUESTION_TEXT", "turn_index": None, "text": request.question_text}
    ] + [
        {
            "source": "TURN_ANSWER",
            "turn_index": index,
            "turn_kind": turn.kind,
            "text": turn.answer,
        }
        for index, turn in enumerate(request.turns)
    ]


def _model_input(request: Stage1DRequest) -> dict[str, Any]:
    """Return evidence only: no session/case id, expectations, or proposal."""

    return {
        "question_text": request.question_text,
        "answers": [
            {
                "turn_index": index,
                "turn_kind": turn.kind,
                "context_question": turn.question,
                "answer": turn.answer,
            }
            for index, turn in enumerate(request.turns)
        ],
        "locale": request.locale,
        "evidence_catalog": _catalog(request),
    }


def _usage(response: Any, *, model: str, latency_ms: int) -> GenerationMetrics:
    usage = getattr(response, "usage", None)
    return GenerationMetrics(
        model=model,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        latency_ms=latency_ms,
    )


def _safe_error(exc: Exception) -> str:
    text = str(exc).replace("\n", " ").strip()
    return f"{type(exc).__name__}:{text[:600]}"


def _raw_json_object(raw_text: str | None) -> dict[str, Any] | None:
    if not raw_text:
        return None
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else {"_non_object_json": value}


class OpenAICritic:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1DRequest, *, call_sequence: int) -> CriticAttempt:
        started = time.perf_counter()
        if not os.getenv("OPENAI_API_KEY"):
            return CriticAttempt(
                record=ModelCallRecord(
                    sequence=call_sequence,
                    role="CRITIC",
                    model=self.model,
                    prompt_sha256=CRITIC_PROMPT_SHA256,
                    latency_ms=0,
                    outcome="TRANSPORT_ERROR",
                    error_detail="Stage1DError:OPENAI_API_KEY is unavailable",
                )
            )
        response = None
        try:
            client = self._client_factory(timeout=90.0, max_retries=0)
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": CRITIC_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": json.dumps(_model_input(request), ensure_ascii=False),
                    },
                ],
                text={"format": type_to_text_format_param(CriticOutput)},
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=2_000,
            )
            latency = round((time.perf_counter() - started) * 1000)
            raw_text = getattr(response, "output_text", None)
            parsed = CriticOutput.model_validate_json(raw_text) if raw_text else None
            usage = _usage(response, model=self.model, latency_ms=latency)
            record = ModelCallRecord(
                sequence=call_sequence,
                role="CRITIC",
                model=self.model,
                prompt_sha256=CRITIC_PROMPT_SHA256,
                latency_ms=latency,
                response_id=getattr(response, "id", None),
                raw_output_text=raw_text,
                raw_parsed_output=parsed.model_dump(mode="json") if parsed else None,
                usage=usage,
                outcome="SUCCESS" if parsed else "MISSING_PARSED_OUTPUT",
                error_detail=None if parsed else "response.output_parsed is missing",
            )
            return CriticAttempt(output=parsed, record=record)
        except Exception as exc:  # pragma: no cover - live SDK errors
            latency = round((time.perf_counter() - started) * 1000)
            body = getattr(exc, "body", None)
            raw_text = getattr(response, "output_text", None) if response else None
            usage = None
            if response is not None:
                usage = _usage(response, model=self.model, latency_ms=latency)
            return CriticAttempt(
                record=ModelCallRecord(
                    sequence=call_sequence,
                    role="CRITIC",
                    model=self.model,
                    prompt_sha256=CRITIC_PROMPT_SHA256,
                    latency_ms=latency,
                    response_id=getattr(response, "id", None),
                    raw_output_text=(
                        raw_text if raw_text is not None else json.dumps(body, ensure_ascii=False) if body else None
                    ),
                    raw_parsed_output=_raw_json_object(raw_text),
                    usage=usage,
                    outcome=(
                        "PARSE_OR_SCHEMA_ERROR"
                        if response is not None or isinstance(exc, ValidationError)
                        else "TRANSPORT_ERROR"
                    ),
                    error_detail=_safe_error(exc),
                )
            )


class OpenAIProposer:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1DRequest, *, call_sequence: int) -> ProposerAttempt:
        started = time.perf_counter()
        if not os.getenv("OPENAI_API_KEY"):
            return ProposerAttempt(
                record=ModelCallRecord(
                    sequence=call_sequence,
                    role="PROPOSER",
                    model=self.model,
                    prompt_sha256=PROPOSER_PROMPT_SHA256,
                    latency_ms=0,
                    outcome="TRANSPORT_ERROR",
                    error_detail="Stage1DError:OPENAI_API_KEY is unavailable",
                )
            )
        response = None
        try:
            client = self._client_factory(timeout=90.0, max_retries=0)
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": PROPOSER_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": json.dumps(_model_input(request), ensure_ascii=False),
                    },
                ],
                text={"format": type_to_text_format_param(FrameProposal)},
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=3_200,
            )
            latency = round((time.perf_counter() - started) * 1000)
            raw_text = getattr(response, "output_text", None)
            parsed = FrameProposal.model_validate_json(raw_text) if raw_text else None
            usage = _usage(response, model=self.model, latency_ms=latency)
            record = ModelCallRecord(
                sequence=call_sequence,
                role="PROPOSER",
                model=self.model,
                prompt_sha256=PROPOSER_PROMPT_SHA256,
                latency_ms=latency,
                response_id=getattr(response, "id", None),
                raw_output_text=raw_text,
                raw_parsed_output=parsed.model_dump(mode="json") if parsed else None,
                usage=usage,
                outcome="SUCCESS" if parsed else "MISSING_PARSED_OUTPUT",
                error_detail=None if parsed else "response.output_parsed is missing",
            )
            return ProposerAttempt(output=parsed, record=record)
        except Exception as exc:  # pragma: no cover - live SDK errors
            latency = round((time.perf_counter() - started) * 1000)
            body = getattr(exc, "body", None)
            raw_text = getattr(response, "output_text", None) if response else None
            usage = None
            if response is not None:
                usage = _usage(response, model=self.model, latency_ms=latency)
            return ProposerAttempt(
                record=ModelCallRecord(
                    sequence=call_sequence,
                    role="PROPOSER",
                    model=self.model,
                    prompt_sha256=PROPOSER_PROMPT_SHA256,
                    latency_ms=latency,
                    response_id=getattr(response, "id", None),
                    raw_output_text=(
                        raw_text if raw_text is not None else json.dumps(body, ensure_ascii=False) if body else None
                    ),
                    raw_parsed_output=_raw_json_object(raw_text),
                    usage=usage,
                    outcome=(
                        "PARSE_OR_SCHEMA_ERROR"
                        if response is not None or isinstance(exc, ValidationError)
                        else "TRANSPORT_ERROR"
                    ),
                    error_detail=_safe_error(exc),
                )
            )


def _validate_refs(refs: list[EvidenceRef], request: Stage1DRequest) -> None:
    for reference in refs:
        _validate_evidence_ref(reference, request)


def _validate_review(review: AskOneReview | ReadyReview, request: Stage1DRequest) -> None:
    _validate_refs(review.evidence_refs, request)
    if isinstance(review, AskOneReview):
        if review.question.count("？") + review.question.count("?") != 1:
            raise Stage1DError("critic must ask exactly one question")
        if _INDUCING_PATTERN.search(review.question):
            raise Stage1DError("critic question is inducing")
        _validate_question(review.question)


def _validate_proposal(proposal: FrameProposal, request: Stage1DRequest) -> None:
    for axis in proposal.frame.decision_axes:
        _validate_refs(axis.evidence_refs, request)
    for premise in proposal.frame.stated_premises:
        _validate_refs(premise.evidence_refs, request)
    agency = proposal.frame.agency_and_authority
    motive = proposal.frame.motive_and_feared_cost
    for value in (
        agency.initiator,
        agency.authorizer,
        agency.decision_owner,
        agency.action_owner,
        motive.desired_outcome,
        motive.feared_cost,
    ):
        if isinstance(value, GroundedValue):
            _validate_refs(value.evidence_refs, request)
    _validate_refs(proposal.candidate_hypothesis.evidence_refs, request)


def _critical_answer_index(request: Stage1DRequest) -> int | None:
    indexes = [index for index, turn in enumerate(request.turns) if turn.kind == "CRITICAL_ANSWER"]
    if len(indexes) > 1:
        raise Stage1DError("at most one critical answer is allowed")
    return indexes[0] if indexes else None


def _frame_refs(frame: DecisionFrame) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for axis in frame.decision_axes:
        refs.extend(axis.evidence_refs)
    for premise in frame.stated_premises:
        refs.extend(premise.evidence_refs)
    agency = frame.agency_and_authority
    motive = frame.motive_and_feared_cost
    for value in (
        agency.initiator,
        agency.authorizer,
        agency.decision_owner,
        agency.action_owner,
        motive.desired_outcome,
        motive.feared_cost,
    ):
        if isinstance(value, GroundedValue):
            refs.extend(value.evidence_refs)
    return refs


def _mark_semantic_error(record: ModelCallRecord, exc: Exception) -> None:
    record.outcome = "SEMANTIC_VALIDATION_ERROR"
    record.error_detail = _safe_error(exc)


def _has_turn_ref(refs: list[EvidenceRef], turn_index: int) -> bool:
    return any(ref.source == "TURN_ANSWER" and ref.turn_index == turn_index for ref in refs)


def arbitrate_stage1d_request(
    payload: object,
    *,
    call_sequence_start: int = 1,
    critic: CriticProtocol | None = None,
    proposer: ProposerProtocol | None = None,
) -> dict[str, Any]:
    try:
        request = Stage1DRequest.model_validate(payload)
        critical_index = _critical_answer_index(request)
    except Exception as exc:
        raise ValueError("invalid stage1d request") from exc

    selected_critic = critic or OpenAICritic(
        model=os.getenv("ABALO_STAGE1D_CRITIC_MODEL", DEFAULT_MODEL)
    )
    selected_proposer = proposer or OpenAIProposer(
        model=os.getenv("ABALO_STAGE1D_PROPOSER_MODEL", DEFAULT_MODEL)
    )
    records: list[ModelCallRecord] = []

    critic_attempt = selected_critic.generate(request, call_sequence=call_sequence_start)
    records.append(critic_attempt.record)
    if critic_attempt.output is None:
        return Stage1DResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="独立就绪审查失败，本次不能形成瓶颈。",
            call_records=records,
            review_error=f"CRITIC_{critic_attempt.record.outcome}:{critic_attempt.record.error_detail}",
        ).model_dump(mode="json")

    review = critic_attempt.output.decision
    try:
        _validate_review(review, request)
    except Exception as exc:
        _mark_semantic_error(critic_attempt.record, exc)
        return Stage1DResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="独立就绪审查未通过证据验证，本次不能形成瓶颈。",
            review=review,
            call_records=records,
            review_error=f"CRITIC_SEMANTIC_VALIDATION_ERROR:{_safe_error(exc)}",
        ).model_dump(mode="json")

    if isinstance(review, AskOneReview):
        if critical_index is not None:
            return Stage1DResponse(
                session_id=request.session_id,
                status="INSUFFICIENT_TO_CONFIRM",
                assistant_message="唯一一次关键回答后仍存在会改变卜题定义的缺口，本次停止形成瓶颈。",
                review=review,
                call_records=records,
            ).model_dump(mode="json")
        return Stage1DResponse(
            session_id=request.session_id,
            status="ASK_CRITICAL",
            assistant_message="在形成瓶颈前，还需要先澄清一个会改变卜题定义的问题。",
            next_question=review.question,
            review=review,
            call_records=records,
        ).model_dump(mode="json")

    if critical_index is not None and not _has_turn_ref(review.evidence_refs, critical_index):
        exc = Stage1DError("READY review must cite the critical answer")
        _mark_semantic_error(critic_attempt.record, exc)
        return Stage1DResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="关键回答没有进入就绪判断，本次不能形成瓶颈。",
            review=review,
            call_records=records,
            review_error=f"ARBITER_ERROR:{exc}",
        ).model_dump(mode="json")

    if len(records) >= MAX_CALLS_PER_ARBITRATION:
        return Stage1DResponse(
            session_id=request.session_id,
            status="BUDGET_EXCEEDED",
            assistant_message="本次调用预算已用尽，不能形成瓶颈。",
            review=review,
            call_records=records,
            review_error="ARBITER_ERROR:per-arbitration call budget exceeded",
        ).model_dump(mode="json")

    proposer_attempt = selected_proposer.generate(
        request, call_sequence=call_sequence_start + len(records)
    )
    records.append(proposer_attempt.record)
    if proposer_attempt.output is None:
        return Stage1DResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="瓶颈提议失败，本次不能进入确认。",
            review=review,
            call_records=records,
            review_error=f"PROPOSER_{proposer_attempt.record.outcome}:{proposer_attempt.record.error_detail}",
        ).model_dump(mode="json")

    proposal = proposer_attempt.output
    try:
        _validate_proposal(proposal, request)
        if critical_index is not None:
            if not _has_turn_ref(proposal.candidate_hypothesis.evidence_refs, critical_index):
                raise Stage1DError("hypothesis must cite the critical answer")
            if not _has_turn_ref(_frame_refs(proposal.frame), critical_index):
                raise Stage1DError("frame must cite the critical answer")
    except Exception as exc:
        _mark_semantic_error(proposer_attempt.record, exc)
        return Stage1DResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="瓶颈提议未通过证据验证，本次不能进入确认。",
            review=review,
            proposal=proposal,
            call_records=records,
            review_error=f"PROPOSER_SEMANTIC_VALIDATION_ERROR:{_safe_error(exc)}",
        ).model_dump(mode="json")

    hypothesis = proposal.candidate_hypothesis
    question = f"我的理解是：{hypothesis.statement}。这个理解准确吗？如果不准确，请纠正。"
    return Stage1DResponse(
        session_id=request.session_id,
        status="CONFIRM",
        assistant_message="问题定义已经收束，可以请你确认当前瓶颈理解。",
        next_question=question,
        review=review,
        proposal=proposal,
        hypothesis=hypothesis,
        call_records=records,
    ).model_dump(mode="json")
