"""Deterministic program-owned short references for provider-facing Evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .evidence_roles import evidence_role_constraints
from .models import InterpretationRequest, KnowledgeSelection, SynthesisResult

EVIDENCE_REFERENCE_CATALOG_VERSION = "MEIHUA_EVIDENCE_REFERENCE_CATALOG_V1"

ROLE_EXPLANATION = "EXPLANATION"
ROLE_ACTION_OPTION = "ACTION_OPTION"
ROLE_CONDITION = "CONDITION"
ROLE_REVIEW_QUESTION = "REVIEW_QUESTION"


class EvidenceReferenceError(ValueError):
    pass


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class EvidenceReferenceEntry:
    evidence_ref: str
    canonical_evidence_id: str
    allowed_roles: tuple[str, ...]
    evidence_source_type: str
    display_payload_hash: str
    safe_display_payload: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_ref": self.evidence_ref,
            "canonical_evidence_id": self.canonical_evidence_id,
            "allowed_roles": list(self.allowed_roles),
            "evidence_source_type": self.evidence_source_type,
            "display_payload_hash": self.display_payload_hash,
            "safe_display_payload": self.safe_display_payload,
        }


@dataclass(frozen=True, slots=True)
class EvidenceReferenceCatalog:
    catalog_version: str
    entries: tuple[EvidenceReferenceEntry, ...]
    catalog_sha256: str

    def to_payload(self) -> dict[str, object]:
        return {
            "catalog_version": self.catalog_version,
            "entries": [entry.to_payload() for entry in self.entries],
            "catalog_sha256": self.catalog_sha256,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "EvidenceReferenceCatalog":
        entries = tuple(
            EvidenceReferenceEntry(
                evidence_ref=str(item["evidence_ref"]),
                canonical_evidence_id=str(item["canonical_evidence_id"]),
                allowed_roles=tuple(item["allowed_roles"]),
                evidence_source_type=str(item["evidence_source_type"]),
                display_payload_hash=str(item["display_payload_hash"]),
                safe_display_payload=dict(item["safe_display_payload"]),
            )
            for item in payload["entries"]
        )
        catalog = cls(str(payload["catalog_version"]), entries, str(payload["catalog_sha256"]))
        catalog.validate_integrity()
        return catalog

    def validate_integrity(self) -> None:
        refs = [entry.evidence_ref for entry in self.entries]
        ids = [entry.canonical_evidence_id for entry in self.entries]
        if len(refs) != len(set(refs)) or len(ids) != len(set(ids)):
            raise EvidenceReferenceError("EVIDENCE_REFERENCE_CATALOG_NOT_ONE_TO_ONE")
        for entry in self.entries:
            if hashlib.sha256(_stable_json(entry.safe_display_payload).encode()).hexdigest() != entry.display_payload_hash:
                raise EvidenceReferenceError("EVIDENCE_REFERENCE_DISPLAY_HASH_MISMATCH")
        expected = _catalog_hash(self.entries)
        if expected != self.catalog_sha256:
            raise EvidenceReferenceError("EVIDENCE_REFERENCE_CATALOG_HASH_MISMATCH")

    def resolve(self, evidence_ref: str, *, required_role: str) -> str:
        entry = next((item for item in self.entries if item.evidence_ref == evidence_ref), None)
        if entry is None:
            raise EvidenceReferenceError("UNKNOWN_EVIDENCE_REF")
        if required_role not in entry.allowed_roles:
            raise EvidenceReferenceError("EVIDENCE_REF_ROLE_NOT_ALLOWED")
        return entry.canonical_evidence_id

    def refs_for_role(self, role: str) -> list[str]:
        return [entry.evidence_ref for entry in self.entries if role in entry.allowed_roles]


def _catalog_hash(entries: tuple[EvidenceReferenceEntry, ...]) -> str:
    material = [
        {
            "evidence_ref": entry.evidence_ref,
            "canonical_evidence_id": entry.canonical_evidence_id,
            "allowed_roles": list(entry.allowed_roles),
            "evidence_source_type": entry.evidence_source_type,
            "display_payload_hash": entry.display_payload_hash,
        }
        for entry in entries
    ]
    return hashlib.sha256(_stable_json(material).encode()).hexdigest()


def build_evidence_reference_catalog(
    request: InterpretationRequest,
    knowledge: KnowledgeSelection,
    synthesis: SynthesisResult,
) -> EvidenceReferenceCatalog:
    roles = evidence_role_constraints(request, knowledge, synthesis)
    role_sets = {
        ROLE_EXPLANATION: roles.explanation_ids,
        ROLE_ACTION_OPTION: roles.action_option_ids,
        ROLE_CONDITION: roles.condition_ids,
        ROLE_REVIEW_QUESTION: roles.review_question_ids,
    }
    chart = {item.evidence_id: item for item in request.chart.evidence}
    selected_knowledge = {
        item.evidence_id: item
        for item in knowledge.knowledge_evidence
        if item.evidence_id in roles.selected_knowledge_ids
    }
    canonical_ids = sorted(set().union(*role_sets.values()))
    entries = []
    for index, evidence_id in enumerate(canonical_ids, start=1):
        allowed_roles = tuple(role for role, ids in role_sets.items() if evidence_id in ids)
        if evidence_id in chart:
            item = chart[evidence_id]
            source_type = item.evidence_type.value
            display = {
                "fact": item.fact,
                "rule_statement": item.rule_statement,
                "polarity": item.polarity.value,
                "strength": item.strength.value,
            }
        elif evidence_id in selected_knowledge:
            item = selected_knowledge[evidence_id]
            source_type = item.source_type.value
            display = {
                "core_theme": item.core_theme,
                "literal_paraphrase": item.literal_paraphrase,
                "favorable_conditions": item.favorable_conditions,
                "risk_conditions": item.risk_conditions,
                "action_tendency": item.action_tendency,
                "prohibited_inferences": item.prohibited_inferences,
                "polarity": item.polarity.value if item.polarity else None,
                "strength": item.strength.value if item.strength else None,
                "review_status": item.review_status.value,
                "preview": item.preview,
            }
        else:
            raise EvidenceReferenceError("CATALOG_CANONICAL_ID_NOT_IN_CURRENT_ALLOWED_EVIDENCE")
        entries.append(
            EvidenceReferenceEntry(
                evidence_ref=f"EV{index:02d}",
                canonical_evidence_id=evidence_id,
                allowed_roles=allowed_roles,
                evidence_source_type=source_type,
                display_payload_hash=hashlib.sha256(_stable_json(display).encode()).hexdigest(),
                safe_display_payload=display,
            )
        )
    frozen = tuple(entries)
    catalog = EvidenceReferenceCatalog(EVIDENCE_REFERENCE_CATALOG_VERSION, frozen, _catalog_hash(frozen))
    catalog.validate_integrity()
    return catalog
