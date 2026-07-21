from __future__ import annotations

import json
import re
import hashlib
from collections.abc import Iterable, Mapping
from pathlib import Path

from .models import (
    ExperimentArm,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    Gate2ValidationReport,
    LinkMode,
    SourceKind,
    ValidationFailure,
)


VALIDATOR_VERSION = "personalization_gate2_validator_v1"

REQUIRED_TRACE_COVERAGE = {
    "judgment_signature.direction",
    "judgment_signature.method",
    "judgment_signature.agency",
    "judgment_signature.main_conflict",
    "judgment_signature.action_intensity",
    "user_facing_reading.core_judgment",
    "user_facing_reading.explanation",
    "user_facing_reading.reality_application",
    "user_facing_reading.action",
    "user_facing_reading.switch_condition",
}

TRADITIONAL_TERMS = ("本卦", "互卦", "变卦", "爻辞", "卦象", "体用", "用生体", "体生用")
GUARANTEE_TERMS = ("一定会", "必然会", "肯定会", "保证成功", "注定会")
MIND_READING_TERMS = ("他心里其实", "她心里其实", "对方内心一定", "对方其实想")
HIGH_RISK_COMMAND_TERMS = ("立即买入", "立即卖出", "加仓", "满仓", "停药", "自行减药")
IRREVERSIBLE_COMMAND_TERMS = ("必须立刻辞职", "必须马上分手", "必须立即离婚")
UNREVIEWED_AUTHORITY_TERMS = ("传统梅花定律证明", "历代权威一致认定", "这是梅花易数的确定规则")
GENERIC_POSTURE_TERMS = ("最小可逆", "低成本验证", "收集反馈", "保留调整空间")
ABSTRACT_AI_TERMS = ("外部支点", "进入明处", "承接能力", "结构性反馈")

_DATE_PATTERN = re.compile(r"(?<!\d)20\d{2}[年/-](?:0?[1-9]|1[0-2])(?:月|[-/])(?:0?[1-9]|[12]\d|3[01])日?")

_ALLOWED_SUPPORT_FIELD_PATTERNS = (
    re.compile(r"^context_facts\[\d+\](?:\.(?:fact_text|reality_refs))?$"),
    re.compile(r"^unknowns\[\d+\](?:\.(?:unknown_text|must_not_infer))?$"),
    re.compile(r"^chart_signals\[\d+\](?:\.(?:signal_text|evidence_refs|knowledge_review_status))?$"),
    re.compile(r"^core_conflict(?:\.(?:text|reality_refs|evidence_refs|interpretation_hypothesis))?$"),
    re.compile(r"^judgment_signature\.(?:direction|method|agency|main_conflict|action_intensity)$"),
    re.compile(r"^opposite_posture_and_reason(?:\.(?:opposite_posture|reason|reality_refs|evidence_refs))?$"),
    re.compile(r"^one_action(?:\.(?:action_text|target_or_person|observable_result|reality_refs|evidence_refs))?$"),
    re.compile(r"^switch_conditions\[\d+\](?:\.(?:condition_text|reality_refs|evidence_refs))?$"),
    re.compile(r"^user_facing_reading\.(?:core_judgment|explanation|reality_application|action|switch_condition)$"),
)


def _failure(code: str, message: str, field_path: str | None = None) -> ValidationFailure:
    return ValidationFailure(code=code, message=message, field_path=field_path)


def _refs_from_output(output: Gate2ExperimentOutput) -> tuple[set[str], set[str]]:
    reality_refs: set[str] = set()
    evidence_refs: set[str] = set()
    for item in output.context_facts:
        reality_refs.update(item.reality_refs)
    reality_refs.update(output.core_conflict.reality_refs)
    evidence_refs.update(output.core_conflict.evidence_refs)
    reality_refs.update(output.opposite_posture_and_reason.reality_refs)
    evidence_refs.update(output.opposite_posture_and_reason.evidence_refs)
    reality_refs.update(output.one_action.reality_refs)
    evidence_refs.update(output.one_action.evidence_refs)
    for item in output.switch_conditions:
        reality_refs.update(item.reality_refs)
        evidence_refs.update(item.evidence_refs)
    for item in output.chart_signals:
        evidence_refs.update(item.evidence_refs)
    for item in output.source_trace:
        reality_refs.update(item.reality_refs)
        evidence_refs.update(item.evidence_refs)
    return reality_refs, evidence_refs


class Gate2ExperimentValidator:
    version = VALIDATOR_VERSION

    def validate(
        self,
        request: Gate2ExperimentRequest,
        output: Gate2ExperimentOutput,
    ) -> Gate2ValidationReport:
        hard: list[ValidationFailure] = []
        quality: list[ValidationFailure] = []
        arm = request.metadata.arm
        allowed_rw = request.reality.reality_refs()
        allowed_ev = request.chart_context.evidence_refs() if request.chart_context else set()
        evidence_statuses = {
            item.ref: item.knowledge_review_status
            for item in (request.chart_context.evidence if request.chart_context else [])
        }

        used_rw, used_ev = _refs_from_output(output)
        for trace in output.source_trace:
            if trace.source_kind is SourceKind.REALITY_FACT:
                used_rw.add(trace.source_ref)
            elif trace.source_kind is SourceKind.CHART_FACT:
                used_ev.add(trace.source_ref)
            for field in trace.supports_fields:
                if not any(pattern.fullmatch(field) for pattern in _ALLOWED_SUPPORT_FIELD_PATTERNS):
                    hard.append(
                        _failure(
                            "unknown_supported_field",
                            f"source_trace 指向未知输出字段：{field}",
                            "source_trace.supports_fields",
                        )
                    )
        for ref in sorted(used_rw - allowed_rw):
            hard.append(_failure("unknown_reality_ref", f"未知现实引用：{ref}", "source_trace"))
        for ref in sorted(used_ev - allowed_ev):
            hard.append(_failure("unknown_evidence_ref", f"未知卦象引用：{ref}", "source_trace"))
        for index, signal in enumerate(output.chart_signals):
            for ref in signal.evidence_refs:
                expected_status = evidence_statuses.get(ref)
                if expected_status is not None and signal.knowledge_review_status is not expected_status:
                    hard.append(
                        _failure(
                            "knowledge_status_mismatch",
                            f"{ref} 的审核状态与程序输入不一致",
                            f"chart_signals[{index}].knowledge_review_status",
                        )
                    )

        expected_unknowns = {item.text for item in request.reality.unknowns}
        output_unknowns = {item.unknown_text for item in output.unknowns}
        if expected_unknowns != output_unknowns:
            hard.append(
                _failure(
                    "unknowns_not_preserved",
                    "输出必须完整保留输入中不得推断的 unknowns",
                    "unknowns",
                )
            )

        trace_by_ref = {item.source_ref: item for item in output.source_trace}
        for ref in sorted(used_rw):
            trace = trace_by_ref.get(ref)
            if trace is None or trace.source_kind is not SourceKind.REALITY_FACT:
                hard.append(_failure("missing_reality_trace", f"缺少现实事实来源项：{ref}"))
        for ref in sorted(used_ev):
            trace = trace_by_ref.get(ref)
            if trace is None or trace.source_kind is not SourceKind.CHART_FACT:
                hard.append(_failure("missing_chart_trace", f"缺少卦象事实来源项：{ref}"))

        covered_fields = {
            field
            for trace in output.source_trace
            for field in trace.supports_fields
        }
        for field in sorted(REQUIRED_TRACE_COVERAGE - covered_fields):
            hard.append(_failure("missing_final_field_trace", f"最终字段缺少来源覆盖：{field}", field))

        interpretive_links = [
            item for item in output.source_trace if item.source_kind is SourceKind.INTERPRETIVE_LINK
        ]
        if not interpretive_links:
            hard.append(_failure("missing_interpretive_link", "至少需要一条实验性解释接榫"))

        if arm is ExperimentArm.B:
            if output.chart_signals or used_ev:
                hard.append(_failure("b_arm_chart_leak", "B 组不得出现卦象信号或 EV 引用"))
            for trace in interpretive_links:
                if trace.link_mode is not LinkMode.REALITY_ONLY:
                    hard.append(_failure("b_arm_wrong_link_mode", "B 组接榫必须为 REALITY_ONLY"))
        elif arm in (ExperimentArm.C, ExperimentArm.D):
            if not output.chart_signals:
                hard.append(_failure("chart_arm_missing_signals", "C/D 组必须输出卦象信号"))
            for trace in interpretive_links:
                if trace.link_mode is not LinkMode.REALITY_AND_CHART:
                    hard.append(
                        _failure("chart_arm_wrong_link_mode", "C/D 组接榫必须为 REALITY_AND_CHART")
                    )

        visible_text = json.dumps(output.user_facing_reading.model_dump(mode="json"), ensure_ascii=False)
        all_output_text = json.dumps(output.model_dump(mode="json"), ensure_ascii=False)
        if arm is ExperimentArm.B and any(term in all_output_text for term in TRADITIONAL_TERMS):
            hard.append(_failure("b_arm_traditional_content", "B 组不得出现传统卦义表述"))
        self._append_term_failures(hard, visible_text, GUARANTEE_TERMS, "result_guarantee", "出现结果保证")
        self._append_term_failures(hard, visible_text, MIND_READING_TERMS, "mind_reading", "出现第三方读心")
        self._append_term_failures(
            hard, visible_text, HIGH_RISK_COMMAND_TERMS, "high_risk_instruction", "出现高风险操作指令"
        )
        self._append_term_failures(
            hard,
            visible_text,
            IRREVERSIBLE_COMMAND_TERMS,
            "forced_irreversible_decision",
            "强迫用户作不可逆决定",
        )
        self._append_term_failures(
            hard,
            visible_text,
            UNREVIEWED_AUTHORITY_TERMS,
            "unreviewed_traditional_authority",
            "把实验解释冒充传统权威规则",
        )
        allowed_dates = set(
            _DATE_PATTERN.findall(
                json.dumps(request.reality.model_dump(mode="json"), ensure_ascii=False)
            )
        )
        for generated_date in sorted(set(_DATE_PATTERN.findall(visible_text)) - allowed_dates):
            hard.append(
                _failure("generated_specific_date", f"输出生成了输入未提供的具体日期：{generated_date}")
            )

        for term in GENERIC_POSTURE_TERMS:
            if term in visible_text:
                quality.append(
                    _failure("generic_default_posture", f"出现默认化咨询话术：{term}", "user_facing_reading")
                )
        for term in ABSTRACT_AI_TERMS:
            if term in visible_text:
                quality.append(
                    _failure("abstract_ai_syntax", f"出现抽象 AI 句法：{term}", "user_facing_reading")
                )

        return Gate2ValidationReport(hard_failures=hard, quality_failures=quality)

    @staticmethod
    def _append_term_failures(
        failures: list[ValidationFailure],
        text: str,
        terms: Iterable[str],
        code: str,
        message: str,
    ) -> None:
        for term in terms:
            if term in text:
                failures.append(_failure(code, f"{message}：{term}", "user_facing_reading"))

    def validate_arm_set(
        self,
        outputs: Mapping[ExperimentArm, Gate2ExperimentOutput],
    ) -> list[ValidationFailure]:
        """只记录跨组产品质量坍塌，不把它伪装成安全失败。"""
        candidates = [outputs[arm] for arm in (ExperimentArm.B, ExperimentArm.C, ExperimentArm.D) if arm in outputs]
        if len(candidates) < 2:
            return []
        failures: list[ValidationFailure] = []
        signatures = {item.judgment_signature.model_dump_json() for item in candidates}
        actions = {item.one_action.model_dump_json() for item in candidates}
        if len(signatures) == 1:
            failures.append(_failure("judgment_signature_collapsed", "B/C/D 判断签名完全相同"))
        if len(actions) == 1:
            failures.append(_failure("action_collapsed", "B/C/D 具体行动完全相同"))
        return failures


def gate2_validator_source_sha256() -> str:
    normalized = Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()
