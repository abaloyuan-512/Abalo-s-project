"""Stage 1 isolated discernment experiment.

This module does not cast or interpret a chart and is not connected to any
production route.  Its only purpose is to test whether a user-grounded,
explicitly confirmable decision-bottleneck hypothesis improves question
clarification over the frozen V1 baseline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
from collections.abc import Callable
from typing import Any, Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "GUANXIANG_DISCERNMENT_EXPERIMENT_V1"
DEFAULT_MODEL = "gpt-5.6-luna"
MAX_TURNS = 8
MAX_TRANSCRIPT_CHARS = 7_200
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_QUESTION_CUE_PATTERN = re.compile(
    r"(吗|么|什么|为何|为什么|如何|怎样|怎么|是否|能否|可否|该不该|要不要|"
    r"会不会|值不值得|应该|还是|哪(?:个|些|一|里|方面)?|何时|什么时候|多久|多少|"
    r"走向|趋势|可能性|作用|影响|结果|前景|方向)"
)
_CONFIRMATION_QUESTION_PATTERN = re.compile(r"(对吗|准确吗|符合.*吗|如果不对|如果不准确|请纠正)")
_POSITIVE_CONFIRMATION_PATTERN = re.compile(r"(是的|对|准确|没错|基本符合|基本准确|就是这个意思)")
_CORRECTION_PATTERN = re.compile(r"(不对|不准确|不是|更准确|应该是|真正卡住|真正纠结)")


class Stage1ExperimentError(RuntimeError):
    """Experiment boundary failure; callers must record it rather than silently recover."""


class ExperimentTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=280)
    answer: str = Field(min_length=1, max_length=1_200)


class Stage1ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: Literal[CONTRACT_VERSION]
    session_id: str = Field(min_length=1, max_length=80)
    question_text: str = Field(min_length=6, max_length=240)
    turns: list[ExperimentTurn] = Field(default_factory=list, max_length=MAX_TURNS)
    locale: Literal["zh-CN"] = "zh-CN"

    @model_validator(mode="after")
    def validate_request(self) -> "Stage1ExperimentRequest":
        if not _SESSION_ID_PATTERN.fullmatch(self.session_id):
            raise ValueError("invalid session_id")
        self.question_text = unicodedata.normalize("NFC", self.question_text).strip()
        total = len(self.question_text) + sum(len(turn.question) + len(turn.answer) for turn in self.turns)
        if total > MAX_TRANSCRIPT_CHARS:
            raise ValueError("intake transcript is too large")
        return self


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: Literal["QUESTION_TEXT", "TURN_ANSWER"]
    turn_index: int | None = Field(default=None, ge=0, le=MAX_TURNS - 1)
    quote: str = Field(min_length=1, max_length=220)

    @model_validator(mode="after")
    def validate_source_shape(self) -> "EvidenceRef":
        if self.source == "QUESTION_TEXT" and self.turn_index is not None:
            raise ValueError("QUESTION_TEXT evidence cannot include turn_index")
        if self.source == "TURN_ANSWER" and self.turn_index is None:
            raise ValueError("TURN_ANSWER evidence requires turn_index")
        return self


class BottleneckHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str = Field(min_length=12, max_length=260)
    why_decision_is_stuck: str = Field(min_length=8, max_length=220)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)
    uncertainty_note: str = Field(min_length=4, max_length=160)


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    state: Literal["NOT_REQUESTED", "AWAITING", "CONFIRMED", "CORRECTED", "REJECTED"]
    user_quote: str | None = Field(default=None, max_length=240)
    corrected_statement: str | None = Field(default=None, max_length=260)

    @model_validator(mode="after")
    def validate_confirmation(self) -> "Confirmation":
        if self.state in {"CONFIRMED", "CORRECTED", "REJECTED"} and not self.user_quote:
            raise ValueError("resolved confirmation requires user_quote")
        if self.state == "CORRECTED" and not self.corrected_statement:
            raise ValueError("corrected confirmation requires corrected_statement")
        if self.state != "CORRECTED" and self.corrected_statement is not None:
            raise ValueError("only corrected confirmation may include corrected_statement")
        if self.state in {"NOT_REQUESTED", "AWAITING"} and self.user_quote is not None:
            raise ValueError("unresolved confirmation cannot include user_quote")
        return self


class QuestionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=6, max_length=160)
    focus_type: Literal["CORE_DECISION", "BLOCKING_TENSION", "TRADEOFF"]
    what_it_tests: str = Field(min_length=8, max_length=180)
    why_this_question: str = Field(min_length=8, max_length=220)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)


class Stage1ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["ASK", "CONFIRM", "COMPLETE"]
    assistant_message: str = Field(min_length=1, max_length=320)
    next_question: str | None = Field(default=None, max_length=240)
    hypothesis: BottleneckHypothesis | None = None
    confirmation: Confirmation
    unconfirmed_assumptions: list[str] = Field(default_factory=list, max_length=4)
    candidates: list[QuestionCandidate] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def validate_state_machine(self) -> "Stage1ModelOutput":
        if self.status == "ASK":
            if not self.next_question or self.candidates:
                raise ValueError("ASK requires next_question and forbids candidates")
            if self.confirmation.state not in {"NOT_REQUESTED", "REJECTED"}:
                raise ValueError("ASK confirmation state must be NOT_REQUESTED or REJECTED")
        elif self.status == "CONFIRM":
            if not self.next_question or self.hypothesis is None or self.candidates:
                raise ValueError("CONFIRM requires hypothesis and next_question and forbids candidates")
            if self.confirmation.state != "AWAITING":
                raise ValueError("CONFIRM requires AWAITING confirmation")
            if not _CONFIRMATION_QUESTION_PATTERN.search(self.next_question):
                raise ValueError("CONFIRM next_question must invite confirmation and correction")
        else:
            if self.next_question is not None or self.hypothesis is None:
                raise ValueError("COMPLETE requires hypothesis and forbids next_question")
            if self.confirmation.state not in {"CONFIRMED", "CORRECTED"}:
                raise ValueError("COMPLETE requires confirmed or corrected hypothesis")
            if not 1 <= len(self.candidates) <= 2:
                raise ValueError("COMPLETE requires one or two candidates")
            if self.unconfirmed_assumptions:
                raise ValueError("COMPLETE cannot retain unconfirmed assumptions")
        return self


class GenerationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int = Field(ge=0)


class GenerationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: Stage1ModelOutput
    metrics: GenerationMetrics


class Stage1ExperimentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    session_id: str
    status: Literal["ASK", "CONFIRM", "COMPLETE"]
    assistant_message: str
    next_question: str | None
    hypothesis: BottleneckHypothesis | None
    confirmation: Confirmation
    unconfirmed_assumptions: list[str]
    candidates: list[QuestionCandidate]
    generation_metrics: GenerationMetrics
    boundary_note: str = (
        "本结果仅用于阶段1辨识实验；不解卦、不排盘、不替用户决定，合成确认也不代表真实用户认可。"
    )


class Stage1Provider(Protocol):
    def generate(self, request: Stage1ExperimentRequest) -> GenerationEnvelope: ...


SYSTEM_INSTRUCTIONS = """你是“观象”阶段1的辨识实验引导者。你的目标不是收集完信息，而是帮助用户识别：他为什么现在无法决定。

输出前必须逐项自检状态字段（这是硬约束，不是写作建议）：
- ASK：next_question 必须有值；confirmation.state 只能是 NOT_REQUESTED 或 REJECTED；candidates 必须是 []。
- CONFIRM：hypothesis 和 next_question 都必须有值；confirmation.state 必须是 AWAITING；candidates 必须是 []。
- COMPLETE：next_question 必须是 null；hypothesis 必须有值；confirmation.state 只能是 CONFIRMED 或 CORRECTED；unconfirmed_assumptions 必须是 []；candidates 必须有 1—2 个。
- 不得把前一状态遗留的 unconfirmed_assumptions 带进 COMPLETE；用户刚刚确认或纠正后，应据此清空该字段。

严格状态顺序：
1. ASK：信息不足以形成决策瓶颈假设时，一次只问一个最能改变判断的问题。不得输出候选卦题。
2. CONFIRM：形成一个 decision bottleneck hypothesis 后，必须明确说这是“我的理解”，并问用户是否准确；同时邀请用户直接说“这个理解不对”并纠正。不得输出候选卦题。
3. COMPLETE：只有上一轮问题正在确认瓶颈，且用户刚刚明确确认或纠正后才可完成。完成时输出 1 个或最多 2 个候选卦题；不要为了数量强凑两个。

必须遵守：
- hypothesis 必须说明“为什么现在无法决定”，不能只是事实摘要或条件清单。
- hypothesis.evidence_refs 与 candidate.evidence_refs 必须逐条引用用户原问题或某一轮回答中的连续原文；source 和 turn_index 必须准确，禁止跨轮拼接。
- turn_index 一律从 0 开始：第一轮回答是 0，第二轮回答是 1，以此类推。quote 必须从对应文本逐字复制连续片段，不得改写、补词或合并两轮内容。
- 模型归纳只能写成假设，不能升级为用户事实。存在关键未确认假设时不得 COMPLETE。
- 用户否认后不得维护旧假设；必须依据纠正原话重建 hypothesis，并将 confirmation.state 设为 CORRECTED。
- 两个候选的 focus_type 必须不同，并检验不同决策矛盾；不得只是同义改写。
- 候选必须是自然、可直接默念的中文问句，以问号结尾，回答用户原始决策；不能是待办清单、祈使句或已经替用户作出的结论。
- 只使用用户提供的时间范围，不生成日期。
- 不占卜、不解卦、不索取起卦数字，不接触确定性排盘，不输出吉凶。
- 不补写现实事实，不读第三方内心，不替用户决定。
- 使用简短、自然、口语化的中文，避免“机制、闭环、抓手、回调、阶段复盘”等管理术语，除非用户自己使用且确有必要。
- 通常在 2–4 条有效回答后形成 CONFIRM；没有用户确认时，无论轮数多少都不得自动完成。

候选焦点：
- CORE_DECISION：直接检验用户最核心的选择。
- BLOCKING_TENSION：检验造成无法决定的关键拉扯或阻碍。
- TRADEOFF：检验两种代价或价值之间的取舍。
"""
SYSTEM_INSTRUCTIONS_SHA256 = hashlib.sha256(SYSTEM_INSTRUCTIONS.encode("utf-8")).hexdigest()


class OpenAIStage1Provider:
    """Stateless structured-output provider used only by the isolated experiment runner."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        client_factory: Callable[..., Any] = OpenAI,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.model = model
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds

    def generate(self, request: Stage1ExperimentRequest) -> GenerationEnvelope:
        if not os.getenv("OPENAI_API_KEY"):
            raise Stage1ExperimentError("OPENAI_API_KEY is unavailable")
        client = self._client_factory(timeout=self._timeout_seconds, max_retries=0)
        evidence_catalog = [
            {
                "source": "QUESTION_TEXT",
                "turn_index": None,
                "text": request.question_text,
            }
        ] + [
            {
                "source": "TURN_ANSWER",
                "turn_index": index,
                "text": turn.answer,
            }
            for index, turn in enumerate(request.turns)
        ]
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
                                "turn_index_rule": "turn_index is zero-based; copy quote verbatim from exactly one declared source",
                                "evidence_catalog": evidence_catalog,
                                "request": request.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                text_format=Stage1ModelOutput,
                reasoning={"effort": "medium"},
                store=False,
                tools=[],
                max_output_tokens=2_400,
            )
        except Exception as exc:  # pragma: no cover - SDK boundary is tested with fakes
            raise Stage1ExperimentError("stage1 model request failed") from exc
        latency_ms = round((time.perf_counter() - started) * 1000)
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise Stage1ExperimentError("stage1 structured output is missing")
        usage = getattr(response, "usage", None)
        metrics = GenerationMetrics(
            model=self.model,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            latency_ms=latency_ms,
        )
        return GenerationEnvelope(output=parsed, metrics=metrics)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", value)).strip("，。；：！？、,.!?;: ")


def _validate_evidence_ref(reference: EvidenceRef, request: Stage1ExperimentRequest) -> None:
    if reference.source == "QUESTION_TEXT":
        source_text = request.question_text
    else:
        assert reference.turn_index is not None
        if reference.turn_index >= len(request.turns):
            raise Stage1ExperimentError("evidence turn_index is outside the transcript")
        source_text = request.turns[reference.turn_index].answer
    if _normalized(reference.quote) not in _normalized(source_text):
        raise Stage1ExperimentError("evidence quote is not grounded in its declared source")


def _validate_question(question: str) -> None:
    normalized = unicodedata.normalize("NFC", question).strip()
    if not (
        6 <= len(normalized) <= 160
        and normalized.endswith(("？", "?"))
        and _QUESTION_CUE_PATTERN.search(normalized)
    ):
        raise Stage1ExperimentError("candidate is not a usable interrogative question")


def _validate_confirmation_binding(output: Stage1ModelOutput, request: Stage1ExperimentRequest) -> None:
    if output.status != "COMPLETE":
        return
    if not request.turns:
        raise Stage1ExperimentError("COMPLETE requires a confirmation turn")
    latest = request.turns[-1]
    if not _CONFIRMATION_QUESTION_PATTERN.search(latest.question):
        raise Stage1ExperimentError("COMPLETE is not bound to a prior confirmation question")
    user_quote = output.confirmation.user_quote or ""
    if _normalized(user_quote) not in _normalized(latest.answer):
        raise Stage1ExperimentError("confirmation quote is not grounded in the latest answer")
    if output.confirmation.state == "CONFIRMED" and not _POSITIVE_CONFIRMATION_PATTERN.search(user_quote):
        raise Stage1ExperimentError("CONFIRMED state lacks an explicit positive user cue")
    if output.confirmation.state == "CORRECTED":
        if not _CORRECTION_PATTERN.search(user_quote):
            raise Stage1ExperimentError("CORRECTED state lacks an explicit correction cue")
        latest_index = len(request.turns) - 1
        if output.hypothesis is None or not any(
            ref.source == "TURN_ANSWER" and ref.turn_index == latest_index
            for ref in output.hypothesis.evidence_refs
        ):
            raise Stage1ExperimentError("corrected hypothesis must cite the latest correction answer")


def process_stage1_experiment_request(
    payload: object,
    *,
    provider: Stage1Provider | None = None,
) -> dict[str, Any]:
    """Validate one experimental turn with strict grounding and confirmation gates."""
    try:
        request = Stage1ExperimentRequest.model_validate(payload)
    except Exception as exc:
        raise ValueError("invalid stage1 experiment request") from exc

    selected_provider = provider or OpenAIStage1Provider(
        model=os.getenv("ABALO_STAGE1_DISCERNMENT_MODEL", DEFAULT_MODEL)
    )
    envelope = selected_provider.generate(request)
    output = envelope.output

    # A COMPLETE response must first prove that the latest turn was an explicit
    # confirmation/correction exchange.  Validate that state transition before
    # inspecting downstream evidence so an unconfirmed completion cannot be
    # obscured by a secondary citation error.
    _validate_confirmation_binding(output, request)

    if output.hypothesis is not None:
        for reference in output.hypothesis.evidence_refs:
            _validate_evidence_ref(reference, request)
    for candidate in output.candidates:
        _validate_question(candidate.question)
        for reference in candidate.evidence_refs:
            _validate_evidence_ref(reference, request)

    if len(output.candidates) == 2:
        first, second = output.candidates
        if _normalized(first.question) == _normalized(second.question):
            raise Stage1ExperimentError("candidate questions must not be duplicates")
        if first.focus_type == second.focus_type:
            raise Stage1ExperimentError("two candidates must test different decision focuses")

    return Stage1ExperimentResponse(
        session_id=request.session_id,
        status=output.status,
        assistant_message=output.assistant_message,
        next_question=output.next_question,
        hypothesis=output.hypothesis,
        confirmation=output.confirmation,
        unconfirmed_assumptions=output.unconfirmed_assumptions,
        candidates=output.candidates,
        generation_metrics=envelope.metrics,
    ).model_dump(mode="json")
