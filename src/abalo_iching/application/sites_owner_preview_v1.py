"""Personalized reading service used by the private formal Guanxiang site."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Callable
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import Field, ValidationError

from abalo_iching.meihua import MeihuaInput, cast_meihua, chart_to_dict
from abalo_iching.personalization_gate2.models import (
    ChartContext,
    ChartEvidence,
    ExperimentArm,
    Gate2PromptPackage,
    Gate2ProviderResult,
    KnowledgeReviewStatus,
    RealityFact,
    SourceKind,
    StrictModel,
    UnknownItem,
)
from abalo_iching.personalization_gate2.live_provider import Gate2LiveProviderError
from abalo_iching.personalization_gate2.pricing import Gate2TokenPricing
from abalo_iching.personalization_gate2.stage_c2_contract import (
    C2_SOURCE_TRACE_INSTRUCTIONS,
    C2_SELF_SERVE_QUALITY_INSTRUCTIONS,
    Gate2ExperimentOutputV3,
    Gate2StageC2Validator,
)
from abalo_iching.personalization_gate2.validators import question_clauses_from_text

from .sites_meihua_service_v3 import (
    CONTRACT_VERSION_V3,
    process_sites_meihua_v3_request,
)
from .interpretation_packet_v1 import (
    InterpretationPacketV1,
    build_interpretation_packet_v1,
    interpretation_packet_evidence_v1,
)
from .sites_page8_reading_v1 import (
    OwnerPreviewExperimentOutputPage8V1,
    build_page8_reading_v1,
)


OWNER_PREVIEW_CONTRACT_VERSION = "SITES_OWNER_PREVIEW_CONTRACT_V1"
OWNER_PREVIEW_PROMPT_VERSION = "guanxiang_owner_preview_v8_page8_model"
OWNER_PREVIEW_VALIDATOR_VERSION = "guanxiang_owner_preview_validator_v7_page8_model"
OWNER_PREVIEW_MODEL = "gpt-5.6-sol"
OWNER_PREVIEW_REASONING_EFFORT = "medium"
OWNER_PREVIEW_MAX_OUTPUT_TOKENS = 9_000
# Keep the backend task alive longer than the browser's ordinary wait window.
# This is a technical lifecycle boundary, not a usage or spending quota.
OWNER_PREVIEW_MAX_POLL_ATTEMPTS = 900
LOGGER = logging.getLogger("abalo.owner_preview")

OWNER_PREVIEW_TRACE_COVERAGE_INSTRUCTIONS = """
所有 judgment_signature 五个字段与 user_facing_reading 五个字段，都必须至少出现在一条 INTERPRETIVE_LINK 的 supports_fields 中：
- judgment_signature.direction
- judgment_signature.method
- judgment_signature.agency
- judgment_signature.main_conflict
- judgment_signature.action_intensity
- user_facing_reading.core_judgment
- user_facing_reading.explanation
- user_facing_reading.reality_application
- user_facing_reading.action
- user_facing_reading.switch_condition
不得只覆盖承载这些内容的中间结构字段。
对于列表整体的来源覆盖，supports_fields 允许使用以下三个精确集合路径：context_facts、chart_signals、switch_conditions；
也可以继续使用 context_facts[0].fact_text、chart_signals[0].signal_text、switch_conditions[0].condition_text 这类带序号路径。
除这三个集合路径外，不得省略列表序号或使用未声明的字段路径。
""".strip()

_OWNER_PREVIEW_AGGREGATE_SUPPORT_FIELDS = {
    "context_facts",
    "chart_signals",
    "switch_conditions",
}

_DOMAIN_LABELS = {
    "WORK_CAREER": "工作或职业",
    "PROJECT_COOPERATION": "项目或合作",
    "RELATIONSHIP_COMMUNICATION": "关系或沟通",
    "PERSONAL_PLANNING": "个人计划",
}
_GOAL_LABELS = {
    "IDENTIFY_OBSTACLES": "识别阻力与支持条件",
    "PLAN_NEXT_STEP": "看清下一步",
    "PREPARE_COMMUNICATION": "准备一次沟通",
    "ADJUST_COMMITMENT_BOUNDARIES": "调整投入与边界",
    "OBSERVE_VERIFY_SIGNALS": "观察和核实现实信号",
}
_HORIZON_LABELS = {
    "CURRENT": "当前阶段",
    "NEXT_30_DAYS": "未来三十天",
    "NEXT_QUARTER": "未来一个季度",
    "NEXT_6_MONTHS": "未来六个月",
}
_STAGE_LABELS = {
    "EXPLORING": "正在了解",
    "PREPARING": "正在准备",
    "ALREADY_ACTING": "已经行动",
    "WAITING_FEEDBACK": "正在等待回应",
}
_UNCERTAINTY_LABELS = {
    "CONDITIONS": "现实条件是否具备",
    "OTHER_RESPONSE": "对方是否回应",
    "OWN_COMMITMENT": "自己是否值得继续投入",
    "TIMING": "时机是否合适",
}
_RISK_PROFILE_LABELS = {
    "STANDARD": "一般，可分阶段调整",
    "HIGH_IRREVERSIBLE": "高不可逆，需要先确认共同意愿、长期责任与专业现实条件",
}


class OwnerPreviewAcknowledgements(StrictModel):
    owner_preview_only: Literal[True]
    live_model_cost_acknowledged: Literal[True]
    no_formal_persistence: Literal[True]
    user_statements_not_verified_facts: Literal[True]


class OwnerPreviewPayload(StrictModel):
    contract_version: Literal[OWNER_PREVIEW_CONTRACT_VERSION]
    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    question_text: str = Field(min_length=6, max_length=160)
    question_domain: str = Field(min_length=1, max_length=80)
    decision_goal: str = Field(min_length=1, max_length=80)
    time_horizon: str = Field(min_length=1, max_length=80)
    decision_stage: str = Field(min_length=1, max_length=80)
    key_uncertainty: str = Field(min_length=1, max_length=80)
    decision_risk_profile: Literal["STANDARD", "HIGH_IRREVERSIBLE"] = "STANDARD"
    confirmed_facts: list[str] = Field(min_length=1, max_length=8)
    unknowns: list[str] = Field(min_length=1, max_length=6)
    options: list[str] = Field(default_factory=list, max_length=4)
    actions_already_taken: list[str] = Field(default_factory=list, max_length=6)
    observable_responses: list[str] = Field(default_factory=list, max_length=6)
    numbers: list[int] = Field(min_length=3, max_length=3)
    locale: Literal["zh-CN"]
    client_timestamp: str = Field(min_length=1, max_length=80)
    user_acknowledgements: OwnerPreviewAcknowledgements


class OwnerPreviewRealityContext(StrictModel):
    data_classification: Literal["OWNER_PROVIDED_PRIVATE_PREVIEW"]
    question_text: str
    question_clauses: list[str] = Field(min_length=1, max_length=12)
    decision_risk_profile: Literal["STANDARD", "HIGH_IRREVERSIBLE"]
    explicit_facts: list[RealityFact]
    unknowns: list[UnknownItem]
    options: list[RealityFact]
    actions_already_taken: list[RealityFact]
    observable_responses: list[RealityFact]

    def reality_facts(self) -> tuple[RealityFact, ...]:
        return tuple(
            self.explicit_facts
            + self.options
            + self.actions_already_taken
            + self.observable_responses
        )

    def reality_refs(self) -> set[str]:
        return {item.ref for item in self.reality_facts()}


OWNER_PREVIEW_SYSTEM_INSTRUCTIONS = """你正在生成观象正式站点的个性化解读；当前站点仍处于所有者私有生产阶段。
只使用输入中列出的用户陈述与程序提供的卦象 Evidence；用户陈述尚未经外部核验，不得把未知信息补写成事实。
不得重新排盘、读心、保证结果、生成输入未提供的具体日期，或提供证券与医疗操作指令。
现实陈述、卦象事实和解释接榫必须分开。解释接榫只能标记为实验性解释假设。
context_facts.fact_text 必须逐字复制其唯一 reality_refs 对应的输入陈述，不得改写或补充。
第一段先给一个明确但不过界的主要判断；说明为什么不是相反姿态，并给出具体对象、动作、可观察结果与转向条件。
必须逐项回答 question_clauses 中的每个子问题，并把这些回答写入 user_facing_reading.question_responses；question_text 必须逐字复制对应子问题。
用户可见回答至少使用两条不同卦象 Evidence，其中至少一条来自变化后体用或动爻，并说明这些卦象事实为何支持该方向。
只能引用输入中提供的 EVxx；所有解释接榫必须同时引用现实陈述与卦象事实。
中文应自然、平实、具体，有少量传统文化气息；避免翻译腔、抽象 AI 句法和万能咨询套话。
user_facing_reading 中不得出现以下会触发质量拦截的原词：最小可逆、低成本验证、收集反馈、保留调整空间、外部支点、进入明处、承接能力、结构性反馈。请直接写具体的人、动作、条件与可观察结果。
必须严格按给定结构化 Schema 输出，不得增加字段。一次生成完成，不请求工具，不联网，不自我修复。"""

OWNER_PREVIEW_JUDGMENT_FIRST_INSTRUCTIONS = """判断优先与解释资料包使用约束：
1. 先对整个问题给出一个明确、有边界的总判断，再按 question_clauses 原顺序逐项回答；缺失信息只能用来限定判断，不能代替判断。
2. 从 interpretation_packet 与 chart_context 中选择最能区分本案的 2 至 3 条 EVxx；必须至少使用 EV10 至 EV13 中的一条，并至少覆盖变卦、变化后体用或动爻中的一项。
3. 解释这些卦象事实为何支持当前方向，并明确说明为什么不是相反方向；不得只罗列卦名、卦辞或爻辞。
4. interpretation_packet 只包含排盘事实与经典原文。把它们应用到用户现实处境时，必须标记为解释假设，并同时引用现实 RWxx 与卦象 EVxx。
5. 行动建议必须是前述判断的直接落实，写清对象、动作、可观察结果和转向条件；不得用通用咨询套话填充篇幅。
6. 经典原文不得被表述为对现实结果的保证，也不得据此虚构第三方动机、未提供的日期或未核实事实。""".strip()

OWNER_PREVIEW_REFERENCE_CLOSURE_INSTRUCTIONS = """来源追踪闭合检查（输出前必须逐项执行）：
1. 先汇总输出所有字段中实际使用的 RWxx 与 EVxx，包括 context_facts、chart_signals、各 evidence_refs/reality_refs 和 source_trace 的解释接榫。
2. 每一个实际使用的 RWxx，必须在 source_trace 中恰好有一条 source_kind=REALITY_FACT 且 source_ref 与 trace_id 都等于该 RWxx 的事实追踪行。
3. 每一个实际使用的 EVxx，必须在 source_trace 中恰好有一条 source_kind=CHART_FACT 且 source_ref 与 trace_id 都等于该 EVxx 的事实追踪行；即使该 EVxx 只出现在 chart_signals 或某个 evidence_refs 中，也不能省略。
4. 先为选中的每条卦象证据创建 CHART_FACT 追踪行，再创建 INTERPRETIVE_LINK；不得用 INTERPRETIVE_LINK 代替事实追踪行，不得创建输入未提供的引用。
5. 提交前再次比较“全部实际引用集合”和“事实追踪行集合”，两者必须完全闭合。""".strip()

OWNER_PREVIEW_PAGE8_INSTRUCTIONS = """第八页“读卦”分层输出约束：
1. layered_reading 必须严格输出五项，顺序固定为 BASE_HEXAGRAM、MUTUAL_HEXAGRAM、CHANGED_HEXAGRAM、MOVING_LINE、BODY_USE_STRENGTH。
2. 五项分别回答本卦看眼下结构、互卦看内部发展、变卦看变化后结构方向、动爻看变化位置与阶段、体用旺衰看双方关系与当前余力。
3. 每项只写“本层读到什么、怎样连接用户明确提供的现实、仍不能据此断定什么”；不得写下一步行动、可借之力、当慎之处、何时转向或最终核心判断，这些全部留给第九页。
4. reality_connection 必须具体承接输入中的 RWxx，不得虚构第三方动机、结果、日期或用户未提供的事实。
5. uncertainty_boundary 必须明确本层不能证明的现实结论，不能用模糊免责声明代替具体边界。
6. 每项必须同时引用至少一条 RWxx 与指定 EVxx，并标记 interpretation_hypothesis=true：本卦必须含 EV10；互卦必须含 EV11；变卦必须含 EV12；动爻必须含 EV13；体用旺衰必须同时含 EV02、EV03、EV06。
7. layered_reading 自带 reality_refs 与 evidence_refs，由第八页专用验证器检查；不要把 layered_reading 字段加入 source_trace.supports_fields。
8. 每项保持精炼：layer_summary 一至两句，reality_connection 两至四句，uncertainty_boundary 一至两句。""".strip()


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _nonempty_lines(values: list[str]) -> list[str]:
    normalized = [value.strip() for value in values]
    if any(not value or len(value) > 400 for value in normalized):
        raise ValueError("事实与未知项必须是1至400字的非空文字。")
    return normalized


def _reality(payload: OwnerPreviewPayload) -> OwnerPreviewRealityContext:
    confirmed = _nonempty_lines(payload.confirmed_facts)
    unknowns = _nonempty_lines(payload.unknowns)
    options = _nonempty_lines(payload.options)
    actions = _nonempty_lines(payload.actions_already_taken)
    responses = _nonempty_lines(payload.observable_responses)
    facts = [
        f"用户本次所问：{payload.question_text.strip()}",
        f"用户选择的事情范围：{_DOMAIN_LABELS.get(payload.question_domain, payload.question_domain)}。",
        f"用户这次最想看清：{_GOAL_LABELS.get(payload.decision_goal, payload.decision_goal)}。",
        f"用户选择的观察范围：{_HORIZON_LABELS.get(payload.time_horizon, payload.time_horizon)}。",
        f"用户说明事情阶段：{_STAGE_LABELS.get(payload.decision_stage, payload.decision_stage)}。",
        f"用户最需要确认的变量：{_UNCERTAINTY_LABELS.get(payload.key_uncertainty, payload.key_uncertainty)}。",
        f"用户选择的决定风险：{_RISK_PROFILE_LABELS[payload.decision_risk_profile]}。",
        *confirmed,
    ]
    next_ref = 1

    def referenced(items: list[str]) -> list[RealityFact]:
        nonlocal next_ref
        result: list[RealityFact] = []
        for item in items:
            result.append(RealityFact(ref=f"RW{next_ref:02d}", text=item))
            next_ref += 1
        return result

    return OwnerPreviewRealityContext(
        data_classification="OWNER_PROVIDED_PRIVATE_PREVIEW",
        question_text=payload.question_text.strip(),
        question_clauses=question_clauses_from_text(payload.question_text.strip()),
        decision_risk_profile=payload.decision_risk_profile,
        explicit_facts=referenced(facts),
        unknowns=[UnknownItem(text=item) for item in unknowns],
        options=referenced(options),
        actions_already_taken=referenced(actions),
        observable_responses=referenced(responses),
    )


def _chart_context(
    payload: OwnerPreviewPayload,
    generated_at: datetime,
) -> tuple[ChartContext, InterpretationPacketV1]:
    chart = cast_meihua(
        MeihuaInput(
            *payload.numbers,
            generated_at,
            "Asia/Shanghai",
            payload.request_id,
        )
    )
    chart_bytes = _canonical_json(chart_to_dict(chart)).encode("utf-8")
    evidence = [
        ChartEvidence(
            ref=f"EV{index:02d}",
            canonical_evidence_id=f"{chart.versions.rule_version}:{item.evidence_id}",
            text=item.fact,
            knowledge_review_status=KnowledgeReviewStatus.CANONICAL_ONLY,
        )
        for index, item in enumerate(chart.evidence, start=1)
    ]
    packet = build_interpretation_packet_v1(chart)
    evidence.extend(interpretation_packet_evidence_v1(packet))
    return (
        ChartContext(
            chart_mapping_id=f"CHART-{hashlib.sha256(chart_bytes).hexdigest()[:20]}",
            is_mismatched_control=False,
            evidence=evidence,
        ),
        packet,
    )


def _prompt(
    reality: OwnerPreviewRealityContext,
    chart_context: ChartContext,
    interpretation_packet: InterpretationPacketV1,
) -> Gate2PromptPackage:
    payload = {
        "preview_constraints": {
            "access": "OWNER_ONLY_PRIVATE_PREVIEW",
            "user_statements_are_unverified": True,
            "question_text_used_for_calculation": False,
            "question_text_used_for_interpretation": True,
            "store": False,
            "tools": [],
            "single_generation_only": True,
            "automatic_model_repair": False,
            "interpretation_is_hypothesis": True,
            "formal_persistence_allowed": False,
        },
        "reality_context": reality.model_dump(mode="json"),
        "chart_context": {
            "chart_mapping_id": chart_context.chart_mapping_id,
            "is_mismatched_control": False,
            "evidence": [
                {
                    "ref": item.ref,
                    "text": item.text,
                    "knowledge_review_status": item.knowledge_review_status.value,
                }
                for item in chart_context.evidence
            ],
        },
        "interpretation_packet": interpretation_packet.model_dump(mode="json"),
        "allowed_reality_refs": sorted(reality.reality_refs()),
        "allowed_evidence_refs": sorted(chart_context.evidence_refs()),
        "question_clauses": reality.question_clauses,
        "output_schema": OwnerPreviewExperimentOutputPage8V1.model_json_schema(),
    }
    instructions = (
        f"{OWNER_PREVIEW_SYSTEM_INSTRUCTIONS}\n\n"
        f"{C2_SOURCE_TRACE_INSTRUCTIONS}\n\n"
        f"{OWNER_PREVIEW_TRACE_COVERAGE_INSTRUCTIONS}\n\n"
        f"{C2_SELF_SERVE_QUALITY_INSTRUCTIONS}\n\n"
        f"{OWNER_PREVIEW_JUDGMENT_FIRST_INSTRUCTIONS}\n\n"
        f"{OWNER_PREVIEW_REFERENCE_CLOSURE_INSTRUCTIONS}\n\n"
        f"{OWNER_PREVIEW_PAGE8_INSTRUCTIONS}"
    )
    digest = hashlib.sha256(
        f"{instructions}\n{_canonical_json(payload)}".encode("utf-8")
    ).hexdigest()
    return Gate2PromptPackage(
        prompt_version=OWNER_PREVIEW_PROMPT_VERSION,
        system_instructions=instructions,
        input_payload=payload,
        prompt_sha256=digest,
    )


def _validate_output(
    reality: OwnerPreviewRealityContext,
    chart_context: ChartContext,
    output: Gate2ExperimentOutputV3,
) -> tuple[list[str], list[str]]:
    request_view = SimpleNamespace(
        metadata=SimpleNamespace(arm=ExperimentArm.C),
        reality=reality,
        chart_context=chart_context,
    )
    report = Gate2StageC2Validator().validate(request_view, output)  # type: ignore[arg-type]
    authored_payload = output.model_dump(mode="json")
    authored_payload.pop("context_facts", None)
    authored_payload.pop("unknowns", None)
    authored_text = _canonical_json(authored_payload)
    copied_text_safety_codes = {
        "result_guarantee",
        "mind_reading",
        "high_risk_instruction",
        "forced_irreversible_decision",
        "unreviewed_traditional_authority",
    }
    hard_failures = []
    for item in report.hard_failures:
        if item.code == "unknown_supported_field":
            matched_field = item.message.rsplit("：", 1)[-1].strip()
            if matched_field in _OWNER_PREVIEW_AGGREGATE_SUPPORT_FIELDS:
                continue
        if item.code in copied_text_safety_codes:
            matched_text = item.message.rsplit("：", 1)[-1].strip()
            if matched_text and matched_text not in authored_text:
                continue
        hard_failures.append(item.code)
    quality_failures = [item.code for item in report.quality_failures]
    visible_packet_refs = {
        ref
        for trace in output.source_trace
        if trace.source_kind is SourceKind.INTERPRETIVE_LINK
        and any(field.startswith("user_facing_reading.") for field in trace.supports_fields)
        for ref in trace.evidence_refs
        if ref in {"EV10", "EV11", "EV12", "EV13"}
    }
    if not visible_packet_refs:
        quality_failures.append("interpretation_packet_unused")
    return hard_failures, quality_failures


_PAGE8_DATE_PATTERN = re.compile(
    r"(?<!\d)20\d{2}[年/-](?:0?[1-9]|1[0-2])(?:月|[-/])(?:0?[1-9]|[12]\d|3[01])日?"
)
_PAGE8_SAFETY_FORBIDDEN = (
    "一定会",
    "必然会",
    "肯定会",
    "保证成功",
    "注定会",
    "他心里其实",
    "她心里其实",
    "对方内心一定",
    "立即买入",
    "立即卖出",
    "满仓",
    "停药",
    "自行减药",
    "必须立刻",
)
_PAGE8_RESERVED_FOR_LATER = (
    "可借之力",
    "当慎之处",
    "下一步",
    "何时转向",
    "核心判断",
    "建议你",
    "你应该",
    "你应当",
)


def _validate_page8_output(
    reality: OwnerPreviewRealityContext,
    chart_context: ChartContext,
    output: OwnerPreviewExperimentOutputPage8V1,
) -> list[str]:
    failures: list[str] = []
    allowed_reality_refs = reality.reality_refs()
    allowed_evidence_refs = chart_context.evidence_refs()
    for layer in output.layered_reading:
        prefix = f"page8_{layer.scene_id.value.lower()}"
        if not set(layer.reality_refs).issubset(allowed_reality_refs):
            failures.append(f"{prefix}_unknown_reality_ref")
        if not set(layer.evidence_refs).issubset(allowed_evidence_refs):
            failures.append(f"{prefix}_unknown_evidence_ref")
        authored_text = "".join(
            (
                layer.layer_summary,
                layer.reality_connection,
                layer.uncertainty_boundary,
            )
        )
        if _PAGE8_DATE_PATTERN.search(authored_text):
            failures.append(f"{prefix}_specific_date")
        if any(term in authored_text for term in _PAGE8_SAFETY_FORBIDDEN):
            failures.append(f"{prefix}_unsafe_claim")
        if any(term in authored_text for term in _PAGE8_RESERVED_FOR_LATER):
            failures.append(f"{prefix}_page9_content")
        if not any(
            marker in layer.uncertainty_boundary
            for marker in ("不能", "不可", "仍", "未知", "不等于", "无法")
        ):
            failures.append(f"{prefix}_unclear_uncertainty_boundary")
    return failures


def _restore_input_unknowns(
    reality: OwnerPreviewRealityContext,
    output: OwnerPreviewExperimentOutputPage8V1,
) -> tuple[OwnerPreviewExperimentOutputPage8V1, bool]:
    """Keep copied unknowns deterministic instead of trusting model transcription."""
    expected_unknowns = [item.text for item in reality.unknowns]
    model_unknowns = [item.unknown_text for item in output.unknowns]
    normalized_payload = output.model_dump(mode="python")
    normalized_payload["unknowns"] = [
        {"unknown_text": text, "must_not_infer": True}
        for text in expected_unknowns
    ]
    return (
        OwnerPreviewExperimentOutputPage8V1.model_validate(normalized_payload),
        model_unknowns != expected_unknowns,
    )


def _error(
    request_id: str,
    status: str,
    message: str,
    *,
    preview_meta_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preview_meta = {
        "owner_preview_only": True,
        "should_charge": False,
        "formal_persistence_allowed": False,
    }
    if preview_meta_extra:
        preview_meta.update(preview_meta_extra)
    return {
        "contract_version": OWNER_PREVIEW_CONTRACT_VERSION,
        "request_id": request_id,
        "status": status,
        "deterministic_result": None,
        "personalized_reading": None,
        "preview_meta": preview_meta,
        "error": message,
    }


def _provider_failure_meta(exc: Exception) -> dict[str, Any]:
    if not isinstance(exc, Gate2LiveProviderError):
        return {
            "failure_stage": "PROVIDER_OR_SCHEMA",
            "failure_codes": [type(exc).__name__],
        }
    meta: dict[str, Any] = {
        "failure_stage": "PROVIDER_OR_SCHEMA",
        "failure_codes": [exc.code],
        "provider_api_status": exc.api_status or "unknown",
        "provider_poll_count": exc.poll_count,
    }
    if exc.incomplete_reason:
        meta["provider_incomplete_reason"] = exc.incomplete_reason[:120]
    if exc.cost_usd is not None:
        meta["actual_api_cost_usd"] = exc.cost_usd
    return meta


def _provider_failure_message(failure_codes: list[str]) -> str:
    provider_prefixes = (
        "background_",
        "rate_limit",
        "authentication_failed",
        "api_key_missing",
    )
    communication_markers = ("_timeout", "_connection_failed")
    if any(
        code.startswith(provider_prefixes) or code.endswith(communication_markers)
        for code in failure_codes
    ):
        return (
            "OpenAI 服务本次未能完成通信；系统没有创建第二次生成，"
            "也没有调用模型修复。"
        )
    return "本次新版解读未能完成结构或安全检查，未展示也不会自动重新生成。"


def _live_generator(prompt: Gate2PromptPackage) -> Gate2ProviderResult:
    from abalo_iching.personalization_gate2.background_provider import (
        OpenAIGate2BackgroundProvider,
    )

    class OwnerPreviewProvider(OpenAIGate2BackgroundProvider):
        provider_name = "OPENAI_RESPONSES_API_OWNER_PREVIEW_BACKGROUND"
        output_model = OwnerPreviewExperimentOutputPage8V1
        stage_label = "OWNER_PREVIEW_PAGE8_MODEL_V1"

    provider = OwnerPreviewProvider(
        model=OWNER_PREVIEW_MODEL,
        reasoning_effort=OWNER_PREVIEW_REASONING_EFFORT,
        max_output_tokens=OWNER_PREVIEW_MAX_OUTPUT_TOKENS,
        max_poll_attempts=OWNER_PREVIEW_MAX_POLL_ATTEMPTS,
    )
    return provider.generate(prompt)


def process_sites_owner_preview_v1_request(
    request_payload: Any,
    *,
    generator: Callable[[Gate2PromptPackage], Gate2ProviderResult] | None = None,
    clock: Callable[[], datetime] | None = None,
    input_provenance: Literal["SYNTHETIC", "REAL"] = "REAL",
) -> dict[str, Any]:
    request_id = (
        str(request_payload.get("request_id", "invalid-request"))[:80]
        if isinstance(request_payload, dict)
        else "invalid-request"
    )
    try:
        payload = OwnerPreviewPayload.model_validate(request_payload)
        payload.confirmed_facts = _nonempty_lines(payload.confirmed_facts)
        payload.unknowns = _nonempty_lines(payload.unknowns)
        if any(value < 1 or value > 999 for value in payload.numbers):
            raise ValueError("三个数字必须在1到999之间。")
    except (ValidationError, ValueError):
        return _error(request_id, "VALIDATION_ERROR", "请完整填写问题、已确认事实、未知项和三个数字。")

    v3_payload = {
        "contract_version": CONTRACT_VERSION_V3,
        "request_id": payload.request_id,
        "question_text": payload.question_text,
        "question_domain": payload.question_domain,
        "decision_goal": payload.decision_goal,
        "time_horizon": payload.time_horizon,
        "decision_stage": payload.decision_stage,
        "key_uncertainty": payload.key_uncertainty,
        "decision_risk_profile": payload.decision_risk_profile,
        "numbers": payload.numbers,
        "locale": payload.locale,
        "client_timestamp": payload.client_timestamp,
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "question_text_not_evidence": True,
        },
    }
    deterministic = process_sites_meihua_v3_request(
        v3_payload,
        clock=clock,
        input_provenance=input_provenance,
    )
    if deterministic.get("status") != "SUCCESS":
        return _error(payload.request_id, "VALIDATION_ERROR", "排盘输入未通过验证，请检查后再试。")

    payload.question_text = deterministic["user_question"]
    generated_at = datetime.fromisoformat(deterministic["audit"]["generated_at"])
    reality = _reality(payload)
    chart_context, interpretation_packet = _chart_context(payload, generated_at)
    prompt = _prompt(reality, chart_context, interpretation_packet)
    preflight = Gate2TokenPricing(model=OWNER_PREVIEW_MODEL).conservative_preflight_estimate(
        prompt,
        max_output_tokens=OWNER_PREVIEW_MAX_OUTPUT_TOKENS,
    )
    if generator is None:
        if os.getenv("ABALO_OWNER_PREVIEW_ENABLED", "").strip().lower() != "true":
            return _error(payload.request_id, "PREVIEW_DISABLED", "新版解读私有体验尚未启用。")
        generator = _live_generator
    try:
        provider_result = generator(prompt)
        output = OwnerPreviewExperimentOutputPage8V1.model_validate(provider_result.raw_output)
        output, model_unknowns_replaced = _restore_input_unknowns(reality, output)
        hard_failures, quality_failures = _validate_output(reality, chart_context, output)
        hard_failures.extend(_validate_page8_output(reality, chart_context, output))
    except Exception as exc:
        failure_meta = _provider_failure_meta(exc)
        LOGGER.warning(
            "owner_preview_generation_failed request_id=%s failure_stage=%s failure_codes=%s api_status=%s cost_usd=%s",
            payload.request_id,
            failure_meta["failure_stage"],
            ",".join(failure_meta["failure_codes"]),
            failure_meta.get("provider_api_status", "unavailable"),
            failure_meta.get("actual_api_cost_usd", "unknown"),
        )
        return _error(
            payload.request_id,
            "PREVIEW_FAILED",
            _provider_failure_message(failure_meta["failure_codes"]),
            preview_meta_extra=failure_meta,
        )
    if hard_failures or quality_failures:
        hard_failure_codes = sorted(set(hard_failures))
        quality_failure_codes = sorted(set(quality_failures))
        LOGGER.warning(
            "owner_preview_validation_failed request_id=%s hard_failure_codes=%s quality_failure_codes=%s api_status=%s cost_usd=%s",
            payload.request_id,
            ",".join(hard_failure_codes) or "none",
            ",".join(quality_failure_codes) or "none",
            provider_result.api_status or "unknown",
            provider_result.cost_usd,
        )
        return _error(
            payload.request_id,
            "PREVIEW_FAILED",
            "本次新版解读未通过安全或质量检查，未展示也不会自动重试。",
            preview_meta_extra={
                "stored": False,
                "automatic_sdk_retries": 0,
                "automatic_model_repair_calls": 0,
                "model": OWNER_PREVIEW_MODEL,
                "reasoning_effort": OWNER_PREVIEW_REASONING_EFFORT,
                "prompt_version": OWNER_PREVIEW_PROMPT_VERSION,
                "validator_version": OWNER_PREVIEW_VALIDATOR_VERSION,
                "input_unknowns_canonicalized": True,
                "model_unknowns_replaced": model_unknowns_replaced,
                "failure_stage": "OUTPUT_VALIDATION",
                "failure_codes": hard_failure_codes + quality_failure_codes,
                "hard_failure_codes": hard_failure_codes,
                "quality_failure_codes": quality_failure_codes,
                "actual_api_cost_usd": provider_result.cost_usd,
                "preflight_estimated_cost_usd": float(preflight),
                "hard_cost_limit_enabled": False,
            },
        )
    try:
        page8_reading = build_page8_reading_v1(
            user_question=deterministic["user_question"],
            deterministic_result=deterministic["deterministic_result"],
            interpretations=output.layered_reading,
        )
    except (ValidationError, ValueError) as exc:
        LOGGER.warning(
            "owner_preview_page8_model_failed request_id=%s failure=%s",
            payload.request_id,
            type(exc).__name__,
        )
        return _error(
            payload.request_id,
            "PREVIEW_FAILED",
            "本次第八页数据模型没有通过完整性检查，未展示也不会自动重试。",
            preview_meta_extra={
                "failure_stage": "PAGE8_MODEL_ASSEMBLY",
                "failure_codes": [type(exc).__name__],
            },
        )
    return {
        "contract_version": OWNER_PREVIEW_CONTRACT_VERSION,
        "request_id": payload.request_id,
        "status": "SUCCESS",
        "user_question": deterministic["user_question"],
        "structured_intake": deterministic["structured_intake"],
        "deterministic_result": deterministic["deterministic_result"],
        "personalized_reading": output.user_facing_reading.model_dump(mode="json"),
        "page8_reading": page8_reading.model_dump(mode="json"),
        "preview_meta": {
            "owner_preview_only": True,
            "should_charge": False,
            "formal_persistence_allowed": False,
            "stored": False,
            "automatic_sdk_retries": 0,
            "automatic_model_repair_calls": 0,
            "model": OWNER_PREVIEW_MODEL,
            "reasoning_effort": OWNER_PREVIEW_REASONING_EFFORT,
            "prompt_version": OWNER_PREVIEW_PROMPT_VERSION,
            "validator_version": OWNER_PREVIEW_VALIDATOR_VERSION,
            "input_unknowns_canonicalized": True,
            "model_unknowns_replaced": model_unknowns_replaced,
            "actual_api_cost_usd": provider_result.cost_usd,
            "preflight_estimated_cost_usd": float(preflight),
            "hard_cost_limit_enabled": False,
        },
        "error": None,
    }
