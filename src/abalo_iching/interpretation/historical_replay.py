"""Strict versioned compatibility for offline replay of legacy V3 output only."""

from __future__ import annotations

import json
import re

from .evidence_references import (
    EvidenceReferenceCatalog,
    ROLE_ACTION_OPTION,
    ROLE_CONDITION,
    ROLE_EXPLANATION,
    ROLE_REVIEW_QUESTION,
)
from .models import AINarrativeDraftContent, InterpretationRequest
from .narrative_assembly import assemble_narrative

HISTORICAL_REPLAY_COMPAT_VERSION = "MEIHUA_V3_RESPONSE_REPLAY_COMPAT_V2"
LEGACY_EVIDENCE_RESOLVER_VERSION = "MEIHUA_LEGACY_EVIDENCE_RESOLVER_V1"
LEGACY_EVIDENCE_DEDUPLICATOR_VERSION = "MEIHUA_LEGACY_EVIDENCE_DEDUPLICATOR_V1"
LEGACY_MOVING_LINE_RESOLUTION = "LEGACY_UNAMBIGUOUS_MOVING_LINE_EXPANSION"
LEGACY_CANONICAL_ALIAS_COLLAPSE = "LEGACY_CANONICAL_ALIAS_COLLAPSE"
_FIELDS = (
    "plain_language_explanation",
    "real_world_advice",
    "conditions_that_change_outcome",
    "review_questions",
)
_LEGACY_LINE = re.compile(r"^D-L-(\d{1,2})$")
_FIELD_ROLES = {
    "plain_language_explanation": ROLE_EXPLANATION,
    "real_world_advice": ROLE_ACTION_OPTION,
    "conditions_that_change_outcome": ROLE_CONDITION,
    "review_questions": ROLE_REVIEW_QUESTION,
}


class LegacyEvidenceResolutionError(ValueError):
    pass


def resolve_legacy_evidence_id(
    original_id: str,
    request: InterpretationRequest,
    catalog: EvidenceReferenceCatalog,
) -> tuple[str, dict[str, object] | None]:
    allowed = {entry.canonical_evidence_id for entry in catalog.entries}
    if original_id in allowed:
        return original_id, None
    match = _LEGACY_LINE.fullmatch(original_id)
    if match is None:
        raise LegacyEvidenceResolutionError("LEGACY_EVIDENCE_ID_NOT_EXACT_OR_ALLOWED")
    number = int(match.group(1))
    if number != request.chart.base_hexagram.king_wen_number:
        raise LegacyEvidenceResolutionError("LEGACY_LINE_HEXAGRAM_MISMATCH")
    candidate = f"D-L-{number}-{request.chart.moving_line}"
    candidates = [item for item in allowed if item == candidate]
    if len(candidates) != 1:
        raise LegacyEvidenceResolutionError("LEGACY_LINE_RESOLUTION_NOT_UNIQUE")
    audit = {
        "original_evidence_id": original_id,
        "resolved_evidence_id": candidate,
        "resolution_type": LEGACY_MOVING_LINE_RESOLUTION,
        "case_id": request.question_id,
        "resolver_version": LEGACY_EVIDENCE_RESOLVER_VERSION,
        "model_text_changed": False,
    }
    return candidate, audit


def replay_legacy_v3_output_text_with_audit(
    raw_text: str,
    request: InterpretationRequest,
    catalog: EvidenceReferenceCatalog,
):
    """Resolve exact legacy IDs, translate to refs, and assemble fixed metadata."""
    legacy = json.loads(raw_text)
    ref_by_id = {entry.canonical_evidence_id: entry.evidence_ref for entry in catalog.entries}
    resolution_audit = []
    deduplication_audit = []
    draft_payload = {}
    for field in _FIELDS:
        draft_claims = []
        for claim_index, claim in enumerate(legacy[field]):
            resolved_items = []
            for original_id in claim["evidence_ids"]:
                canonical_id, audit = resolve_legacy_evidence_id(original_id, request, catalog)
                if canonical_id not in ref_by_id:
                    raise LegacyEvidenceResolutionError("RESOLVED_CANONICAL_ID_NOT_IN_CATALOG")
                evidence_ref = ref_by_id[canonical_id]
                catalog.resolve(evidence_ref, required_role=_FIELD_ROLES[field])
                resolved_items.append((original_id, canonical_id, evidence_ref, audit))
                if audit is not None:
                    resolution_audit.append(audit)
            seen = set()
            kept = []
            removed_by_canonical = {}
            kept_original_by_canonical = {}
            for original_id, canonical_id, evidence_ref, audit in resolved_items:
                if canonical_id in seen:
                    removed_by_canonical.setdefault(canonical_id, []).append(original_id)
                    continue
                seen.add(canonical_id)
                kept.append((original_id, canonical_id, evidence_ref, audit))
                kept_original_by_canonical[canonical_id] = original_id
            for canonical_id, removed in removed_by_canonical.items():
                kept_item = next(item for item in kept if item[1] == canonical_id)
                deduplication_audit.append(
                    {
                        "case_id": request.question_id,
                        "claim_section": field,
                        "claim_index": claim_index,
                        "original_evidence_ids": list(claim["evidence_ids"]),
                        "resolved_evidence_ids_before_dedup": [item[1] for item in resolved_items],
                        "canonical_evidence_ids_after_dedup": [item[1] for item in kept],
                        "kept_original_reference": kept_original_by_canonical[canonical_id],
                        "removed_original_references": removed,
                        "resolved_canonical_id": canonical_id,
                        "resolution_type": (
                            kept_item[3]["resolution_type"] if kept_item[3] is not None else "EXACT_CANONICAL_ID"
                        ),
                        "deduplication_type": LEGACY_CANONICAL_ALIAS_COLLAPSE,
                        "resolver_version": LEGACY_EVIDENCE_RESOLVER_VERSION,
                        "deduplication_version": LEGACY_EVIDENCE_DEDUPLICATOR_VERSION,
                        "model_text_changed": False,
                        "original_response_changed": False,
                    }
                )
            refs = [item[2] for item in kept]
            draft_claims.append(
                {
                    "text": claim["text"],
                    "evidence_refs": refs,
                    "subject_scope": claim["subject_scope"],
                }
            )
        draft_payload[field] = draft_claims
    draft = AINarrativeDraftContent.model_validate(draft_payload)
    return assemble_narrative(draft, catalog), resolution_audit, deduplication_audit


def replay_legacy_v3_output_text(
    raw_text: str,
    request: InterpretationRequest,
    catalog: EvidenceReferenceCatalog,
):
    assembled, _, _ = replay_legacy_v3_output_text_with_audit(raw_text, request, catalog)
    return assembled
