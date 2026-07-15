"""M1-A deterministic safe-Evidence projection with private/public hash separation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from abalo_iching.meihua.enums import EvidencePolarity, EvidenceStrength, EvidenceType

from .m1a_context import (
    M1AEvidenceRole,
    M1APrivateChartEvidence,
    M1AProgramContext,
    M1ASafeEvidenceProposition,
    freeze_safe_evidence_allowlist,
    m1a_program_hash,
)

M1A_EVIDENCE_CATALOG_VERSION = "MEIHUA_M1A_SAFE_EVIDENCE_CATALOG_V1"


class M1AEvidenceCatalogError(ValueError):
    pass


_DIRECTION_TEXT = {
    EvidencePolarity.POSITIVE: "该证据提供支持性信号，但不构成结果保证。",
    EvidencePolarity.NEGATIVE: "该证据提示阻碍或消耗风险，需要优先核实。",
    EvidencePolarity.MIXED: "该证据同时包含支持与限制，不能单向解释。",
    EvidencePolarity.NEUTRAL: "该证据用于界定条件或观察重点，不单独指向结果。",
}
_STRENGTH_TEXT = {
    EvidenceStrength.STRONG: "程序标记的影响强度较高。",
    EvidenceStrength.MEDIUM: "程序标记的影响强度为中等。",
    EvidenceStrength.WEAK: "程序标记的影响强度较弱，不宜过度推断。",
}
_CONDITION_PROJECTIONS = {
    "用方生助能力弱于体方当前承接能力，利向需要现实条件确认。": (
        "外部支持能否转化为用户可承接的现实条件仍需核实。"
    ),
    "体方需要持续具备控制和执行条件。": "用户是否持续具备执行和控制条件仍需核实。",
    "体方弱于用方，体克用的执行条件不足。": (
        "用户当前执行能力可能不足以覆盖外部要求，应先核实资源与承接能力。"
    ),
    "体强用弱可降低消耗风险，但不能翻转方向。": (
        "较强的自身承接能力可能降低消耗，但不能改变该证据方向。"
    ),
    "体方承压能力不弱于用方，可降低风险强度但不能翻转方向。": (
        "较强的自身承压能力可能降低风险强度，但不能改变该证据方向。"
    ),
    "比和表示同类互动，不因双方旺衰直接转成有利或不利。": (
        "同类互动本身不提供单向支持或阻碍，需要结合现实反馈。"
    ),
}
_FORBIDDEN_PUBLIC_TERMS = (
    "本卦",
    "互卦",
    "变卦",
    "动爻",
    "体卦",
    "用卦",
    "体方",
    "用方",
    "旺衰",
    "五行",
    "卦序",
    "rule_statement",
    "source_ref",
)


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _safe_condition(value: str) -> str:
    if value in _CONDITION_PROJECTIONS:
        return _CONDITION_PROJECTIONS[value]
    marker = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"存在一项需现实核实的程序条件（条件标记C-{marker}）。"


def _condition_map(context: M1AProgramContext) -> dict[str, tuple[str, ...]]:
    mapped: dict[str, list[str]] = {}
    for assessment in context.synthesis.relation_assessments:
        evidence_id = assessment.evidence_ids[0]
        values = [*assessment.conditions, *assessment.warnings]
        if values:
            mapped.setdefault(evidence_id, []).extend(_safe_condition(value) for value in values)
    return {key: tuple(dict.fromkeys(values)) for key, values in mapped.items()}


def _role_map(context: M1AProgramContext) -> dict[str, tuple[M1AEvidenceRole, ...]]:
    evidence_ids = [item.evidence_id for item in context.private_chart_evidence]
    action_ids = set(context.synthesis.supporting_evidence_ids) | set(context.synthesis.blocking_evidence_ids)
    if not action_ids:
        action_ids = {
            assessment.evidence_ids[0]
            for assessment in context.synthesis.relation_assessments
            if assessment.evidence_ids
        }
    condition_ids = set(_condition_map(context))
    result: dict[str, tuple[M1AEvidenceRole, ...]] = {}
    for evidence_id in evidence_ids:
        roles = [M1AEvidenceRole.EXPLANATION, M1AEvidenceRole.REVIEW_QUESTION]
        if evidence_id in action_ids:
            roles.append(M1AEvidenceRole.ACTION_OPTION)
        if evidence_id in condition_ids:
            roles.append(M1AEvidenceRole.CONDITION)
        result[evidence_id] = tuple(roles)
    return result


def _all_synthesis_ids(context: M1AProgramContext) -> set[str]:
    result = (
        set(context.synthesis.supporting_evidence_ids)
        | set(context.synthesis.blocking_evidence_ids)
        | set(context.synthesis.conflicting_evidence_ids)
    )
    for assessment in context.synthesis.relation_assessments:
        result.update(assessment.evidence_ids)
    return result


def _validate_private_source(context: M1AProgramContext) -> dict[str, M1APrivateChartEvidence]:
    private_by_id = {item.evidence_id: item for item in context.private_chart_evidence}
    if len(private_by_id) != len(context.private_chart_evidence):
        raise M1AEvidenceCatalogError("M1A_PRIVATE_EVIDENCE_IDS_NOT_UNIQUE")
    if not private_by_id:
        raise M1AEvidenceCatalogError("M1A_PRIVATE_EVIDENCE_EMPTY")
    for item in context.private_chart_evidence:
        if item.evidence_id.startswith(("K-", "R-", "D-")):
            raise M1AEvidenceCatalogError("M1A_KNOWLEDGE_EVIDENCE_FORBIDDEN")
        if type(item.evidence_type) is not EvidenceType:  # noqa: E721 - strict source boundary
            raise M1AEvidenceCatalogError("M1A_EVIDENCE_SOURCE_TYPE_INVALID")
        if not all((item.source_ref, item.fact, item.rule_statement, item.data_version)):
            raise M1AEvidenceCatalogError("M1A_EVIDENCE_SOURCE_INCOMPLETE")
    if _all_synthesis_ids(context) - set(private_by_id):
        raise M1AEvidenceCatalogError("M1A_SYNTHESIS_EVIDENCE_NOT_IN_CURRENT_CHART")
    return private_by_id


def _private_mapping_hash(
    item: M1APrivateChartEvidence,
    *,
    evidence_ref: str,
    program_hash: str,
) -> str:
    return _sha256(
        {
            "evidence_ref": evidence_ref,
            "canonical_evidence_id": item.evidence_id,
            "evidence_type": item.evidence_type.value,
            "source_ref": item.source_ref,
            "fact": item.fact,
            "rule_statement": item.rule_statement,
            "polarity": item.polarity.value,
            "strength": item.strength.value,
            "data_version": item.data_version,
            "program_hash": program_hash,
        }
    )


def _provider_entry_payload(item: M1ASafeEvidenceProposition) -> dict[str, object]:
    return {
        "evidence_ref": item.provider_evidence_ref,
        "safe_evidence_content": item.safe_evidence_content,
        "polarity": item.polarity.value,
        "strength": item.strength.value,
        "allowed_roles": [role.value for role in item.allowed_roles],
        "conditions": list(item.conditions),
    }


@dataclass(frozen=True, slots=True)
class M1ASafeEvidenceCatalog:
    catalog_version: str
    entries: tuple[M1ASafeEvidenceProposition, ...]
    provider_catalog_hash: str
    private_catalog_hash: str
    program_hash: str

    def to_provider_payload(self) -> dict[str, object]:
        return {
            "catalog_version": self.catalog_version,
            "catalog_sha256": self.provider_catalog_hash,
            "entries": [
                {**_provider_entry_payload(item), "display_payload_hash": item.provider_payload_hash}
                for item in self.entries
            ],
        }

    def validate_integrity(self, context: M1AProgramContext) -> None:
        private_by_id = _validate_private_source(context)
        if self.catalog_version != M1A_EVIDENCE_CATALOG_VERSION:
            raise M1AEvidenceCatalogError("M1A_EVIDENCE_CATALOG_VERSION_INVALID")
        if self.program_hash != m1a_program_hash(context):
            raise M1AEvidenceCatalogError("M1A_PROGRAM_HASH_MISMATCH")
        if set(private_by_id) != {item.canonical_evidence_id for item in self.entries}:
            raise M1AEvidenceCatalogError("M1A_CATALOG_NOT_CURRENT_CHART_EXACT_SET")
        try:
            freeze_safe_evidence_allowlist(self.entries)
        except (TypeError, ValueError) as exc:
            raise M1AEvidenceCatalogError(str(exc)) from exc
        for item in self.entries:
            private = private_by_id[item.canonical_evidence_id]
            expected_private = _private_mapping_hash(
                private,
                evidence_ref=item.provider_evidence_ref,
                program_hash=self.program_hash,
            )
            if expected_private != item.private_mapping_hash:
                raise M1AEvidenceCatalogError("M1A_PRIVATE_MAPPING_HASH_MISMATCH")
            if _sha256(_provider_entry_payload(item)) != item.provider_payload_hash:
                raise M1AEvidenceCatalogError("M1A_DISPLAY_PAYLOAD_HASH_MISMATCH")
            if any(term in item.safe_evidence_content for term in _FORBIDDEN_PUBLIC_TERMS):
                raise M1AEvidenceCatalogError("M1A_SAFE_EVIDENCE_LEAKS_CHART_STRUCTURE")
        provider_material = [
            {**_provider_entry_payload(item), "display_payload_hash": item.provider_payload_hash}
            for item in self.entries
        ]
        if _sha256(provider_material) != self.provider_catalog_hash:
            raise M1AEvidenceCatalogError("M1A_PROVIDER_CATALOG_HASH_MISMATCH")
        private_material = [
            {
                "evidence_ref": item.provider_evidence_ref,
                "canonical_evidence_id": item.canonical_evidence_id,
                "private_mapping_hash": item.private_mapping_hash,
            }
            for item in self.entries
        ]
        if _sha256({"program_hash": self.program_hash, "entries": private_material}) != self.private_catalog_hash:
            raise M1AEvidenceCatalogError("M1A_PRIVATE_CATALOG_HASH_MISMATCH")

    def resolve(self, evidence_ref: str, *, required_role: M1AEvidenceRole) -> str:
        item = next((entry for entry in self.entries if entry.provider_evidence_ref == evidence_ref), None)
        if item is None:
            raise M1AEvidenceCatalogError("M1A_UNKNOWN_EVIDENCE_REF")
        if required_role not in item.allowed_roles:
            raise M1AEvidenceCatalogError("M1A_EVIDENCE_ROLE_NOT_ALLOWED")
        return item.canonical_evidence_id

    def refs_for_role(self, role: M1AEvidenceRole) -> list[str]:
        return [item.provider_evidence_ref for item in self.entries if role in item.allowed_roles]


def build_m1a_evidence_catalog(context: M1AProgramContext) -> M1ASafeEvidenceCatalog:
    private_by_id = _validate_private_source(context)
    program_hash = m1a_program_hash(context)
    role_map = _role_map(context)
    conditions = _condition_map(context)
    entries: list[M1ASafeEvidenceProposition] = []
    for index, item in enumerate(context.private_chart_evidence, start=1):
        evidence_ref = f"M1AEV{index:02d}"
        safe_conditions = conditions.get(item.evidence_id, ())
        role_text = (
            "该证据可用于设计可逆行动或核实条件。"
            if M1AEvidenceRole.ACTION_OPTION in role_map[item.evidence_id]
            else "该证据仅用于解释和复盘观察。"
        )
        safe_content = " ".join(
            (
                f"安全证据{evidence_ref}。",
                _DIRECTION_TEXT[item.polarity],
                _STRENGTH_TEXT[item.strength],
                role_text,
                *safe_conditions,
            )
        )
        private_hash = _private_mapping_hash(item, evidence_ref=evidence_ref, program_hash=program_hash)
        display_material = {
            "evidence_ref": evidence_ref,
            "safe_evidence_content": safe_content,
            "polarity": item.polarity.value,
            "strength": item.strength.value,
            "allowed_roles": [role.value for role in role_map[item.evidence_id]],
            "conditions": list(safe_conditions),
        }
        entries.append(
            M1ASafeEvidenceProposition(
                canonical_evidence_id=item.evidence_id,
                provider_evidence_ref=evidence_ref,
                safe_evidence_content=safe_content,
                polarity=item.polarity,
                strength=item.strength,
                allowed_roles=role_map[item.evidence_id],
                conditions=safe_conditions,
                private_mapping_hash=private_hash,
                provider_payload_hash=_sha256(display_material),
            )
        )
    frozen = freeze_safe_evidence_allowlist(tuple(entries))
    provider_material = [
        {**_provider_entry_payload(item), "display_payload_hash": item.provider_payload_hash}
        for item in frozen
    ]
    private_material = [
        {
            "evidence_ref": item.provider_evidence_ref,
            "canonical_evidence_id": item.canonical_evidence_id,
            "private_mapping_hash": item.private_mapping_hash,
        }
        for item in frozen
    ]
    catalog = M1ASafeEvidenceCatalog(
        catalog_version=M1A_EVIDENCE_CATALOG_VERSION,
        entries=frozen,
        provider_catalog_hash=_sha256(provider_material),
        private_catalog_hash=_sha256({"program_hash": program_hash, "entries": private_material}),
        program_hash=program_hash,
    )
    catalog.validate_integrity(context)
    return catalog
