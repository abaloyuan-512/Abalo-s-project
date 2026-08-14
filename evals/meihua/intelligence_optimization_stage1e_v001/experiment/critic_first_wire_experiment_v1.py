"""Stage 1E flat wire schemas and critic-first arbitration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, TypeVar

from openai import OpenAI
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    DEFAULT_MODEL,
    BottleneckHypothesis,
    EvidenceRef,
    GenerationMetrics,
    _validate_question,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    DecisionAxis,
    Stage1BExperimentRequest,
    StatedPremise,
)
from evals.meihua.intelligence_optimization_stage1d_v001.experiment.critic_first_experiment_v1 import (
    AgencyAndAuthority,
    AskOneReview,
    DecisionFrame,
    FrameProposal,
    GroundedValue,
    MotiveAndFearedCost,
    NotRelevantValue,
    ReadyReview,
    UnknownValue,
    _frame_refs,
    _validate_proposal,
    _validate_review,
)

CONTRACT_VERSION = "GUANXIANG_CRITIC_FIRST_WIRE_EXPERIMENT_V1"
MAX_CALLS_PER_ARBITRATION = 2
FORBIDDEN_SCHEMA_KEYS = {
    "oneOf",
    "discriminator",
    "allOf",
    "not",
    "dependentRequired",
    "dependentSchemas",
    "if",
    "then",
    "else",
}
_INDUCING_PATTERN = re.compile(
    r"(是不是因为|是否因为|你是不是其实|难道不是|其实你是|你真正害怕的是)"
)


class Stage1EError(RuntimeError):
    """Stage 1E contract or orchestration failure."""


class Stage1ERequest(Stage1BExperimentRequest):
    contract_version: Literal[CONTRACT_VERSION]


Dimension = Literal[
    "DECISION_AXIS",
    "STATED_PREMISE",
    "AGENCY_AUTHORITY",
    "MOTIVE_COST",
]


class CriticWireOutput(BaseModel):
    """Single-object API DTO; branch exclusivity is enforced after parsing."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Literal["ASK_ONE", "READY"]
    dimension: Dimension | None
    definition_a: str | None = Field(min_length=4, max_length=220)
    definition_b: str | None = Field(min_length=4, max_length=220)
    why_answers_create_different_questions: str | None = Field(min_length=6, max_length=260)
    question: str | None = Field(min_length=4, max_length=220)
    resolved_problem_definition: str | None = Field(min_length=6, max_length=260)
    ready_reason: str | None = Field(min_length=6, max_length=260)
    non_blocking_unknowns: list[str] = Field(max_length=2)
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_branch(self) -> "CriticWireOutput":
        ask_values = (
            self.dimension,
            self.definition_a,
            self.definition_b,
            self.why_answers_create_different_questions,
            self.question,
        )
        if self.verdict == "ASK_ONE":
            if any(value is None for value in ask_values):
                raise ValueError("ASK_ONE requires all ASK fields")
            if self.resolved_problem_definition is not None or self.ready_reason is not None:
                raise ValueError("ASK_ONE cannot carry READY fields")
            if self.non_blocking_unknowns:
                raise ValueError("ASK_ONE cannot carry non-blocking unknowns")
        else:
            if any(value is not None for value in ask_values):
                raise ValueError("READY cannot carry ASK fields")
            if self.resolved_problem_definition is None or self.ready_reason is None:
                raise ValueError("READY requires resolved definition and reason")
        return self

    def to_internal(self) -> AskOneReview | ReadyReview:
        if self.verdict == "ASK_ONE":
            return AskOneReview(
                verdict="ASK_ONE",
                dimension=self.dimension,
                definition_a=self.definition_a,
                definition_b=self.definition_b,
                why_answers_create_different_questions=self.why_answers_create_different_questions,
                question=self.question,
                evidence_refs=self.evidence_refs,
            )
        return ReadyReview(
            verdict="READY",
            resolved_problem_definition=self.resolved_problem_definition,
            ready_reason=self.ready_reason,
            non_blocking_unknowns=self.non_blocking_unknowns,
            evidence_refs=self.evidence_refs,
        )


class FrameValueWire(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["GROUNDED", "UNKNOWN", "NOT_RELEVANT"]
    value: str | None = Field(min_length=1, max_length=180)
    evidence_refs: list[EvidenceRef] = Field(max_length=4)

    @model_validator(mode="after")
    def validate_status(self) -> "FrameValueWire":
        if self.status == "GROUNDED":
            if self.value is None or not self.evidence_refs:
                raise ValueError("GROUNDED requires value and evidence")
        elif self.value is not None or self.evidence_refs:
            raise ValueError("UNKNOWN/NOT_RELEVANT require null value and empty evidence")
        return self

    def to_internal(self) -> GroundedValue | UnknownValue | NotRelevantValue:
        if self.status == "GROUNDED":
            return GroundedValue(
                status="GROUNDED", value=self.value, evidence_refs=self.evidence_refs
            )
        if self.status == "UNKNOWN":
            return UnknownValue(status="UNKNOWN")
        return NotRelevantValue(status="NOT_RELEVANT")


class AgencyAndAuthorityWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initiator: FrameValueWire
    authorizer: FrameValueWire
    decision_owner: FrameValueWire
    action_owner: FrameValueWire


class MotiveAndFearedCostWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_outcome: FrameValueWire
    feared_cost: FrameValueWire


class DecisionFrameWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_axes: list[DecisionAxis] = Field(min_length=1, max_length=2)
    stated_premises: list[StatedPremise] = Field(max_length=5)
    agency_and_authority: AgencyAndAuthorityWire
    motive_and_feared_cost: MotiveAndFearedCostWire
    highest_value_unknown: None

    def to_internal(self) -> DecisionFrame:
        agency = self.agency_and_authority
        motive = self.motive_and_feared_cost
        return DecisionFrame(
            decision_axes=self.decision_axes,
            stated_premises=self.stated_premises,
            agency_and_authority=AgencyAndAuthority(
                initiator=agency.initiator.to_internal(),
                authorizer=agency.authorizer.to_internal(),
                decision_owner=agency.decision_owner.to_internal(),
                action_owner=agency.action_owner.to_internal(),
            ),
            motive_and_feared_cost=MotiveAndFearedCost(
                desired_outcome=motive.desired_outcome.to_internal(),
                feared_cost=motive.feared_cost.to_internal(),
            ),
            highest_value_unknown=None,
        )


class FrameProposalWire(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frame: DecisionFrameWire
    candidate_hypothesis: BottleneckHypothesis
    proposal_note: str = Field(min_length=4, max_length=220)

    def to_internal(self) -> FrameProposal:
        return FrameProposal(
            frame=self.frame.to_internal(),
            candidate_hypothesis=self.candidate_hypothesis,
            proposal_note=self.proposal_note,
        )


def _walk_schema(node: Any, path: str = "$") -> None:
    if isinstance(node, dict):
        forbidden = FORBIDDEN_SCHEMA_KEYS & set(node)
        if forbidden:
            raise Stage1EError(f"forbidden schema keys at {path}: {sorted(forbidden)}")
        if node.get("type") == "object":
            properties = node.get("properties")
            required = node.get("required")
            if not isinstance(properties, dict):
                raise Stage1EError(f"object missing properties at {path}")
            if node.get("additionalProperties") is not False:
                raise Stage1EError(f"object must forbid extra fields at {path}")
            if set(required or []) != set(properties):
                raise Stage1EError(f"all object properties must be required at {path}")
        for key, value in node.items():
            _walk_schema(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_schema(value, f"{path}[{index}]")


def _wire_text_format(model: type[BaseModel]) -> dict[str, Any]:
    text_format = type_to_text_format_param(model)
    if text_format.get("type") != "json_schema":
        raise Stage1EError("wire text format must use json_schema")
    if text_format.get("strict") is not True:
        raise Stage1EError("wire text format must enable strict mode")
    if not str(text_format.get("name") or "").strip():
        raise Stage1EError("wire text format requires a non-empty schema name")
    schema = text_format["schema"]
    if schema.get("type") != "object":
        raise Stage1EError("wire schema root must be object")
    if "anyOf" in schema:
        raise Stage1EError("wire schema root cannot use anyOf")
    _walk_schema(schema)
    return text_format


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


CRITIC_TEXT_FORMAT = _wire_text_format(CriticWireOutput)
PROPOSER_TEXT_FORMAT = _wire_text_format(FrameProposalWire)
CRITIC_WIRE_SCHEMA_SHA256 = _canonical_sha(CRITIC_TEXT_FORMAT["schema"])
PROPOSER_WIRE_SCHEMA_SHA256 = _canonical_sha(PROPOSER_TEXT_FORMAT["schema"])


CRITIC_INSTRUCTIONS = """你是观象阶段1E的独立问题定义就绪审查器。你只读取用户原问题和用户回答；你看不到、也不得假设任何Proposer答案、案例标签、标准答案或后续答案。

你只判断：现在是否仍存在两种都合理、但会产生实质不同卜题的问题定义。

按以下顺序审查：
1. 尊重用户明确给定的情境前提，不得用风险猜测替换前提。
2. 拆分复合行动表达中的“是否做”与“怎么做”，以及速度、时机、公开范围、规模等不同语义成分；不得静默合并。
3. 核对发起者、授权者、决定者和执行者；主动意愿不等于已获授权。
4. 核对动机、希望得到的结果和担心承担的代价；只有它们会改变真正判断对象时才阻断。
5. 只有缺口会改变卜题对象、选择轴、固定前提、决定主体或核心取舍时，才能ASK_ONE。

非阻断规则：更多数据、沟通渠道、执行步骤、普通次数或持续时长默认只是执行细节；除非用户明确把该参数本身设为决策对象，否则不得因此追问。问题中的时间范围是观察/决策窗口，不自动代表持续行动频率。

若存在kind=CRITICAL_ANSWER的最新回答，该回答优先于原问题的宽泛措辞。你只能判断首次关键缺口是否已解决，不得转而寻找新的、次优的或执行层缺口。

所有wire字段必须输出。ASK_ONE时填写dimension、两种定义、差异原因、一个问题；READY字段必须为null且non_blocking_unknowns为空。READY时ASK字段和dimension必须为null，填写resolved_problem_definition与ready_reason。

不得生成瓶颈、卜题、建议或行动清单；不得心理诊断、读心、预埋答案；不得提出多个问题。quote必须逐字复制，turn_index从0开始。"""


PROPOSER_INSTRUCTIONS = """你是观象阶段1E的瓶颈提议者。独立Critic已经确认问题定义就绪；你只基于用户原问题和回答形成一个可审计决策框架与候选瓶颈。

权限：
- 只能输出frame、candidate_hypothesis、proposal_note。
- 不得提问、不得改变状态、不得重新做就绪审查、不得生成多个候选、不得生成卜题或建议。
- 不得把事实摘要冒充瓶颈。候选瓶颈必须说明：哪个尚未解决的核心取舍或条件使用户无法决定，以及为什么它会改变选择。

所有FrameValue wire对象必须同时输出status、value、evidence_refs：GROUNDED必须填写value与逐字证据；UNKNOWN/NOT_RELEVANT的value必须为null且evidence_refs必须为空数组。frame.highest_value_unknown固定为null。

决策轴、前提、GROUNDED值和候选瓶颈必须引用原问题或单轮回答中的连续原文。turn_index从0开始；不跨轮拼接；不挑战用户明确前提；不补事实、不读心。

边界：不生成日期、不替用户决定、不占卜、不解卦、不排盘、不索取数字、不输出行动清单。"""


CRITIC_PROMPT_SHA256 = hashlib.sha256(CRITIC_INSTRUCTIONS.encode("utf-8")).hexdigest()
PROPOSER_PROMPT_SHA256 = hashlib.sha256(PROPOSER_INSTRUCTIONS.encode("utf-8")).hexdigest()


class ModelCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    role: Literal["CRITIC", "PROPOSER"]
    attempted: bool
    model: str
    prompt_sha256: str
    schema_sha256: str
    input_sha256: str
    started_at: str
    finished_at: str
    latency_ms: int = Field(ge=0)
    response_id: str | None
    request_id: str | None
    http_status: int | None
    api_error_code: str | None
    api_error_param: str | None
    raw_output_text: str | None
    raw_parsed_output: dict[str, Any] | None
    usage: GenerationMetrics | None
    outcome: Literal[
        "SUCCESS",
        "SCHEMA_COMPATIBILITY_ERROR",
        "TRANSPORT_ERROR",
        "WIRE_JSON_PARSE_ERROR",
        "WIRE_VALIDATION_ERROR",
        "SEMANTIC_VALIDATION_ERROR",
        "MISSING_OUTPUT",
    ]
    error_detail: str | None


class CriticAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: CriticWireOutput | None
    record: ModelCallRecord


class ProposerAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: FrameProposalWire | None
    record: ModelCallRecord


class Stage1EResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    session_id: str
    status: Literal[
        "ASK_CRITICAL",
        "CONFIRM",
        "INSUFFICIENT_TO_CONFIRM",
        "REVIEW_ERROR",
        "SCHEMA_COMPATIBILITY_ERROR",
    ]
    assistant_message: str
    next_question: str | None = None
    review: AskOneReview | ReadyReview | None = None
    proposal: FrameProposal | None = None
    hypothesis: BottleneckHypothesis | None = None
    call_records: list[ModelCallRecord] = Field(default_factory=list, max_length=2)
    review_error: str | None = None
    boundary_note: str = "本结果仅用于阶段1E隔离实验；不解卦、不排盘、不替用户决定。"


class CriticProtocol(Protocol):
    def generate(self, request: Stage1ERequest, *, call_sequence: int) -> CriticAttempt: ...


class ProposerProtocol(Protocol):
    def generate(self, request: Stage1ERequest, *, call_sequence: int) -> ProposerAttempt: ...


def _model_input(request: Stage1ERequest) -> dict[str, Any]:
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
        "evidence_catalog": [
            {"source": "QUESTION_TEXT", "turn_index": None, "text": request.question_text}
        ]
        + [
            {
                "source": "TURN_ANSWER",
                "turn_index": index,
                "turn_kind": turn.kind,
                "text": turn.answer,
            }
            for index, turn in enumerate(request.turns)
        ],
    }


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}:{str(exc).replace(chr(10), ' ')[:700]}"


def _usage(response: Any, *, model: str, latency_ms: int) -> GenerationMetrics:
    usage = getattr(response, "usage", None)
    return GenerationMetrics(
        model=model,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        latency_ms=latency_ms,
    )


def _api_error(exc: Exception) -> tuple[int | None, str | None, str | None, dict[str, Any] | None]:
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    param = error.get("param") if isinstance(error, dict) else None
    return status, code, param, body if isinstance(body, dict) else None


WireT = TypeVar("WireT", bound=BaseModel)


def _perform_call(
    *,
    role: Literal["CRITIC", "PROPOSER"],
    model: str,
    prompt: str,
    prompt_sha256: str,
    schema_sha256: str,
    text_format: dict[str, Any],
    wire_model: type[WireT],
    request: Stage1ERequest,
    call_sequence: int,
    client_factory: Callable[..., Any],
    max_output_tokens: int,
) -> tuple[WireT | None, ModelCallRecord]:
    input_payload = _model_input(request)
    input_text = json.dumps(input_payload, ensure_ascii=False)
    input_sha256 = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
    started_dt = datetime.now(UTC)
    started = time.perf_counter()
    response = None
    if not os.getenv("OPENAI_API_KEY"):
        finished = datetime.now(UTC)
        return None, ModelCallRecord(
            sequence=call_sequence,
            role=role,
            attempted=True,
            model=model,
            prompt_sha256=prompt_sha256,
            schema_sha256=schema_sha256,
            input_sha256=input_sha256,
            started_at=started_dt.isoformat(),
            finished_at=finished.isoformat(),
            latency_ms=0,
            response_id=None,
            request_id=None,
            http_status=None,
            api_error_code=None,
            api_error_param=None,
            raw_output_text=None,
            raw_parsed_output=None,
            usage=None,
            outcome="TRANSPORT_ERROR",
            error_detail="Stage1EError:OPENAI_API_KEY is unavailable",
        )
    try:
        client = client_factory(timeout=90.0, max_retries=0)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text},
            ],
            text={"format": text_format},
            reasoning={"effort": "medium"},
            store=False,
            tools=[],
            max_output_tokens=max_output_tokens,
        )
        latency = round((time.perf_counter() - started) * 1000)
        finished = datetime.now(UTC)
        raw_text = getattr(response, "output_text", None)
        usage = _usage(response, model=model, latency_ms=latency)
        base = dict(
            sequence=call_sequence,
            role=role,
            attempted=True,
            model=model,
            prompt_sha256=prompt_sha256,
            schema_sha256=schema_sha256,
            input_sha256=input_sha256,
            started_at=started_dt.isoformat(),
            finished_at=finished.isoformat(),
            latency_ms=latency,
            response_id=getattr(response, "id", None),
            request_id=getattr(response, "_request_id", None),
            http_status=200,
            api_error_code=None,
            api_error_param=None,
            raw_output_text=raw_text,
            usage=usage,
        )
        if not raw_text:
            return None, ModelCallRecord(
                **base,
                raw_parsed_output=None,
                outcome="MISSING_OUTPUT",
                error_detail="response.output_text is missing",
            )
        try:
            raw_json = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return None, ModelCallRecord(
                **base,
                raw_parsed_output=None,
                outcome="WIRE_JSON_PARSE_ERROR",
                error_detail=_safe_error(exc),
            )
        if not isinstance(raw_json, dict):
            raw_json = {"_non_object_json": raw_json}
        try:
            output = wire_model.model_validate(raw_json)
        except ValidationError as exc:
            return None, ModelCallRecord(
                **base,
                raw_parsed_output=raw_json,
                outcome="WIRE_VALIDATION_ERROR",
                error_detail=_safe_error(exc),
            )
        return output, ModelCallRecord(
            **base,
            raw_parsed_output=raw_json,
            outcome="SUCCESS",
            error_detail=None,
        )
    except Exception as exc:  # pragma: no cover - real SDK/network errors
        latency = round((time.perf_counter() - started) * 1000)
        finished = datetime.now(UTC)
        status, code, param, body = _api_error(exc)
        schema_error = code == "invalid_json_schema" or param == "text.format.schema"
        return None, ModelCallRecord(
            sequence=call_sequence,
            role=role,
            attempted=True,
            model=model,
            prompt_sha256=prompt_sha256,
            schema_sha256=schema_sha256,
            input_sha256=input_sha256,
            started_at=started_dt.isoformat(),
            finished_at=finished.isoformat(),
            latency_ms=latency,
            response_id=getattr(response, "id", None),
            request_id=getattr(exc, "request_id", None),
            http_status=status,
            api_error_code=code,
            api_error_param=param,
            raw_output_text=json.dumps(body, ensure_ascii=False) if body else None,
            raw_parsed_output=body,
            usage=None,
            outcome="SCHEMA_COMPATIBILITY_ERROR" if schema_error else "TRANSPORT_ERROR",
            error_detail=_safe_error(exc),
        )


class OpenAICritic:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1ERequest, *, call_sequence: int) -> CriticAttempt:
        output, record = _perform_call(
            role="CRITIC",
            model=self.model,
            prompt=CRITIC_INSTRUCTIONS,
            prompt_sha256=CRITIC_PROMPT_SHA256,
            schema_sha256=CRITIC_WIRE_SCHEMA_SHA256,
            text_format=CRITIC_TEXT_FORMAT,
            wire_model=CriticWireOutput,
            request=request,
            call_sequence=call_sequence,
            client_factory=self._client_factory,
            max_output_tokens=2_000,
        )
        return CriticAttempt(output=output, record=record)


class OpenAIProposer:
    def __init__(self, *, model=DEFAULT_MODEL, client_factory: Callable[..., Any] = OpenAI):
        self.model = model
        self._client_factory = client_factory

    def generate(self, request: Stage1ERequest, *, call_sequence: int) -> ProposerAttempt:
        output, record = _perform_call(
            role="PROPOSER",
            model=self.model,
            prompt=PROPOSER_INSTRUCTIONS,
            prompt_sha256=PROPOSER_PROMPT_SHA256,
            schema_sha256=PROPOSER_WIRE_SCHEMA_SHA256,
            text_format=PROPOSER_TEXT_FORMAT,
            wire_model=FrameProposalWire,
            request=request,
            call_sequence=call_sequence,
            client_factory=self._client_factory,
            max_output_tokens=3_200,
        )
        return ProposerAttempt(output=output, record=record)


def is_schema_compatibility_error(record: ModelCallRecord) -> bool:
    return record.outcome == "SCHEMA_COMPATIBILITY_ERROR"


def _critical_answer_index(request: Stage1ERequest) -> int | None:
    indexes = [index for index, turn in enumerate(request.turns) if turn.kind == "CRITICAL_ANSWER"]
    if len(indexes) > 1:
        raise Stage1EError("at most one critical answer is allowed")
    return indexes[0] if indexes else None


def _has_turn_ref(refs: list[EvidenceRef], turn_index: int) -> bool:
    return any(ref.source == "TURN_ANSWER" and ref.turn_index == turn_index for ref in refs)


def _mark_semantic_error(record: ModelCallRecord, exc: Exception) -> None:
    record.outcome = "SEMANTIC_VALIDATION_ERROR"
    record.error_detail = _safe_error(exc)


def arbitrate_stage1e_request(
    payload: object,
    *,
    call_sequence_start: int = 1,
    critic: CriticProtocol | None = None,
    proposer: ProposerProtocol | None = None,
) -> dict[str, Any]:
    try:
        request = Stage1ERequest.model_validate(payload)
        critical_index = _critical_answer_index(request)
    except Exception as exc:
        raise ValueError("invalid stage1e request") from exc
    selected_critic = critic or OpenAICritic(
        model=os.getenv("ABALO_STAGE1E_CRITIC_MODEL", DEFAULT_MODEL)
    )
    selected_proposer = proposer or OpenAIProposer(
        model=os.getenv("ABALO_STAGE1E_PROPOSER_MODEL", DEFAULT_MODEL)
    )
    records: list[ModelCallRecord] = []
    critic_attempt = selected_critic.generate(request, call_sequence=call_sequence_start)
    records.append(critic_attempt.record)
    if critic_attempt.output is None:
        schema_error = is_schema_compatibility_error(critic_attempt.record)
        return Stage1EResponse(
            session_id=request.session_id,
            status="SCHEMA_COMPATIBILITY_ERROR" if schema_error else "REVIEW_ERROR",
            assistant_message="服务端Schema不兼容。" if schema_error else "独立就绪审查失败。",
            call_records=records,
            review_error=f"CRITIC_{critic_attempt.record.outcome}:{critic_attempt.record.error_detail}",
        ).model_dump(mode="json")
    review = critic_attempt.output.to_internal()
    try:
        _validate_review(review, request)
    except Exception as exc:
        _mark_semantic_error(critic_attempt.record, exc)
        return Stage1EResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="独立就绪审查未通过证据验证。",
            review=review,
            call_records=records,
            review_error=f"CRITIC_SEMANTIC_VALIDATION_ERROR:{_safe_error(exc)}",
        ).model_dump(mode="json")
    if isinstance(review, AskOneReview):
        if critical_index is not None:
            return Stage1EResponse(
                session_id=request.session_id,
                status="INSUFFICIENT_TO_CONFIRM",
                assistant_message="唯一关键回答后仍存在定义缺口，本次停止。",
                review=review,
                call_records=records,
            ).model_dump(mode="json")
        return Stage1EResponse(
            session_id=request.session_id,
            status="ASK_CRITICAL",
            assistant_message="形成瓶颈前还需澄清一个会改变卜题定义的问题。",
            next_question=review.question,
            review=review,
            call_records=records,
        ).model_dump(mode="json")
    if critical_index is not None and not _has_turn_ref(review.evidence_refs, critical_index):
        exc = Stage1EError("READY review must cite the critical answer")
        _mark_semantic_error(critic_attempt.record, exc)
        return Stage1EResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="关键回答没有进入就绪判断。",
            review=review,
            call_records=records,
            review_error=f"ARBITER_ERROR:{exc}",
        ).model_dump(mode="json")
    proposer_attempt = selected_proposer.generate(
        request, call_sequence=call_sequence_start + 1
    )
    records.append(proposer_attempt.record)
    if proposer_attempt.output is None:
        schema_error = is_schema_compatibility_error(proposer_attempt.record)
        return Stage1EResponse(
            session_id=request.session_id,
            status="SCHEMA_COMPATIBILITY_ERROR" if schema_error else "REVIEW_ERROR",
            assistant_message="服务端Schema不兼容。" if schema_error else "瓶颈提议失败。",
            review=review,
            call_records=records,
            review_error=f"PROPOSER_{proposer_attempt.record.outcome}:{proposer_attempt.record.error_detail}",
        ).model_dump(mode="json")
    proposal = proposer_attempt.output.to_internal()
    try:
        _validate_proposal(proposal, request)
        if critical_index is not None:
            if not _has_turn_ref(proposal.candidate_hypothesis.evidence_refs, critical_index):
                raise Stage1EError("hypothesis must cite critical answer")
            if not _has_turn_ref(_frame_refs(proposal.frame), critical_index):
                raise Stage1EError("frame must cite critical answer")
    except Exception as exc:
        _mark_semantic_error(proposer_attempt.record, exc)
        return Stage1EResponse(
            session_id=request.session_id,
            status="REVIEW_ERROR",
            assistant_message="瓶颈提议未通过证据验证。",
            review=review,
            proposal=proposal,
            call_records=records,
            review_error=f"PROPOSER_SEMANTIC_VALIDATION_ERROR:{_safe_error(exc)}",
        ).model_dump(mode="json")
    hypothesis = proposal.candidate_hypothesis
    return Stage1EResponse(
        session_id=request.session_id,
        status="CONFIRM",
        assistant_message="问题定义已经收束，可以确认当前瓶颈理解。",
        next_question=f"我的理解是：{hypothesis.statement}。这个理解准确吗？如果不准确，请纠正。",
        review=review,
        proposal=proposal,
        hypothesis=hypothesis,
        call_records=records,
    ).model_dump(mode="json")
