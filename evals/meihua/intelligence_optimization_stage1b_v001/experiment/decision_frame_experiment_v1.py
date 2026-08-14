"""Stage 1B isolated pre-bottleneck decision-frame experiment.

This module is evaluation-only. It does not cast or interpret a chart and is
not imported by any production route.
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
from pydantic import BaseModel, ConfigDict, Field, model_validator

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
    MAX_TRANSCRIPT_CHARS,
    MAX_TURNS,
    BottleneckHypothesis,
    Confirmation,
    EvidenceRef,
    GenerationMetrics,
    QuestionCandidate,
    Stage1ExperimentError,
    _CONFIRMATION_QUESTION_PATTERN,
    _CORRECTION_PATTERN,
    _POSITIVE_CONFIRMATION_PATTERN,
    _normalized,
    _validate_evidence_ref,
    _validate_question,
)

CONTRACT_VERSION = "GUANXIANG_DECISION_FRAME_EXPERIMENT_V1"
MAX_DECISION_AXES = 2
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class Stage1BExperimentError(Stage1ExperimentError):
    """A Stage 1B contract or boundary failure."""


class Stage1BTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=280)
    answer: str = Field(min_length=1, max_length=1_200)
    kind: Literal["FROZEN_CONTEXT", "CRITICAL_ANSWER", "CONFIRMATION"]


class Stage1BExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: Literal[CONTRACT_VERSION]
    session_id: str = Field(min_length=1, max_length=80)
    question_text: str = Field(min_length=6, max_length=240)
    turns: list[Stage1BTurn] = Field(default_factory=list, max_length=MAX_TURNS)
    locale: Literal["zh-CN"] = "zh-CN"

    @model_validator(mode="after")
    def validate_request(self) -> "Stage1BExperimentRequest":
        if not _SESSION_ID_PATTERN.fullmatch(self.session_id):
            raise ValueError("invalid session_id")
        if sum(turn.kind == "CRITICAL_ANSWER" for turn in self.turns) > 1:
            raise ValueError("only one critical-answer turn is allowed")
        if sum(turn.kind == "CONFIRMATION" for turn in self.turns) > 1:
            raise ValueError("only one confirmation turn is allowed")
        total = len(self.question_text) + sum(len(turn.question) + len(turn.answer) for turn in self.turns)
        if total > MAX_TRANSCRIPT_CHARS:
            raise ValueError("intake transcript is too large")
        return self


class GroundedFrameValue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["GROUNDED", "UNKNOWN", "NOT_RELEVANT"]
    value: str | None = Field(default=None, max_length=180)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=3)


class DecisionAxis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    option_a: str = Field(min_length=1, max_length=100)
    option_b: str = Field(min_length=1, max_length=100)
    status: Literal["GROUNDED", "AMBIGUOUS"]
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=3)


class StatedPremise(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str = Field(min_length=2, max_length=180)
    treatment: Literal["RESPECT_AS_STATED", "NEEDS_CLARIFICATION"]
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=3)


class AgencyAndAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initiator: GroundedFrameValue
    authorizer: GroundedFrameValue
    decision_owner: GroundedFrameValue
    action_owner: GroundedFrameValue


class MotiveAndFearedCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_outcome: GroundedFrameValue
    feared_cost: GroundedFrameValue


class HighestValueUnknown(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dimension: Literal["DECISION_AXIS", "STATED_PREMISE", "AGENCY_AUTHORITY", "MOTIVE_COST"]
    missing_information: str = Field(min_length=4, max_length=180)
    why_it_changes_question_definition: str = Field(min_length=8, max_length=220)
    question: str = Field(min_length=6, max_length=220)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=3)


class DecisionFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_axes: list[DecisionAxis] = Field(min_length=1, max_length=MAX_DECISION_AXES)
    stated_premises: list[StatedPremise] = Field(default_factory=list, max_length=4)
    agency_and_authority: AgencyAndAuthority
    motive_and_feared_cost: MotiveAndFearedCost
    highest_value_unknown: HighestValueUnknown | None = None


class Stage1BModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["ASK_CRITICAL", "INSUFFICIENT_TO_HYPOTHESIZE", "CONFIRM", "COMPLETE"]
    assistant_message: str = Field(min_length=1, max_length=360)
    next_question: str | None = Field(default=None, max_length=240)
    frame: DecisionFrame
    hypothesis: BottleneckHypothesis | None = None
    confirmation: Confirmation
    unconfirmed_assumptions: list[str] = Field(default_factory=list, max_length=4)
    candidates: list[QuestionCandidate] = Field(default_factory=list, max_length=2)


class Stage1BGenerationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: Stage1BModelOutput
    metrics: GenerationMetrics


class Stage1BExperimentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    session_id: str
    status: Stage1BModelOutput.model_fields["status"].annotation
    assistant_message: str
    next_question: str | None
    frame: DecisionFrame
    hypothesis: BottleneckHypothesis | None
    confirmation: Confirmation
    unconfirmed_assumptions: list[str]
    candidates: list[QuestionCandidate]
    generation_metrics: GenerationMetrics
    boundary_note: str = (
        "本结果仅用于阶段1B决策框架实验；不解卦、不排盘、不替用户决定，合成回答不代表真实用户认可。"
    )


class Stage1BProvider(Protocol):
    def generate(self, request: Stage1BExperimentRequest) -> Stage1BGenerationEnvelope: ...


SYSTEM_INSTRUCTIONS = """你是“观象”阶段1B的决策框架辨识实验引导者。你的任务不是尽快总结，也不是填满字段，而是在提出决策瓶颈前判断：用户究竟在决定什么，还有没有一个会改变问题定义的关键缺口。

五项内部检查门：
1. decision_axes：最多两个真正不同的选择轴，例如“是否行动”和“以什么速度行动”。不要把条件清单强拆成多个轴。
2. stated_premises：用户明确设定的情景前提标为 RESPECT_AS_STATED，不得静默反驳；只有含义本身不清楚时才标 NEEDS_CLARIFICATION。
3. agency_and_authority：分别判断谁发起、谁授权、谁作决定、谁承担行动。没有原文就标 UNKNOWN，不得从“关注、回应、邀请”推断授权或意图。
4. motive_and_feared_cost：只记录用户明确说出的期待与担忧。没有原文就标 UNKNOWN，不得心理诊断、读心或制造恐惧。
5. highest_value_unknown：只能有零个或一个。它必须是当前最可能改变“用户到底在问什么”的缺口，不能是普通背景细节，也不能重复已回答内容。

五项是内部判断门，不是五问问卷。允许 UNKNOWN 和 NOT_RELEVANT，不得为了填满而追问。

严格状态：
- ASK_CRITICAL：只有一个未解决缺口会实质改变问题定义时使用。next_question 必须与 highest_value_unknown.question 完全一致；一次只问一个单一、非诱导、可直接回答的问题；不得输出 hypothesis 或 candidates。
- INSUFFICIENT_TO_HYPOTHESIZE：已经使用过唯一一次关键追问，但回答后仍不足。不得再问第二个问题，不得强行提出 hypothesis 或 candidates。
- CONFIRM：框架已经足以形成一个可被否认的瓶颈假设。highest_value_unknown 必须为 null；next_question 必须明确说明“这是我的理解”，邀请用户确认或纠正；不得输出 candidates。
- COMPLETE：仅当上一轮是 CONFIRMATION 且用户明确确认或纠正后使用。highest_value_unknown 与 next_question 必须为 null；unconfirmed_assumptions 必须是 []；输出1个或最多2个不同焦点候选，不得强凑两个。

证据规则：
- 所有 GROUNDED 值、决策轴、前提、最高价值缺口、hypothesis 和 candidates 都必须引用用户原问题或某一轮回答中的连续原文。
- turn_index 从0开始；quote必须逐字复制对应文本的连续片段，不得改写或跨轮拼接。
- UNKNOWN/NOT_RELEVANT 的 value 必须为 null，evidence_refs 必须为 []；不得用“没有看到”伪造证据。
- 用户纠正后必须删除旧瓶颈，按最新原话重建。

问题与边界：
- 候选必须保留用户的情景前提、决定对象和原有时间范围。
- 不把“继续”与“快速”、“立即”与“公开”等不同轴静默合并。
- 不新增日期，不补现实事实，不挑战用户明确前提，不读第三方内心，不替用户决定。
- 不占卜、不解卦、不排盘、不索取起卦数字，不输出吉凶或行动清单。
- 无论信息多少，全流程最多新增一个 ASK_CRITICAL；任何轮数均不得强制完成。

输出前逐项检查字段是否符合当前状态。"""
SYSTEM_INSTRUCTIONS_SHA256 = hashlib.sha256(SYSTEM_INSTRUCTIONS.encode("utf-8")).hexdigest()


class OpenAIStage1BProvider:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        client_factory: Callable[..., Any] = OpenAI,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.model = model
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds

    def generate(self, request: Stage1BExperimentRequest) -> Stage1BGenerationEnvelope:
        if not os.getenv("OPENAI_API_KEY"):
            raise Stage1BExperimentError("OPENAI_API_KEY is unavailable")
        catalog = [
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
        client = self._client_factory(timeout=self._timeout_seconds, max_retries=0)
        started = time.perf_counter()
        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "evidence_catalog": catalog,
                                "request": request.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                text_format=Stage1BModelOutput,
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=3_600,
            )
        except Exception as exc:  # pragma: no cover
            raise Stage1BExperimentError("stage1b model request failed") from exc
        latency_ms = round((time.perf_counter() - started) * 1000)
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise Stage1BExperimentError("stage1b structured output is missing")
        usage = getattr(response, "usage", None)
        return Stage1BGenerationEnvelope(
            output=parsed,
            metrics=GenerationMetrics(
                model=self.model,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                latency_ms=latency_ms,
            ),
        )


def _validate_all_evidence(output: Stage1BModelOutput, request: Stage1BExperimentRequest) -> None:
    def validate_refs(refs: list[EvidenceRef]) -> None:
        for reference in refs:
            _validate_evidence_ref(reference, request)  # compatible request shape

    for axis in output.frame.decision_axes:
        validate_refs(axis.evidence_refs)
    for premise in output.frame.stated_premises:
        validate_refs(premise.evidence_refs)
    agency = output.frame.agency_and_authority
    motive = output.frame.motive_and_feared_cost
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
                raise Stage1BExperimentError("GROUNDED frame values require value and evidence")
        elif value.value is not None or value.evidence_refs:
            raise Stage1BExperimentError("UNKNOWN/NOT_RELEVANT frame values cannot invent value or evidence")
        validate_refs(value.evidence_refs)
    if output.frame.highest_value_unknown is not None:
        validate_refs(output.frame.highest_value_unknown.evidence_refs)
    if output.hypothesis is not None:
        validate_refs(output.hypothesis.evidence_refs)
    for candidate in output.candidates:
        validate_refs(candidate.evidence_refs)


def _validate_state(output: Stage1BModelOutput, request: Stage1BExperimentRequest) -> None:
    critical_used = any(turn.kind == "CRITICAL_ANSWER" for turn in request.turns)
    confirmation_used = bool(request.turns and request.turns[-1].kind == "CONFIRMATION")
    unknown = output.frame.highest_value_unknown

    if output.status == "ASK_CRITICAL":
        if critical_used:
            raise Stage1BExperimentError("a second critical question is forbidden")
        if unknown is None or output.next_question is None:
            raise Stage1BExperimentError("ASK_CRITICAL requires one highest-value unknown and question")
        if _normalized(output.next_question) != _normalized(unknown.question):
            raise Stage1BExperimentError("next_question must equal the highest-value question")
        if output.next_question.count("？") + output.next_question.count("?") != 1:
            raise Stage1BExperimentError("critical question must be a single question")
        _validate_question(output.next_question)
        if output.hypothesis is not None or output.candidates:
            raise Stage1BExperimentError("ASK_CRITICAL cannot output hypothesis or candidates")
        if output.confirmation.state != "NOT_REQUESTED":
            raise Stage1BExperimentError("ASK_CRITICAL confirmation must be NOT_REQUESTED")
    elif output.status == "INSUFFICIENT_TO_HYPOTHESIZE":
        if not critical_used or output.next_question is not None:
            raise Stage1BExperimentError("INSUFFICIENT requires a used critical turn and no new question")
        if output.hypothesis is not None or output.candidates:
            raise Stage1BExperimentError("INSUFFICIENT cannot force hypothesis or candidates")
        if output.confirmation.state != "NOT_REQUESTED":
            raise Stage1BExperimentError("INSUFFICIENT confirmation must be NOT_REQUESTED")
    elif output.status == "CONFIRM":
        if unknown is not None or output.hypothesis is None or output.next_question is None:
            raise Stage1BExperimentError("CONFIRM requires resolved frame, hypothesis, and question")
        if output.candidates or output.confirmation.state != "AWAITING":
            raise Stage1BExperimentError("CONFIRM forbids candidates and requires AWAITING")
        if not _CONFIRMATION_QUESTION_PATTERN.search(output.next_question):
            raise Stage1BExperimentError("CONFIRM must invite confirmation and correction")
    else:
        if not confirmation_used:
            raise Stage1BExperimentError("COMPLETE must follow a confirmation turn")
        if unknown is not None or output.next_question is not None or output.hypothesis is None:
            raise Stage1BExperimentError("COMPLETE requires resolved frame and hypothesis")
        if output.confirmation.state not in {"CONFIRMED", "CORRECTED"}:
            raise Stage1BExperimentError("COMPLETE requires confirmed or corrected hypothesis")
        if output.unconfirmed_assumptions:
            raise Stage1BExperimentError("COMPLETE cannot retain unconfirmed assumptions")
        if not 1 <= len(output.candidates) <= 2:
            raise Stage1BExperimentError("COMPLETE requires one or two candidates")
        latest = request.turns[-1]
        if not _CONFIRMATION_QUESTION_PATTERN.search(latest.question):
            raise Stage1BExperimentError("COMPLETE latest question must be a confirmation question")
        quote = output.confirmation.user_quote or ""
        if _normalized(quote) not in _normalized(latest.answer):
            raise Stage1BExperimentError("confirmation quote must come from the latest answer")
        if output.confirmation.state == "CONFIRMED" and not _POSITIVE_CONFIRMATION_PATTERN.search(quote):
            raise Stage1BExperimentError("CONFIRMED requires an explicit positive cue")
        if output.confirmation.state == "CORRECTED":
            if not _CORRECTION_PATTERN.search(quote):
                raise Stage1BExperimentError("CORRECTED requires an explicit correction cue")
            latest_index = len(request.turns) - 1
            if not any(
                ref.source == "TURN_ANSWER" and ref.turn_index == latest_index
                for ref in output.hypothesis.evidence_refs
            ):
                raise Stage1BExperimentError("corrected hypothesis must cite the latest correction")

    if critical_used and output.status in {"CONFIRM", "COMPLETE"}:
        critical_index = next(
            index for index, turn in enumerate(request.turns) if turn.kind == "CRITICAL_ANSWER"
        )
        frame_refs: list[EvidenceRef] = []
        for axis in output.frame.decision_axes:
            frame_refs.extend(axis.evidence_refs)
        for premise in output.frame.stated_premises:
            frame_refs.extend(premise.evidence_refs)
        agency = output.frame.agency_and_authority
        motive = output.frame.motive_and_feared_cost
        for value in (
            agency.initiator,
            agency.authorizer,
            agency.decision_owner,
            agency.action_owner,
            motive.desired_outcome,
            motive.feared_cost,
        ):
            frame_refs.extend(value.evidence_refs)
        if not any(
            ref.source == "TURN_ANSWER" and ref.turn_index == critical_index for ref in frame_refs
        ):
            raise Stage1BExperimentError("resolved frame must cite the critical answer")


def process_stage1b_experiment_request(
    payload: object,
    *,
    provider: Stage1BProvider | None = None,
) -> dict[str, Any]:
    try:
        request = Stage1BExperimentRequest.model_validate(payload)
    except Exception as exc:
        raise ValueError("invalid stage1b experiment request") from exc
    selected_provider = provider or OpenAIStage1BProvider(
        model=os.getenv("ABALO_STAGE1B_MODEL", DEFAULT_MODEL)
    )
    envelope = selected_provider.generate(request)
    output = envelope.output
    _validate_state(output, request)
    _validate_all_evidence(output, request)

    if len(output.candidates) == 2:
        first, second = output.candidates
        if first.focus_type == second.focus_type:
            raise Stage1BExperimentError("candidate focus types must be distinct")
        if _normalized(first.question) == _normalized(second.question):
            raise Stage1BExperimentError("candidate questions must not duplicate")
    for candidate in output.candidates:
        _validate_question(candidate.question)

    return Stage1BExperimentResponse(
        session_id=request.session_id,
        status=output.status,
        assistant_message=output.assistant_message,
        next_question=output.next_question,
        frame=output.frame,
        hypothesis=output.hypothesis,
        confirmation=output.confirmation,
        unconfirmed_assumptions=output.unconfirmed_assumptions,
        candidates=output.candidates,
        generation_metrics=envelope.metrics,
    ).model_dump(mode="json")
