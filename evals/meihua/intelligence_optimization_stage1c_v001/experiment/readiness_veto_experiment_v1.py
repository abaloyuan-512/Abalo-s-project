"""Stage 1C independent bottleneck-readiness veto experiment.

The proposer and critic are separate stateless model calls. Only deterministic
code maps the critic verdict to the next user-visible state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from typing import Any, Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
    BottleneckHypothesis,
    EvidenceRef,
    GenerationMetrics,
    _normalized,
    _validate_evidence_ref,
    _validate_question,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    DecisionFrame,
    Stage1BExperimentRequest,
)

CONTRACT_VERSION = "GUANXIANG_READINESS_VETO_EXPERIMENT_V1"
_INDUCING_PATTERN = re.compile(r"(是不是因为|是否因为|你是不是其实|难道不是|其实你是|你真正害怕的是)")


class Stage1CError(RuntimeError):
    """Contract or evidence failure in the isolated Stage 1C experiment."""


class Stage1CRequest(Stage1BExperimentRequest):
    contract_version: Literal[CONTRACT_VERSION]


class FrameProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frame: DecisionFrame
    candidate_hypothesis: BottleneckHypothesis
    proposal_note: str = Field(min_length=4, max_length=220)


class ReadinessReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Literal["VETO_ASK", "ALLOW_CONFIRM"]
    critical_gap: str | None = Field(default=None, max_length=180)
    alternative_problem_definition: str | None = Field(default=None, max_length=220)
    definition_change_reason: str | None = Field(default=None, max_length=240)
    question: str | None = Field(default=None, max_length=220)
    ready_reason: str | None = Field(default=None, max_length=220)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=4)


class ProposalEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: FrameProposal
    metrics: GenerationMetrics


class ReviewEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: ReadinessReview
    metrics: GenerationMetrics


class Stage1CResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    session_id: str
    status: Literal["ASK_CRITICAL", "CONFIRM", "INSUFFICIENT_TO_CONFIRM", "REVIEW_ERROR"]
    assistant_message: str
    next_question: str | None = None
    proposal: FrameProposal | None = None
    review: ReadinessReview | None = None
    hypothesis: BottleneckHypothesis | None = None
    proposer_metrics: GenerationMetrics | None = None
    critic_metrics: GenerationMetrics | None = None
    review_error: str | None = None
    boundary_note: str = (
        "本结果仅用于阶段1C独立就绪否决实验；不解卦、不排盘、不替用户决定。"
    )


class ProposerProtocol(Protocol):
    def generate(self, request: Stage1CRequest) -> ProposalEnvelope: ...


class CriticProtocol(Protocol):
    def generate(self, request: Stage1CRequest, proposal: FrameProposal) -> ReviewEnvelope: ...


PROPOSER_INSTRUCTIONS = """你是观象阶段1C的 Frame Proposer。你只能基于用户原问题和回答提出一个可审计的决策框架与候选瓶颈。

严格权限：
- 只能输出 frame、candidate_hypothesis、proposal_note。
- 不得向用户提问，不得输出状态，不得决定ASK或CONFIRM，不得生成卜题候选。
- frame沿用既有 decision_axes、stated_premises、agency_and_authority、motive_and_feared_cost；不得增加新字段。
- frame.highest_value_unknown 必须为 null；是否存在关键缺口由独立Critic判断，不属于你的权限。

证据：
- 所有GROUNDED值、决策轴、前提和候选瓶颈必须引用原问题或单轮回答的连续原文。
- turn_index从0开始，quote逐字复制，不跨轮拼接。
- 无原文支持就标UNKNOWN/NOT_RELEVANT，不补事实、不读心、不挑战用户明确前提。

边界：不生成日期、不替用户决定、不占卜、不解卦、不排盘、不索取数字、不输出行动清单。"""


CRITIC_INSTRUCTIONS = """你是观象阶段1C的独立 Bottleneck Readiness Critic。你不帮助Proposer润色，也不判断建议好不好。你只审查：是否仍存在另一种合理的问题定义，它会导致一个实质不同的卜题。

你可以看到用户原问题、回答、Proposer的frame和candidate_hypothesis，但看不到案例期望或后续回答。

输出权限只有两种：
1. VETO_ASK：仍有一个尚未解决、且会改变卜题对象/选择轴/情景前提/行动主体/动机代价的缺口。此时必须输出：
   - exactly one critical_gap；
   - exactly one alternative_problem_definition；
   - definition_change_reason，说明它会产生怎样不同的卜题；
   - exactly one单句、中性、非诱导、可直接回答的问题；
   - 支持“存在歧义或缺口”的用户逐字证据。
2. ALLOW_CONFIRM：没有发现仍会产生实质不同卜题的问题定义。critical_gap、alternative_problem_definition、definition_change_reason、question必须为null，只写ready_reason与证据。

审查重点：
- 复合措辞是否把两个决策轴静默合并，例如是否行动与行动速度、启动时机与公开方式；
- 主体或授权缺失是否会把“是否要做”改成“如何执行”；
- 在关系或价值取舍中，动机/代价缺失是否会改变真正要判断的对象；
- 用户明确前提必须尊重，不能因为现实风险而静默改写；
- 普通执行细节、更多数据或不会改变卜题的问题，不足以VETO。

不得：改写候选瓶颈、生成卜题、列多个缺口、提出多个问题、给答案或行动建议、心理诊断、读心、使用“是不是因为……”等预埋答案问法。

证据quote必须逐字复制，turn_index从0开始。"""

PROPOSER_PROMPT_SHA256 = hashlib.sha256(PROPOSER_INSTRUCTIONS.encode("utf-8")).hexdigest()
CRITIC_PROMPT_SHA256 = hashlib.sha256(CRITIC_INSTRUCTIONS.encode("utf-8")).hexdigest()


def _catalog(request: Stage1CRequest) -> list[dict[str, Any]]:
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


class OpenAIProposer:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1CRequest) -> ProposalEnvelope:
        if not os.getenv("OPENAI_API_KEY"):
            raise Stage1CError("OPENAI_API_KEY is unavailable")
        client = self._client_factory(timeout=90.0, max_retries=0)
        started = time.perf_counter()
        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": PROPOSER_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"evidence_catalog": _catalog(request), "request": request.model_dump(mode="json")},
                            ensure_ascii=False,
                        ),
                    },
                ],
                text_format=FrameProposal,
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=3_200,
            )
        except Exception as exc:  # pragma: no cover
            raise Stage1CError("proposer request failed") from exc
        usage = getattr(response, "usage", None)
        return ProposalEnvelope(
            output=response.output_parsed,
            metrics=GenerationMetrics(
                model=self.model,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                latency_ms=round((time.perf_counter() - started) * 1000),
            ),
        )


class OpenAICritic:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1CRequest, proposal: FrameProposal) -> ReviewEnvelope:
        if not os.getenv("OPENAI_API_KEY"):
            raise Stage1CError("OPENAI_API_KEY is unavailable")
        client = self._client_factory(timeout=90.0, max_retries=0)
        started = time.perf_counter()
        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": CRITIC_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "evidence_catalog": _catalog(request),
                                "request": request.model_dump(mode="json"),
                                "proposal": proposal.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                text_format=ReadinessReview,
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=1_800,
            )
        except Exception as exc:  # pragma: no cover
            raise Stage1CError("critic request failed") from exc
        usage = getattr(response, "usage", None)
        return ReviewEnvelope(
            output=response.output_parsed,
            metrics=GenerationMetrics(
                model=self.model,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                latency_ms=round((time.perf_counter() - started) * 1000),
            ),
        )


def _validate_refs(refs: list[EvidenceRef], request: Stage1CRequest) -> None:
    for reference in refs:
        _validate_evidence_ref(reference, request)


def _validate_proposal(proposal: FrameProposal, request: Stage1CRequest) -> None:
    if proposal.frame.highest_value_unknown is not None:
        raise Stage1CError("proposer cannot decide the highest-value unknown")
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
        if value.status == "GROUNDED":
            if not value.value or not value.evidence_refs:
                raise Stage1CError("grounded proposal values require evidence")
        elif value.value is not None or value.evidence_refs:
            raise Stage1CError("unknown proposal values cannot invent content")
        _validate_refs(value.evidence_refs, request)
    _validate_refs(proposal.candidate_hypothesis.evidence_refs, request)


def _validate_review(review: ReadinessReview, request: Stage1CRequest) -> None:
    _validate_refs(review.evidence_refs, request)
    if review.verdict == "VETO_ASK":
        if not all(
            [
                review.critical_gap,
                review.alternative_problem_definition,
                review.definition_change_reason,
                review.question,
                review.evidence_refs,
            ]
        ):
            raise Stage1CError("VETO_ASK requires one complete grounded gap")
        if review.ready_reason is not None:
            raise Stage1CError("VETO_ASK cannot include ready_reason")
        assert review.question is not None
        if review.question.count("？") + review.question.count("?") != 1:
            raise Stage1CError("critic must ask exactly one question")
        if _INDUCING_PATTERN.search(review.question):
            raise Stage1CError("critic question is inducing")
        _validate_question(review.question)
    else:
        if any(
            value is not None
            for value in (
                review.critical_gap,
                review.alternative_problem_definition,
                review.definition_change_reason,
                review.question,
            )
        ):
            raise Stage1CError("ALLOW_CONFIRM cannot include a gap or question")
        if not review.ready_reason or not review.evidence_refs:
            raise Stage1CError("ALLOW_CONFIRM requires grounded ready_reason")


def _critical_answer_index(request: Stage1CRequest) -> int | None:
    for index, turn in enumerate(request.turns):
        if turn.kind == "CRITICAL_ANSWER":
            return index
    return None


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
        refs.extend(value.evidence_refs)
    return refs


def arbitrate_stage1c_request(
    payload: object,
    *,
    proposer: ProposerProtocol | None = None,
    critic: CriticProtocol | None = None,
) -> dict[str, Any]:
    try:
        request = Stage1CRequest.model_validate(payload)
    except Exception as exc:
        raise ValueError("invalid stage1c request") from exc
    selected_proposer = proposer or OpenAIProposer(
        model=os.getenv("ABALO_STAGE1C_PROPOSER_MODEL", DEFAULT_MODEL)
    )
    selected_critic = critic or OpenAICritic(
        model=os.getenv("ABALO_STAGE1C_CRITIC_MODEL", DEFAULT_MODEL)
    )
    try:
        proposal_envelope = selected_proposer.generate(request)
        _validate_proposal(proposal_envelope.output, request)
    except Exception as exc:
        return Stage1CResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="决策框架提议未通过证据审查，本次不能进入瓶颈确认。",
            review_error=f"PROPOSER_ERROR:{type(exc).__name__}:{exc}",
        ).model_dump(mode="json")

    try:
        review_envelope = selected_critic.generate(request, proposal_envelope.output)
        _validate_review(review_envelope.output, request)
    except Exception as exc:
        return Stage1CResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="独立就绪审查失败，本次按关闭原则不能进入瓶颈确认。",
            proposal=proposal_envelope.output,
            proposer_metrics=proposal_envelope.metrics,
            review_error=f"CRITIC_ERROR:{type(exc).__name__}:{exc}",
        ).model_dump(mode="json")

    proposal_output = proposal_envelope.output
    review_output = review_envelope.output
    critical_index = _critical_answer_index(request)
    if review_output.verdict == "VETO_ASK":
        if critical_index is not None:
            return Stage1CResponse(
                session_id=request.session_id,
                status="INSUFFICIENT_TO_CONFIRM",
                assistant_message="唯一一次关键追问后，仍存在会改变卜题定义的缺口；本次停止形成瓶颈。",
                proposal=proposal_output,
                review=review_output,
                proposer_metrics=proposal_envelope.metrics,
                critic_metrics=review_envelope.metrics,
            ).model_dump(mode="json")
        return Stage1CResponse(
            session_id=request.session_id,
            status="ASK_CRITICAL",
            assistant_message="在形成瓶颈前，还需要先澄清一个会改变卜题定义的问题。",
            next_question=review_output.question,
            proposal=proposal_output,
            review=review_output,
            proposer_metrics=proposal_envelope.metrics,
            critic_metrics=review_envelope.metrics,
        ).model_dump(mode="json")

    if critical_index is not None:
        refs = proposal_output.candidate_hypothesis.evidence_refs
        if not any(
            ref.source == "TURN_ANSWER" and ref.turn_index == critical_index for ref in refs
        ) or not any(
            ref.source == "TURN_ANSWER" and ref.turn_index == critical_index
            for ref in _frame_refs(proposal_output.frame)
        ) or not any(
            ref.source == "TURN_ANSWER" and ref.turn_index == critical_index
            for ref in review_output.evidence_refs
        ):
            return Stage1CResponse(
                session_id=request.session_id,
                status="REVIEW_ERROR",
                assistant_message="关键回答没有进入更新后的瓶颈证据，本次不能确认。",
                proposal=proposal_output,
                review=review_output,
                proposer_metrics=proposal_envelope.metrics,
                critic_metrics=review_envelope.metrics,
                review_error="ARBITER_ERROR:critical answer not cited by frame, hypothesis, and review",
            ).model_dump(mode="json")

    hypothesis = proposal_output.candidate_hypothesis
    question = f"我的理解是：{hypothesis.statement}。这个理解准确吗？如果不准确，请纠正。"
    return Stage1CResponse(
        session_id=request.session_id,
        status="CONFIRM",
        assistant_message="独立审查没有发现仍会改变卜题定义的关键缺口，可以请你确认当前理解。",
        next_question=question,
        proposal=proposal_output,
        review=review_output,
        hypothesis=hypothesis,
        proposer_metrics=proposal_envelope.metrics,
        critic_metrics=review_envelope.metrics,
    ).model_dump(mode="json")
