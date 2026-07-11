"""Validated package-resource access and internal-only knowledge policy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

from abalo_iching.meihua.models import MeihuaChart

from .enums import KnowledgeAccessMode, KnowledgeEvidenceSourceType, KnowledgeReviewStatus
from .exceptions import KnowledgeIntegrityError
from .models import CanonicalHexagramText, HexagramKnowledge, KnowledgeEvidence, KnowledgeSelection, LineKnowledge

_DATA = files("abalo_iching.data.meihua")


@dataclass(frozen=True, slots=True)
class KnowledgeAccessPolicy:
    mode: KnowledgeAccessMode = KnowledgeAccessMode.PRODUCTION

    @property
    def allowed_statuses(self) -> frozenset[KnowledgeReviewStatus]:
        if self.mode is KnowledgeAccessMode.PRODUCTION:
            return frozenset({KnowledgeReviewStatus.APPROVED})
        if self.mode is KnowledgeAccessMode.INTERNAL_REVIEW:
            return frozenset({KnowledgeReviewStatus.REVIEWED, KnowledgeReviewStatus.APPROVED})
        return frozenset(
            {
                KnowledgeReviewStatus.DRAFT,
                KnowledgeReviewStatus.REVIEWED,
                KnowledgeReviewStatus.APPROVED,
            }
        )

    @property
    def is_preview(self) -> bool:
        return self.mode is not KnowledgeAccessMode.PRODUCTION


@lru_cache(maxsize=1)
def load_canonical_texts() -> tuple[CanonicalHexagramText, ...]:
    payload = json.loads(_DATA.joinpath("hexagram_canonical_texts_v1.json").read_text(encoding="utf-8"))
    records = tuple(CanonicalHexagramText.model_validate(item) for item in payload["hexagrams"])
    if len(records) != 64 or {item.king_wen_number for item in records} != set(range(1, 65)):
        raise KnowledgeIntegrityError("Canonical hexagram coverage must be exactly 1..64")
    if any(len(item.lines) != 6 or {line.line_position for line in item.lines} != set(range(1, 7)) for item in records):
        raise KnowledgeIntegrityError("Every canonical hexagram must contain line positions 1..6")
    if sum(len(item.lines) for item in records) != 384:
        raise KnowledgeIntegrityError("Canonical line coverage must be exactly 384")
    return records


@lru_cache(maxsize=1)
def load_interpretation_knowledge() -> tuple[dict[int, HexagramKnowledge], dict[tuple[int, int], LineKnowledge]]:
    payload = json.loads(_DATA.joinpath("interpretation_knowledge_v1.json").read_text(encoding="utf-8"))
    hexagrams = {item.king_wen_number: item for item in map(HexagramKnowledge.model_validate, payload["hexagrams"])}
    lines = {
        (item.king_wen_number, item.line_position): item
        for item in map(LineKnowledge.model_validate, payload["lines"])
    }
    if set(hexagrams) != set(range(1, 65)) or len(lines) != 384:
        raise KnowledgeIntegrityError("Interpretation knowledge must cover 64 hexagrams and 384 lines")
    return hexagrams, lines


def _validated(record: HexagramKnowledge | LineKnowledge):
    """Revalidate even pre-constructed objects before granting runtime access."""
    return type(record).model_validate(record.model_dump())


def _knowledge_evidence(record: HexagramKnowledge | LineKnowledge) -> KnowledgeEvidence:
    is_line = isinstance(record, LineKnowledge)
    prefix = {
        KnowledgeReviewStatus.APPROVED: "K",
        KnowledgeReviewStatus.REVIEWED: "R",
        KnowledgeReviewStatus.DRAFT: "D",
    }[record.review_status]
    evidence_id = f"{prefix}-{'L' if is_line else 'H'}-{record.king_wen_number}"
    if is_line:
        evidence_id += f"-{record.line_position}"
    source_type = {
        (KnowledgeReviewStatus.APPROVED, False): KnowledgeEvidenceSourceType.APPROVED_HEXAGRAM_KNOWLEDGE,
        (KnowledgeReviewStatus.APPROVED, True): KnowledgeEvidenceSourceType.APPROVED_LINE_KNOWLEDGE,
        (KnowledgeReviewStatus.REVIEWED, False): KnowledgeEvidenceSourceType.REVIEWED_HEXAGRAM_PREVIEW,
        (KnowledgeReviewStatus.REVIEWED, True): KnowledgeEvidenceSourceType.REVIEWED_LINE_PREVIEW,
        (KnowledgeReviewStatus.DRAFT, False): KnowledgeEvidenceSourceType.DRAFT_HEXAGRAM_PREVIEW,
        (KnowledgeReviewStatus.DRAFT, True): KnowledgeEvidenceSourceType.DRAFT_LINE_PREVIEW,
    }[(record.review_status, is_line)]
    return KnowledgeEvidence(
        evidence_id=evidence_id,
        source_type=source_type,
        king_wen_number=record.king_wen_number,
        line_position=record.line_position if is_line else None,
        review_status=record.review_status,
        core_theme=record.core_theme,
        literal_paraphrase=record.literal_paraphrase if is_line else None,
        favorable_conditions=record.favorable_conditions,
        risk_conditions=record.risk_conditions,
        action_tendency=record.action_tendency,
        prohibited_inferences=record.prohibited_inferences,
        polarity=record.evidence_direction,
        strength=record.evidence_strength,
        knowledge_version=record.knowledge_version,
        reviewer=record.reviewer,
        reviewed_at=record.reviewed_at,
        approved_by=record.approved_by,
        approved_at=record.approved_at,
        preview=record.review_status is not KnowledgeReviewStatus.APPROVED,
    )


def select_knowledge(
    chart: MeihuaChart,
    *,
    policy: KnowledgeAccessPolicy | None = None,
) -> KnowledgeSelection:
    policy = policy or KnowledgeAccessPolicy()
    canonical = {item.king_wen_number: item for item in load_canonical_texts()}[chart.base_hexagram.king_wen_number]
    canonical_line = canonical.lines[chart.moving_line - 1]
    hexagrams, lines = load_interpretation_knowledge()
    hex_record = _validated(hexagrams[chart.base_hexagram.king_wen_number])
    line_record = _validated(lines[(chart.base_hexagram.king_wen_number, chart.moving_line)])
    selected_hex = hex_record if hex_record.review_status in policy.allowed_statuses else None
    selected_line = line_record if line_record.review_status in policy.allowed_statuses else None
    knowledge_evidence = [_knowledge_evidence(item) for item in (selected_hex, selected_line) if item is not None]
    evidence_ids = [item.evidence_id for item in knowledge_evidence]
    notice = None
    if selected_hex is None or selected_line is None:
        notice = "当前卦或动爻只有经典原文，未使用经过人工批准的领域化解释。"
    return KnowledgeSelection(
        canonical_hexagram=canonical,
        canonical_line=canonical_line,
        hexagram_knowledge=selected_hex,
        line_knowledge=selected_line,
        allowed_knowledge_evidence_ids=evidence_ids,
        unreviewed_notice=notice,
        access_mode=policy.mode.value,
        is_preview=policy.is_preview,
        knowledge_evidence=knowledge_evidence,
    )
