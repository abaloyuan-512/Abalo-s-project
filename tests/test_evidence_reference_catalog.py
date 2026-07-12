import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.run_meihua_live_eval_v001 import DATASET, _request

from abalo_iching.interpretation.enums import KnowledgeAccessMode
from abalo_iching.interpretation.evidence_references import (
    EVIDENCE_REFERENCE_CATALOG_VERSION,
    EvidenceReferenceCatalog,
    EvidenceReferenceEntry,
    EvidenceReferenceError,
    ROLE_ACTION_OPTION,
    ROLE_EXPLANATION,
    build_evidence_reference_catalog,
)
from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.historical_replay import (
    LEGACY_CANONICAL_ALIAS_COLLAPSE,
    LEGACY_EVIDENCE_DEDUPLICATOR_VERSION,
    LEGACY_EVIDENCE_RESOLVER_VERSION,
    LEGACY_MOVING_LINE_RESOLUTION,
    LegacyEvidenceResolutionError,
    resolve_legacy_evidence_id,
    replay_legacy_v3_output_text_with_audit,
)
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.models import AINarrativeDraftContent
from abalo_iching.interpretation.narrative_assembly import assemble_narrative
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.interpretation.validators import InterpretationValidator


def case_context(case_id="CASE-001", mode=KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW):
    case = next(x for x in json.loads(DATASET.read_text(encoding="utf-8"))["cases"] if x["case_id"] == case_id)
    request = _request(case)
    knowledge = select_knowledge(request.chart, policy=KnowledgeAccessPolicy(mode))
    synthesis = ConclusionSynthesizer().synthesize(request.chart, knowledge)
    catalog = build_evidence_reference_catalog(request, knowledge, synthesis)
    return request, knowledge, synthesis, catalog


def test_catalog_is_deterministic_one_to_one_and_versioned():
    request, knowledge, synthesis, first = case_context()
    second = build_evidence_reference_catalog(request, knowledge, synthesis)
    assert first == second
    assert first.catalog_version == EVIDENCE_REFERENCE_CATALOG_VERSION == "MEIHUA_EVIDENCE_REFERENCE_CATALOG_V1"
    assert [x.evidence_ref for x in first.entries] == [f"EV{i:02d}" for i in range(1, len(first.entries) + 1)]
    assert len({x.evidence_ref for x in first.entries}) == len(first.entries)
    assert len({x.canonical_evidence_id for x in first.entries}) == len(first.entries)


def test_unknown_and_wrong_role_refs_are_rejected(valid_narrative_draft, phase2_evidence_catalog):
    payload = valid_narrative_draft.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_refs"] = ["EV99"]
    with pytest.raises(EvidenceReferenceError, match="UNKNOWN_EVIDENCE_REF"):
        assemble_narrative(payload, phase2_evidence_catalog)
    explanation_only = next(
        item.evidence_ref for item in phase2_evidence_catalog.entries
        if ROLE_EXPLANATION in item.allowed_roles and ROLE_ACTION_OPTION not in item.allowed_roles
    )
    payload = valid_narrative_draft.model_dump(mode="json")
    payload["real_world_advice"][0]["evidence_refs"] = [explanation_only]
    with pytest.raises(EvidenceReferenceError, match="EVIDENCE_REF_ROLE_NOT_ALLOWED"):
        assemble_narrative(payload, phase2_evidence_catalog)


def test_mapped_unknown_canonical_id_is_still_rejected(valid_narrative_draft, phase2_request, phase2_knowledge, phase2_synthesis):
    draft = valid_narrative_draft.model_dump(mode="json")
    _, _, _, valid_catalog = case_context()
    target_ref = draft["plain_language_explanation"][0]["evidence_refs"][0]
    entries = tuple(replace(item, canonical_evidence_id="E999") if item.evidence_ref == target_ref else item for item in valid_catalog.entries)
    catalog = EvidenceReferenceCatalog(EVIDENCE_REFERENCE_CATALOG_VERSION, entries, "test-bypasses-integrity-to-exercise-validator")
    assembled = assemble_narrative(draft, catalog)
    with pytest.raises(InterpretationValidationError, match="unknown_evidence_id"):
        InterpretationValidator().validate(assembled, phase2_request, phase2_knowledge, phase2_synthesis)


def test_production_catalog_excludes_draft_knowledge():
    _, _, _, preview = case_context("CASE-001", KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW)
    _, _, _, production = case_context("CASE-001", KnowledgeAccessMode.PRODUCTION)
    assert any(x.canonical_evidence_id.startswith("D-") for x in preview.entries)
    assert all(not x.canonical_evidence_id.startswith("D-") for x in production.entries)


def test_case007_legacy_line_expands_exactly_and_audits():
    request, _, _, catalog = case_context("CASE-007")
    resolved, audit = resolve_legacy_evidence_id("D-L-34", request, catalog)
    assert resolved == "D-L-34-4"
    assert audit == {
        "original_evidence_id": "D-L-34",
        "resolved_evidence_id": "D-L-34-4",
        "resolution_type": LEGACY_MOVING_LINE_RESOLUTION,
        "case_id": "CASE-007",
        "resolver_version": LEGACY_EVIDENCE_RESOLVER_VERSION,
        "model_text_changed": False,
    }


def test_case007_alias_and_canonical_are_deduplicated_in_original_order():
    raw_text = Path("tests/fixtures/case007_attempt1_legacy_alias.json").read_text(encoding="utf-8")
    legacy = json.loads(raw_text)
    request, knowledge, synthesis, catalog = case_context("CASE-007")
    assembled, resolution_audit, dedup_audit = replay_legacy_v3_output_text_with_audit(raw_text, request, catalog)
    InterpretationValidator().validate(assembled, request, knowledge, synthesis)
    assert len(dedup_audit) == 1
    audit = dedup_audit[0]
    assert audit["claim_section"] == "review_questions" and audit["claim_index"] == 1
    assert audit["original_evidence_ids"] == ["D-L-34", "D-L-34-4"]
    assert audit["resolved_evidence_ids_before_dedup"] == ["D-L-34-4", "D-L-34-4"]
    assert audit["canonical_evidence_ids_after_dedup"] == ["D-L-34-4"]
    assert audit["kept_original_reference"] == "D-L-34"
    assert audit["removed_original_references"] == ["D-L-34-4"]
    assert audit["resolved_canonical_id"] == "D-L-34-4"
    assert audit["deduplication_type"] == LEGACY_CANONICAL_ALIAS_COLLAPSE
    assert audit["deduplication_version"] == LEGACY_EVIDENCE_DEDUPLICATOR_VERSION
    assert audit["model_text_changed"] is False and audit["original_response_changed"] is False
    assert [claim.text for claim in assembled.review_questions] == [claim["text"] for claim in legacy["review_questions"]]
    assert resolution_audit[0]["original_evidence_id"] == "D-L-34"


def test_different_canonical_ids_are_not_deduplicated():
    raw_text = Path("tests/fixtures/case007_attempt1_legacy_alias.json").read_text(encoding="utf-8")
    request, _, _, catalog = case_context("CASE-007")
    assembled, _, audits = replay_legacy_v3_output_text_with_audit(raw_text, request, catalog)
    first_claim = assembled.plain_language_explanation[0]
    assert len(first_claim.evidence_ids) == len(set(first_claim.evidence_ids))
    assert all(audit["resolved_canonical_id"] == "D-L-34-4" for audit in audits)


def test_legacy_resolver_rejects_no_candidate_hex_mismatch_and_typos():
    request, _, _, catalog = case_context("CASE-007")
    with pytest.raises(LegacyEvidenceResolutionError, match="HEXAGRAM_MISMATCH"):
        resolve_legacy_evidence_id("D-L-33", request, catalog)
    with pytest.raises(LegacyEvidenceResolutionError, match="NOT_EXACT_OR_ALLOWED"):
        resolve_legacy_evidence_id("D-L-34-x", request, catalog)
    with pytest.raises(LegacyEvidenceResolutionError, match="NOT_EXACT_OR_ALLOWED"):
        resolve_legacy_evidence_id("E0O", request, catalog)
    _, _, _, production = case_context("CASE-007", KnowledgeAccessMode.PRODUCTION)
    with pytest.raises(LegacyEvidenceResolutionError, match="NOT_UNIQUE"):
        resolve_legacy_evidence_id("D-L-34", request, production)


def test_duplicate_catalog_candidate_is_rejected_before_resolution(phase2_evidence_catalog):
    entry = phase2_evidence_catalog.entries[0]
    duplicate = EvidenceReferenceEntry("EV99", entry.canonical_evidence_id, entry.allowed_roles, entry.evidence_source_type, entry.display_payload_hash, entry.safe_display_payload)
    forged = EvidenceReferenceCatalog(phase2_evidence_catalog.catalog_version, (*phase2_evidence_catalog.entries, duplicate), phase2_evidence_catalog.catalog_sha256)
    with pytest.raises(EvidenceReferenceError, match="NOT_ONE_TO_ONE"):
        forged.validate_integrity()


def test_realtime_assembler_has_no_legacy_resolver_dependency(valid_narrative_draft, phase2_evidence_catalog, monkeypatch):
    import abalo_iching.interpretation.historical_replay as replay_module
    monkeypatch.setattr(replay_module, "resolve_legacy_evidence_id", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy resolver called")))
    assert assemble_narrative(valid_narrative_draft, phase2_evidence_catalog)


def test_realtime_duplicate_refs_remain_rejected(valid_narrative_draft):
    payload = valid_narrative_draft.model_dump(mode="json")
    ref = payload["plain_language_explanation"][0]["evidence_refs"][0]
    payload["plain_language_explanation"][0]["evidence_refs"] = [ref, ref]
    with pytest.raises(Exception, match="Evidence refs must be unique"):
        AINarrativeDraftContent.model_validate(payload)


def test_new_draft_accepts_refs_and_rejects_canonical_ids(valid_narrative_draft):
    assert "evidence_refs" in type(valid_narrative_draft.plain_language_explanation[0]).model_fields
    assert "evidence_ids" not in type(valid_narrative_draft.plain_language_explanation[0]).model_fields
    payload = valid_narrative_draft.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_ids"] = ["E01"]
    with pytest.raises(Exception):
        AINarrativeDraftContent.model_validate(payload)
