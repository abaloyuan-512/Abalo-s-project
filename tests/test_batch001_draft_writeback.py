from __future__ import annotations

import json
from pathlib import Path

from abalo_iching.interpretation.enums import KnowledgeAccessMode, KnowledgeReviewStatus
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, load_interpretation_knowledge, select_knowledge

ROOT = Path(__file__).resolve().parents[1]


def test_batch001_exact_status_counts_and_no_audit_identity():
    hexagrams, lines = load_interpretation_knowledge()
    records = [*hexagrams.values(), *lines.values()]
    assert sum(item.review_status is KnowledgeReviewStatus.DRAFT for item in records) == 16
    assert sum(item.review_status is KnowledgeReviewStatus.CANONICAL_ONLY for item in records) == 432
    assert sum(item.review_status is KnowledgeReviewStatus.REVIEWED for item in records) == 0
    assert sum(item.review_status is KnowledgeReviewStatus.APPROVED for item in records) == 0
    assert all(item.reviewer is None and item.reviewed_at is None for item in records)
    assert all(item.approved_by is None and item.approved_at is None for item in records)


def test_production_never_selects_batch001_drafts(phase2_chart):
    assert select_knowledge(phase2_chart).knowledge_evidence == []


def test_internal_preview_uses_d_evidence_for_batch001(phase2_chart):
    selection = select_knowledge(
        phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW)
    )
    assert selection.is_preview is True
    assert selection.knowledge_evidence
    assert all(item.evidence_id.startswith("D-") and item.preview for item in selection.knowledge_evidence)


def test_derived_source_is_ai_proposal_not_human_signoff():
    payload = json.loads(
        (ROOT / "review_data/meihua/batch_001/batch_001_editorial_drafts.json").read_text(encoding="utf-8")
    )
    assert payload["proposal_type"] == "AI_EDITORIAL_PROPOSAL_NOT_HUMAN_SIGNOFF"
    assert len(payload["records"]) == 16
    assert all(item["formal_target_status"] == "DRAFT" for item in payload["records"])
    assert all(item["review_notes"] == "AI editorial proposal; not human-reviewed" for item in payload["records"])
