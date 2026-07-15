"""Knowledge-free M1-A program context and future safe-Evidence interface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from abalo_iching.meihua.enums import EvidencePolarity, EvidenceStrength, EvidenceType
from abalo_iching.meihua.models import MeihuaChart

from .models import SynthesisResult
from .synthesis import ConclusionSynthesizer


class M1AEvidenceRole(StrEnum):
    """Narrative uses that a future deterministic projection may permit."""

    EXPLANATION = "EXPLANATION"
    ACTION_OPTION = "ACTION_OPTION"
    CONDITION = "CONDITION"
    REVIEW_QUESTION = "REVIEW_QUESTION"


@dataclass(frozen=True, slots=True)
class M1APrivateChartEvidence:
    """Program-private canonical Evidence; never a Provider payload."""

    evidence_id: str
    evidence_type: EvidenceType
    source_ref: str
    fact: str
    rule_statement: str
    polarity: EvidencePolarity
    strength: EvidenceStrength
    data_version: str


@dataclass(frozen=True, slots=True)
class M1ASafeEvidenceProposition:
    """Batch 1 interface only; no proposition templates are implemented here."""

    canonical_evidence_id: str
    provider_evidence_ref: str
    safe_evidence_content: str
    polarity: EvidencePolarity
    strength: EvidenceStrength
    allowed_roles: tuple[M1AEvidenceRole, ...]
    conditions: tuple[str, ...]
    private_mapping_hash: str
    provider_payload_hash: str

    def __post_init__(self) -> None:
        if not self.canonical_evidence_id or not self.provider_evidence_ref:
            raise ValueError("safe Evidence requires private and Provider-visible references")
        if not self.safe_evidence_content.strip():
            raise ValueError("safe Evidence content must not be empty")
        if type(self.polarity) is not EvidencePolarity:  # noqa: E721 - strict boundary by design
            raise TypeError("safe Evidence polarity must remain program-owned")
        if type(self.strength) is not EvidenceStrength:  # noqa: E721 - strict boundary by design
            raise TypeError("safe Evidence strength must remain program-owned")
        if (
            type(self.allowed_roles) is not tuple  # noqa: E721 - strict boundary by design
            or not self.allowed_roles
            or not all(type(item) is M1AEvidenceRole for item in self.allowed_roles)
            or len(set(self.allowed_roles)) != len(self.allowed_roles)
        ):
            raise ValueError("safe Evidence requires unique allowed roles")
        if type(self.conditions) is not tuple or not all(  # noqa: E721 - strict boundary by design
            isinstance(item, str) and item.strip() for item in self.conditions
        ):
            raise TypeError("safe Evidence conditions must be immutable non-empty strings")
        for value in (self.private_mapping_hash, self.provider_payload_hash):
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError("safe Evidence hashes must be lowercase SHA-256 values")


def freeze_safe_evidence_allowlist(
    propositions: tuple[M1ASafeEvidenceProposition, ...],
) -> tuple[M1ASafeEvidenceProposition, ...]:
    """Enforce one-to-one interface identity without defining Batch 2 templates."""
    canonical_ids = [item.canonical_evidence_id for item in propositions]
    provider_refs = [item.provider_evidence_ref for item in propositions]
    safe_contents = [item.safe_evidence_content for item in propositions]
    if len(set(canonical_ids)) != len(canonical_ids):
        raise ValueError("each canonical Evidence may be projected at most once")
    if len(set(provider_refs)) != len(provider_refs):
        raise ValueError("each safe Evidence reference must be unique")
    if len(set(safe_contents)) != len(safe_contents):
        raise ValueError("different Evidence must not collapse to identical generic content")
    return propositions


@dataclass(frozen=True, slots=True)
class M1AProgramContext:
    """Program-only deterministic state; this object must not be serialized to a Provider."""

    synthesis: SynthesisResult
    private_chart_evidence: tuple[M1APrivateChartEvidence, ...]
    provider_evidence_allowlist: tuple[M1ASafeEvidenceProposition, ...]
    rule_version: str
    trigram_data_version: str
    hexagram_data_version: str
    calendar_provider: str
    engine_version: str


def build_m1a_program_context(chart: MeihuaChart) -> M1AProgramContext:
    """Use a Chart transiently, retaining no Chart, MeihuaInput, numbers, or Knowledge."""
    private_evidence = tuple(
        M1APrivateChartEvidence(
            evidence_id=item.evidence_id,
            evidence_type=item.evidence_type,
            source_ref=item.source_ref,
            fact=item.fact,
            rule_statement=item.rule_statement,
            polarity=item.polarity,
            strength=item.strength,
            data_version=item.data_version,
        )
        for item in chart.evidence
    )
    versions = chart.versions
    return M1AProgramContext(
        synthesis=ConclusionSynthesizer().synthesize_chart(chart),
        private_chart_evidence=private_evidence,
        provider_evidence_allowlist=freeze_safe_evidence_allowlist(()),
        rule_version=versions.rule_version,
        trigram_data_version=versions.trigram_data_version,
        hexagram_data_version=versions.hexagram_data_version,
        calendar_provider=versions.calendar_provider,
        engine_version=versions.engine_version,
    )
