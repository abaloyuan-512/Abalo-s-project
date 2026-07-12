"""Deterministically attach program-owned metadata to provider narrative drafts."""

from __future__ import annotations

from .enums import EpistemicBasis, NarrativeKind
from .models import (
    AINarrativeClaim,
    AINarrativeContent,
    AINarrativeDraftClaim,
    AINarrativeDraftContent,
)
from .evidence_references import (
    EvidenceReferenceCatalog,
    ROLE_ACTION_OPTION,
    ROLE_CONDITION,
    ROLE_EXPLANATION,
    ROLE_REVIEW_QUESTION,
)

PROVIDER_SCHEMA_VERSION = "MEIHUA_AI_NARRATIVE_DRAFT_SCHEMA_V3"
NARRATIVE_ASSEMBLY_VERSION = "MEIHUA_NARRATIVE_ASSEMBLY_V1"

_FIXED_METADATA = {
    "plain_language_explanation": (NarrativeKind.EXPLANATION, EpistemicBasis.CHART_EVIDENCE, ROLE_EXPLANATION),
    "real_world_advice": (NarrativeKind.ACTION_OPTION, EpistemicBasis.ACTION_OPTION, ROLE_ACTION_OPTION),
    "conditions_that_change_outcome": (NarrativeKind.CONDITION_TO_VERIFY, EpistemicBasis.UNCERTAINTY, ROLE_CONDITION),
    "review_questions": (NarrativeKind.REVIEW_QUESTION, EpistemicBasis.UNCERTAINTY, ROLE_REVIEW_QUESTION),
}


def _assemble_claim(
    claim: AINarrativeDraftClaim,
    narrative_kind: NarrativeKind,
    epistemic_basis: EpistemicBasis,
    required_role: str,
    catalog: EvidenceReferenceCatalog,
) -> AINarrativeClaim:
    return AINarrativeClaim(
        text=claim.text,
        evidence_ids=[catalog.resolve(ref, required_role=required_role) for ref in claim.evidence_refs],
        subject_scope=claim.subject_scope,
        narrative_kind=narrative_kind,
        epistemic_basis=epistemic_basis,
    )


def assemble_narrative(
    draft: AINarrativeDraftContent | dict[str, object],
    catalog: EvidenceReferenceCatalog | dict[str, object],
) -> AINarrativeContent:
    parsed = draft if isinstance(draft, AINarrativeDraftContent) else AINarrativeDraftContent.model_validate(draft)
    resolved_catalog = catalog if isinstance(catalog, EvidenceReferenceCatalog) else EvidenceReferenceCatalog.from_payload(catalog)
    payload = {}
    for field, (kind, basis, role) in _FIXED_METADATA.items():
        payload[field] = [_assemble_claim(claim, kind, basis, role, resolved_catalog) for claim in getattr(parsed, field)]
    return AINarrativeContent.model_validate(payload)
