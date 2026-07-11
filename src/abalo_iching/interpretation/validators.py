"""Validate the narrow AI narrative surface; program facts never enter this model."""

from __future__ import annotations

import json
import re
import unicodedata

from pydantic import ValidationError

from abalo_iching.meihua.enums import EvidencePolarity, EvidenceType
from abalo_iching.meihua.hexagrams import load_hexagrams

from .enums import EpistemicBasis, NarrativeKind
from .exceptions import InterpretationValidationError
from .models import AINarrativeClaim, AINarrativeContent, InterpretationRequest, KnowledgeSelection, SynthesisResult


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).lower()


_TIME_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"(?<!\d)\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?!\d)",
        r"(?:\d{4}年)?(?:\d{1,2}|[一二两三四五六七八九十]{1,3})月(?:\d{1,2}|[一二三四五六七八九十]{1,3})(?:日|号)?",
        r"(?:[一二两三四五六七八九十百]+|\d+)(?:天|日|周|个月|月)(?:后|内|以内|之内)",
        r"(?:这两天|近日|过几天|月底前|本月底|月初|下旬|明晚|后日上午|下个月|下个礼拜|下下周|下周|周末|明天|后天)",
    )
)
_ABSOLUTE = (
    "必然", "注定", "百分之百", "百分百", "100%", "绝对会", "一定会", "必定", "肯定会", "铁定",
    "毫无疑问", "必成", "必败", "绝不会", "稳稳会成", "肯定能成", "跑不了", "没有悬念", "十拿九稳",
    "板上钉钉", "一准会", "准能成功",
)
_MIND_READING = (
    "他其实舍不得离开你", "他其实舍不得你", "她心里还有你", "对方仍在惦记你", "他只是没说出口",
    "她在等你主动", "对方早已做出决定", "他并不是真想离开", "她嘴上拒绝但心里接受", "对方仍然爱你",
    "他心里放不下你", "她已经决定离开", "对方正在欺骗你", "他只是嘴硬", "她真实想法是",
    "对方内心已经确认", "真实心理是",
)
_FINANCIAL = ("买币", "卖币", "买这只股", "赶紧入场", "建议建仓", "追涨", "做空", "上杠杆", "满仓", "抄底", "加仓")
_MEDICAL = ("把药停了", "停止服药", "少吃一点药", "自行减药", "不用看医生", "无需就医", "这是抑郁症", "已经患有", "这不是大问题", "自己调整剂量")
_SECRETS = ("openai_api_key", "sk-", "系统prompt", "systemprompt", "d:\\", "/home/")
_GENERIC = ("顺其自然", "一切皆有可能", "保持乐观即可")
_FAVORABLE_WORDS = ("有利", "利好", "会成", "成功", "值得立即推进")
_UNFAVORABLE_WORDS = ("不利", "是阻碍", "会败", "失败", "应当停止")
_ACTION_PREFIXES = ("可以考虑", "建议验证", "可先尝试", "可以先", "可考虑")
_CONDITION_TEMPLATE = "建议验证程序列出的条件是否已经满足。"

_FIELD_KIND = {
    "plain_language_explanation": NarrativeKind.EXPLANATION,
    "real_world_advice": NarrativeKind.ACTION_OPTION,
    "conditions_that_change_outcome": NarrativeKind.CONDITION_TO_VERIFY,
    "review_questions": NarrativeKind.REVIEW_QUESTION,
}
_FIELD_BASIS = {
    "plain_language_explanation": EpistemicBasis.CHART_EVIDENCE,
    "real_world_advice": EpistemicBasis.ACTION_OPTION,
    "conditions_that_change_outcome": EpistemicBasis.UNCERTAINTY,
    "review_questions": EpistemicBasis.UNCERTAINTY,
}


def _claims(output: AINarrativeContent):
    for field in _FIELD_KIND:
        for claim in getattr(output, field):
            yield field, claim


class InterpretationValidator:
    def validate(
        self,
        raw_output: AINarrativeContent | dict[str, object],
        request: InterpretationRequest,
        knowledge: KnowledgeSelection,
        synthesis: SynthesisResult,
    ) -> AINarrativeContent:
        try:
            output = raw_output if isinstance(raw_output, AINarrativeContent) else AINarrativeContent.model_validate(raw_output)
        except ValidationError as exc:
            locations = [".".join(str(part) for part in item["loc"]) for item in exc.errors()]
            raise InterpretationValidationError([f"schema:{location}" for location in locations]) from exc

        errors: list[str] = []
        evidence_by_id = {item.evidence_id: item for item in request.chart.evidence}
        knowledge_by_id = {item.evidence_id: item for item in knowledge.knowledge_evidence}
        unified_evidence = {**evidence_by_id, **knowledge_by_id}
        allowed_ids = set(unified_evidence)
        if knowledge.access_mode == "PRODUCTION" and any(
            item.preview or not item.evidence_id.startswith("K-") for item in knowledge.knowledge_evidence
        ):
            errors.append("preview_knowledge_in_production")
        relation_ids = {
            item.evidence_id
            for item in request.chart.evidence
            if item.evidence_type
            in {
                EvidenceType.INITIAL_BODY_USE_RELATION,
                EvidenceType.CHANGED_BODY_USE_RELATION,
                EvidenceType.BODY_SEASONAL_STRENGTH,
                EvidenceType.INITIAL_USE_SEASONAL_STRENGTH,
                EvidenceType.CHANGED_USE_SEASONAL_STRENGTH,
                EvidenceType.MOVING_LINE_STAGE,
            }
        } | set(knowledge.allowed_knowledge_evidence_ids)
        action_ids = set(synthesis.supporting_evidence_ids) | set(synthesis.blocking_evidence_ids)
        condition_ids = {
            item.evidence_ids[0] for item in synthesis.relation_assessments if item.conditions or item.warnings
        }

        for field, claim in _claims(output):
            ids = set(claim.evidence_ids)
            if ids - allowed_ids:
                errors.append("unknown_evidence_id")
            if claim.narrative_kind is not _FIELD_KIND[field]:
                errors.append(f"{field}_narrative_kind_mismatch")
            if claim.epistemic_basis is not _FIELD_BASIS[field]:
                errors.append(f"{field}_epistemic_basis_mismatch")
            if field == "plain_language_explanation" and ids - relation_ids:
                errors.append("explanation_evidence_role_mismatch")
            if field == "real_world_advice":
                if not ids or ids - action_ids:
                    errors.append("action_evidence_role_mismatch")
                if not normalize_text(claim.text).startswith(tuple(normalize_text(item) for item in _ACTION_PREFIXES)):
                    errors.append("action_option_not_noncoercive")
            if field == "conditions_that_change_outcome":
                if not condition_ids or ids - condition_ids or claim.text != _CONDITION_TEMPLATE:
                    errors.append("condition_not_program_grounded")
            if field == "review_questions" and not claim.text.endswith(("?", "？")):
                errors.append("review_question_not_question")
            errors.extend(self._validate_evidence_semantics(claim, unified_evidence))
            for evidence_id in ids & set(knowledge_by_id):
                for prohibited in knowledge_by_id[evidence_id].prohibited_inferences:
                    normalized_rule = normalize_text(prohibited)
                    for prefix in ("不得", "禁止"):
                        if normalized_rule.startswith(prefix):
                            normalized_rule = normalized_rule[len(prefix) :]
                    candidates = {normalized_rule}
                    for verb in ("推断", "声称", "生成", "提供"):
                        if verb in normalized_rule:
                            candidates.add(normalized_rule.split(verb, 1)[1])
                    if any(candidate and candidate in normalize_text(claim.text) for candidate in candidates):
                        errors.append("knowledge_prohibited_inference")

        text = json.dumps(output.model_dump(mode="json"), ensure_ascii=False)
        normalized = normalize_text(text)
        if self._contains_program_fact_restatement(normalized):
            errors.append("program_fact_restatement")
        if any(pattern.search(normalized) for pattern in _TIME_PATTERNS):
            errors.append("ai_time_content_forbidden")
        if any(normalize_text(term) in normalized for term in _ABSOLUTE):
            errors.append("absolute_assertion")
        if any(normalize_text(term) in normalized for term in _MIND_READING):
            errors.append("third_party_mind_reading")
        if any(normalize_text(term) in normalized for term in _FINANCIAL):
            errors.append("financial_instruction")
        if any(normalize_text(term) in normalized for term in _MEDICAL):
            errors.append("medical_instruction")
        if any(term in normalized for term in _SECRETS):
            errors.append("secret_or_internal_data")
        if any(normalize_text(term) in normalized for term in _GENERIC):
            errors.append("generic_unfalsifiable_content")
        if "现实背景是卦象" in normalized or "用户提供的背景属于卦象" in normalized:
            errors.append("real_world_context_misrepresented")
        if errors:
            raise InterpretationValidationError(sorted(set(errors)))
        return output

    @staticmethod
    def _validate_evidence_semantics(
        claim: AINarrativeClaim,
        evidence_by_id: dict[str, object],
    ) -> list[str]:
        polarities = {
            evidence_by_id[item].polarity
            for item in claim.evidence_ids
            if item in evidence_by_id and evidence_by_id[item].polarity is not None
        }
        normalized = normalize_text(claim.text)
        favorable = any(term in normalized for term in _FAVORABLE_WORDS)
        unfavorable = any(term in normalized for term in _UNFAVORABLE_WORDS)
        errors: list[str] = []
        if EvidencePolarity.NEGATIVE in polarities and favorable:
            errors.append("negative_evidence_semantic_reversal")
        if EvidencePolarity.POSITIVE in polarities and unfavorable:
            errors.append("positive_evidence_semantic_reversal")
        if EvidencePolarity.MIXED in polarities and (favorable or unfavorable):
            errors.append("mixed_evidence_forced_direction")
        return errors

    @staticmethod
    def _contains_program_fact_restatement(normalized: str) -> bool:
        fixed_terms = ("本卦", "互卦", "变卦", "动爻", "体卦", "用卦", "体克用", "用克体", "体生用", "用生体", "比和")
        if any(term in normalized for term in fixed_terms):
            return True
        if re.search(r"第(?:\d{1,2}|[一二三四五六七八九十百]{1,3})卦|(?:初|[一二三四五六上])爻", normalized):
            return True
        for hexagram in load_hexagrams():
            if normalize_text(hexagram.full_name_zh) in normalized or normalize_text(f"{hexagram.name_zh}卦") in normalized:
                return True
        return False
