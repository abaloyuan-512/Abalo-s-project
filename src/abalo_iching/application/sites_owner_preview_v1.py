"""Owner-only personalized reading preview; isolated from the formal V3 release path."""

from __future__ import annotations

import hashlib
import json
import os
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
    StrictModel,
    UnknownItem,
)
from abalo_iching.personalization_gate2.pricing import Gate2TokenPricing
from abalo_iching.personalization_gate2.stage_c2_contract import (
    C2_SOURCE_TRACE_INSTRUCTIONS,
    Gate2ExperimentOutputV2,
    Gate2StageC2Validator,
)

from .sites_meihua_service_v3 import (
    CONTRACT_VERSION_V3,
    process_sites_meihua_v3_request,
)


OWNER_PREVIEW_CONTRACT_VERSION = "SITES_OWNER_PREVIEW_CONTRACT_V1"
OWNER_PREVIEW_PROMPT_VERSION = "guanxiang_owner_preview_v2"
OWNER_PREVIEW_VALIDATOR_VERSION = "guanxiang_owner_preview_validator_v2"
OWNER_PREVIEW_MODEL = "gpt-5.6-sol"
OWNER_PREVIEW_REASONING_EFFORT = "medium"
OWNER_PREVIEW_MAX_OUTPUT_TOKENS = 10_000

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
""".strip()

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


OWNER_PREVIEW_SYSTEM_INSTRUCTIONS = """你正在生成观象的所有者私有体验版解读，不是正式发布内容。
只使用输入中列出的用户陈述与程序提供的卦象 Evidence；用户陈述尚未经外部核验，不得把未知信息补写成事实。
不得重新排盘、读心、保证结果、生成输入未提供的具体日期，或提供证券与医疗操作指令。
现实陈述、卦象事实和解释接榫必须分开。解释接榫只能标记为实验性解释假设。
context_facts.fact_text 必须逐字复制其唯一 reality_refs 对应的输入陈述，不得改写或补充。
第一段先给一个明确但不过界的主要判断；说明为什么不是相反姿态，并给出具体对象、动作、可观察结果与转向条件。
只能引用输入中提供的 EVxx；所有解释接榫必须同时引用现实陈述与卦象事实。
中文应自然、平实、具体，有少量传统文化气息；避免翻译腔、抽象 AI 句法和万能咨询套话。
必须严格按给定结构化 Schema 输出，不得增加字段。一次生成完成，不请求工具，不联网，不自我修复。"""


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
        explicit_facts=referenced(facts),
        unknowns=[UnknownItem(text=item) for item in unknowns],
        options=referenced(options),
        actions_already_taken=referenced(actions),
        observable_responses=referenced(responses),
    )


def _chart_context(payload: OwnerPreviewPayload, generated_at: datetime) -> ChartContext:
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
    return ChartContext(
        chart_mapping_id=f"CHART-{hashlib.sha256(chart_bytes).hexdigest()[:20]}",
        is_mismatched_control=False,
        evidence=evidence,
    )


def _prompt(
    reality: OwnerPreviewRealityContext,
    chart_context: ChartContext,
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
        "allowed_reality_refs": sorted(reality.reality_refs()),
        "allowed_evidence_refs": sorted(chart_context.evidence_refs()),
        "output_schema": Gate2ExperimentOutputV2.model_json_schema(),
    }
    instructions = (
        f"{OWNER_PREVIEW_SYSTEM_INSTRUCTIONS}\n\n"
        f"{C2_SOURCE_TRACE_INSTRUCTIONS}\n\n"
        f"{OWNER_PREVIEW_TRACE_COVERAGE_INSTRUCTIONS}"
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
    output: Gate2ExperimentOutputV2,
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
        if item.code in copied_text_safety_codes:
            matched_text = item.message.rsplit("：", 1)[-1].strip()
            if matched_text and matched_text not in authored_text:
                continue
        hard_failures.append(item.code)
    return (
        hard_failures,
        [item.code for item in report.quality_failures],
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


def _live_generator(prompt: Gate2PromptPackage) -> Gate2ProviderResult:
    from abalo_iching.personalization_gate2.background_provider import (
        OpenAIGate2BackgroundProvider,
    )

    class OwnerPreviewProvider(OpenAIGate2BackgroundProvider):
        provider_name = "OPENAI_RESPONSES_API_OWNER_PREVIEW_BACKGROUND"
        output_model = Gate2ExperimentOutputV2
        stage_label = "OWNER_PREVIEW_V1"

    provider = OwnerPreviewProvider(
        model=OWNER_PREVIEW_MODEL,
        reasoning_effort=OWNER_PREVIEW_REASONING_EFFORT,
        max_output_tokens=OWNER_PREVIEW_MAX_OUTPUT_TOKENS,
        max_poll_attempts=40,
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
    chart_context = _chart_context(payload, generated_at)
    prompt = _prompt(reality, chart_context)
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
        output = Gate2ExperimentOutputV2.model_validate(provider_result.raw_output)
        hard_failures, quality_failures = _validate_output(reality, chart_context, output)
    except Exception:
        return _error(payload.request_id, "PREVIEW_FAILED", "本次新版解读未通过安全检查，未展示也不会自动重试。")
    if hard_failures or quality_failures:
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
                "actual_api_cost_usd": provider_result.cost_usd,
                "preflight_estimated_cost_usd": float(preflight),
                "hard_cost_limit_enabled": False,
            },
        )
    return {
        "contract_version": OWNER_PREVIEW_CONTRACT_VERSION,
        "request_id": payload.request_id,
        "status": "SUCCESS",
        "deterministic_result": deterministic["deterministic_result"],
        "personalized_reading": output.user_facing_reading.model_dump(mode="json"),
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
            "actual_api_cost_usd": provider_result.cost_usd,
            "preflight_estimated_cost_usd": float(preflight),
            "hard_cost_limit_enabled": False,
        },
        "error": None,
    }
