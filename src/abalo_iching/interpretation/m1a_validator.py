"""Independent M1-A narrative validator; historical Validator V2 remains untouched."""

from __future__ import annotations

import json

from pydantic import ValidationError

from abalo_iching.meihua.enums import EvidencePolarity, EvidenceStrength

from .exceptions import InterpretationValidationError
from .m1a_context import M1AEvidenceRole, M1AIntakeView
from .m1a_evidence_catalog import M1AEvidenceCatalogError, M1ASafeEvidenceCatalog
from .models import AINarrativeDraftContent
from .validators import InterpretationValidator, _TIME_PATTERNS, normalize_text

M1A_VALIDATOR_VERSION = "MEIHUA_M1A_NARRATIVE_VALIDATOR_V1"

_FIELD_ROLES = {
    "plain_language_explanation": M1AEvidenceRole.EXPLANATION,
    "real_world_advice": M1AEvidenceRole.ACTION_OPTION,
    "conditions_that_change_outcome": M1AEvidenceRole.CONDITION,
    "review_questions": M1AEvidenceRole.REVIEW_QUESTION,
}
_ACTION_PREFIXES = ("可以考虑", "可先", "建议先", "可以先", "可考虑")
_OBSERVABLE_TERMS = ("核实", "观察", "反馈", "条件", "记录", "信号", "复盘")
_UNCERTAINTY_TERMS = ("可能", "需要", "不代表", "仍需", "不能", "尚不", "避免提前")
_FAVORABLE_TERMS = ("有利", "利好", "会成功", "一定能", "应立即推进", "值得马上推进")
_UNFAVORABLE_TERMS = ("不利", "会失败", "应当停止", "必须放弃", "注定失败")
_STRENGTH_INFLATION_TERMS = ("明确证明", "强烈证明", "高度确定", "足以确定", "决定性证明")
_GENERAL_FORBIDDEN = (
    "必然",
    "注定",
    "百分之百",
    "100%",
    "一定会",
    "保证结果",
    "系统prompt",
    "openai_api_key",
    "sk-",
    "买币",
    "买股",
    "上杠杆",
    "博彩",
    "赌一把",
    "不用看医生",
    "停止服药",
)
_PROGRAM_CONCLUSION_TERMS = (
    "程序结论",
    "结论等级",
    "明确有利",
    "条件性有利",
    "混合未定",
    "明确不利",
    "证据不足",
    "clearly_favorable",
    "conditionally_favorable",
    "mixed_or_unsettled",
    "clearly_unfavorable",
    "insufficient_evidence",
)
_DOMAIN_FORBIDDEN = {
    "WORK_CAREER": (
        "保证录用",
        "保证升职",
        "保证收入",
        "招聘方心里",
        "招聘方一定",
        "立刻辞职",
        "必须辞职",
        "对方爱你",
        "建议投资",
        "法律结论",
    ),
    "PROJECT_COOPERATION": (
        "投资",
        "证券",
        "借贷",
        "融资",
        "担保",
        "收益",
        "回本",
        "合作方心里",
        "项目一定成功",
        "保证项目成功",
        "对方爱你",
        "心理诊断",
    ),
    "RELATIONSHIP_COMMUNICATION": (
        "对方爱你",
        "对方不爱你",
        "真实心理是",
        "内心已经",
        "一定会回来",
        "一定会离开",
        "操控",
        "监视",
        "跟踪",
        "强迫",
        "建议投资",
        "诊断为",
        "保证录用",
    ),
    "PERSONAL_PLANNING": (
        "诊断为",
        "抑郁症",
        "焦虑症",
        "投资",
        "借贷",
        "收益",
        "法律结论",
        "违法",
        "命中注定",
        "宿命",
        "必须迁居",
        "必须搬家",
        "必须结婚",
        "必须离婚",
        "必须辞职",
        "保证录用",
        "合作方心里",
        "对方爱你",
    ),
}
_GOAL_FOCUS_TERMS = {
    "IDENTIFY_OBSTACLES": ("阻力", "条件", "风险", "支持", "信号"),
    "PLAN_NEXT_STEP": ("下一步", "先", "小步", "尝试", "验证"),
    "PREPARE_COMMUNICATION": ("沟通", "表达", "询问", "确认", "反馈"),
    "ADJUST_COMMITMENT_BOUNDARIES": ("边界", "投入", "承诺", "调整", "暂停"),
    "OBSERVE_VERIFY_SIGNALS": ("观察", "核实", "反馈", "信号", "记录", "复盘"),
}


def _enum_value(value: object) -> str:
    resolved = getattr(value, "value", None)
    return resolved if isinstance(resolved, str) else ""


def _claims(output: AINarrativeDraftContent):
    for field in _FIELD_ROLES:
        for claim in getattr(output, field):
            yield field, claim


class M1AValidator:
    def validate(
        self,
        raw_output: AINarrativeDraftContent | dict[str, object] | object,
        intake: M1AIntakeView,
        catalog: M1ASafeEvidenceCatalog,
    ) -> AINarrativeDraftContent:
        try:
            if isinstance(raw_output, AINarrativeDraftContent):
                output = raw_output
            elif isinstance(raw_output, dict):
                output = AINarrativeDraftContent.model_validate(raw_output)
            else:
                payload = raw_output.model_dump(mode="json") if hasattr(raw_output, "model_dump") else raw_output
                output = AINarrativeDraftContent.model_validate(payload)
        except (AttributeError, TypeError, ValidationError) as exc:
            errors = getattr(exc, "errors", lambda: [])()
            locations = [".".join(str(part) for part in item["loc"]) for item in errors]
            codes = [f"schema:{location}" for location in locations] or ["schema:invalid_output"]
            raise InterpretationValidationError(codes) from exc

        errors: list[str] = []
        entries_by_ref = {item.provider_evidence_ref: item for item in catalog.entries}
        for field, claim in _claims(output):
            required_role = _FIELD_ROLES[field]
            for evidence_ref in claim.evidence_refs:
                try:
                    catalog.resolve(evidence_ref, required_role=required_role)
                except M1AEvidenceCatalogError as exc:
                    errors.append(str(exc))
            errors.extend(self._validate_evidence_semantics(claim.text, claim.evidence_refs, entries_by_ref))
            normalized_claim = normalize_text(claim.text)
            if field == "real_world_advice" and not normalized_claim.startswith(
                tuple(normalize_text(item) for item in _ACTION_PREFIXES)
            ):
                errors.append("M1A_ACTION_NOT_USER_CONTROLLED_REVERSIBLE")
            if field == "plain_language_explanation" and not any(
                normalize_text(term) in normalized_claim for term in _UNCERTAINTY_TERMS
            ):
                errors.append("M1A_EXPLANATION_NOT_CALIBRATED")
            if field == "conditions_that_change_outcome":
                if not any(entries_by_ref.get(ref) and entries_by_ref[ref].conditions for ref in claim.evidence_refs):
                    errors.append("M1A_CONDITION_NOT_PROGRAM_GROUNDED")
            if field == "review_questions" and not claim.text.endswith(("?", "？")):
                errors.append("M1A_REVIEW_NOT_QUESTION")

        rendered = json.dumps(output.model_dump(mode="json"), ensure_ascii=False)
        normalized = normalize_text(rendered)
        if not any(normalize_text(term) in normalized for term in _OBSERVABLE_TERMS):
            errors.append("M1A_NO_VERIFIABLE_REALITY_OBSERVATION")
        if InterpretationValidator._contains_program_fact_restatement(normalized):
            errors.append("M1A_PROGRAM_FACT_RESTATEMENT")
        if any(pattern.search(normalized) for pattern in _TIME_PATTERNS):
            errors.append("M1A_TIME_JUDGMENT_FORBIDDEN")
        if any(normalize_text(term) in normalized for term in _PROGRAM_CONCLUSION_TERMS):
            errors.append("M1A_PROGRAM_CONCLUSION_FORBIDDEN")
        if any(normalize_text(term) in normalized for term in _GENERAL_FORBIDDEN):
            errors.append("M1A_HIGH_RISK_OR_ABSOLUTE_CONTENT")
        domain = _enum_value(intake.question_domain)
        if domain not in _DOMAIN_FORBIDDEN:
            errors.append("M1A_DOMAIN_NOT_SUPPORTED")
        elif any(normalize_text(term) in normalized for term in _DOMAIN_FORBIDDEN[domain]):
            errors.append(f"M1A_{domain}_SEMANTIC_BOUNDARY_VIOLATION")
        goal = _enum_value(intake.decision_goal)
        if goal not in _GOAL_FOCUS_TERMS:
            errors.append("M1A_DECISION_GOAL_NOT_SUPPORTED")
        elif not any(normalize_text(term) in normalized for term in _GOAL_FOCUS_TERMS[goal]):
            errors.append("M1A_DECISION_GOAL_FOCUS_MISSING")
        if errors:
            raise InterpretationValidationError(sorted(set(errors)))
        return output

    @staticmethod
    def _validate_evidence_semantics(
        text: str,
        evidence_refs: list[str],
        entries_by_ref: dict[str, object],
    ) -> list[str]:
        entries = [entries_by_ref[ref] for ref in evidence_refs if ref in entries_by_ref]
        polarities = {item.polarity for item in entries}
        strengths = {item.strength for item in entries}
        normalized = normalize_text(text)
        favorable = any(normalize_text(term) in normalized for term in _FAVORABLE_TERMS)
        unfavorable = any(normalize_text(term) in normalized for term in _UNFAVORABLE_TERMS)
        errors: list[str] = []
        if EvidencePolarity.NEGATIVE in polarities and favorable:
            errors.append("M1A_NEGATIVE_EVIDENCE_REVERSED")
        if EvidencePolarity.POSITIVE in polarities and unfavorable:
            errors.append("M1A_POSITIVE_EVIDENCE_REVERSED")
        if EvidencePolarity.MIXED in polarities and (favorable or unfavorable):
            errors.append("M1A_MIXED_EVIDENCE_FORCED_DIRECTION")
        if EvidenceStrength.WEAK in strengths and any(
            normalize_text(term) in normalized for term in _STRENGTH_INFLATION_TERMS
        ):
            errors.append("M1A_WEAK_EVIDENCE_STRENGTH_INFLATED")
        return errors
