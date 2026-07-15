"""Deterministic M1-A Batch 3 candidate, fixture, and audit infrastructure."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_meihua_service_v2 import CONTRACT_VERSION_V2
from abalo_iching.application.sites_structured_question_v1 import (
    ALLOWED_GOALS,
    TEMPLATE_VERSION,
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)
from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.enums import (
    BodyUseRelation,
    EvidencePolarity,
    EvidenceStrength,
    MovingLineStage,
)
from abalo_iching.meihua.models import MeihuaChart, MeihuaInput
from abalo_iching.meihua.serialization import chart_to_dict

from .enums import ConclusionLevel, EvidenceSufficiency
from .m1a_context import M1AEvidenceRole, build_m1a_program_context, m1a_program_hash
from .m1a_evidence_catalog import (
    M1A_EVIDENCE_CATALOG_VERSION,
    M1ASafeEvidenceCatalog,
    build_m1a_evidence_catalog,
)
from .m1a_prompt_builder import M1A_PROMPT_VERSION
from .m1a_validator import M1A_VALIDATOR_VERSION
from .synthesis import (
    RULE_BOTH_FAVORABLE_CLEAR,
    RULE_BOTH_FAVORABLE_CONDITIONAL,
    RULE_BOTH_MIXED,
    RULE_BOTH_UNFAVORABLE_CLEAR,
    RULE_DIRECTION_CONFLICT,
    RULE_FAVORABLE_MIXED,
    RULE_MISSING_RELATION,
    RULE_UNFAVORABLE_NOT_CLEAR,
)

M1A_BATCH3_VERSION = "MEIHUA_M1A_BATCH3_V001"
M1A_FIXTURE_VERSION = "MEIHUA_M1A_FIXTURE_V001"
M1A_CLASSIFICATION_VERSION = "MEIHUA_M1A_CLASSIFICATION_V001"
M1A_EVIDENCE_AUDIT_VERSION = "MEIHUA_M1A_EVIDENCE_SEMANTIC_AUDIT_V001"
M1A_RUNNER_OUTPUT_SCHEMA_VERSION = "MEIHUA_M1A_RUNNER_OUTPUT_V001"
M1A_MANUAL_REVIEW_VERSION = "MEIHUA_M1A_MANUAL_REVIEW_V001"
FIXED_CAST_TIME = "2026-07-10T12:00:00+08:00"
FIXED_TIMEZONE = "Asia/Shanghai"
INPUT_NATURE = "SYNTHETIC"
SENTINEL_REPEAT_RUNS = 3

_SYNTHESIS_RULES = (
    RULE_BOTH_FAVORABLE_CLEAR,
    RULE_BOTH_FAVORABLE_CONDITIONAL,
    RULE_FAVORABLE_MIXED,
    RULE_DIRECTION_CONFLICT,
    RULE_BOTH_UNFAVORABLE_CLEAR,
    RULE_UNFAVORABLE_NOT_CLEAR,
    RULE_BOTH_MIXED,
    RULE_MISSING_RELATION,
)
_SAFE_REF_RE = re.compile(r"(?:安全证据\s*)?M1AEV\d+|Evidence\s*(?:引用)?\s*\d+", re.IGNORECASE)


class M1ABatch3Error(ValueError):
    """Fail-closed Batch 3 build or audit error."""


class M1ASemanticCollapseError(M1ABatch3Error):
    """Raised when safe Evidence appears to collapse across semantic metadata."""


def stable_json(value: object, *, indent: int | None = None) -> str:
    """Serialize repository-owned data deterministically."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
    )


def stable_sha256(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _primitive(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_primitive(item) for item in value]
    if isinstance(value, list):
        return [_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    return value


def _counter(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _candidate_id(numbers: tuple[int, int, int]) -> str:
    return f"M1A-CANDIDATE-{numbers[0]:02d}-{numbers[1]:02d}-{numbers[2]:02d}"


def candidate_question_id(numbers: tuple[int, int, int]) -> str:
    return f"m1a-b3-{numbers[0]}-{numbers[1]}-{numbers[2]}"


def _chart_hash(chart: MeihuaChart) -> str:
    return stable_sha256(chart_to_dict(chart))


def _unit_id(dimension: str, value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    return f"M1A3-CU-{dimension.upper().replace('_', '-')}-{normalized}"


@dataclass(frozen=True, slots=True)
class ClassificationDefinition:
    dimension: str
    value: str
    source_fields: tuple[str, ...]
    definition: str

    @property
    def unit_id(self) -> str:
        return _unit_id(self.dimension, self.value)


def _defined_classifications() -> tuple[ClassificationDefinition, ...]:
    definitions: list[ClassificationDefinition] = []

    def add(dimension: str, values: Iterable[str], source_fields: tuple[str, ...]) -> None:
        for value in values:
            definitions.append(
                ClassificationDefinition(
                    dimension=dimension,
                    value=value,
                    source_fields=source_fields,
                    definition=f"{dimension} equals the authoritative value {value}.",
                )
            )

    add("conclusion_level", (item.value for item in ConclusionLevel), ("synthesis.conclusion_level",))
    add(
        "evidence_sufficiency",
        (item.value for item in EvidenceSufficiency),
        ("synthesis.evidence_sufficiency",),
    )
    add(
        "initial_relation",
        (item.value for item in BodyUseRelation),
        ("chart.initial_body_use_relation",),
    )
    add(
        "changed_relation",
        (item.value for item in BodyUseRelation),
        ("chart.changed_body_use_relation",),
    )
    add("moving_line_stage", (item.value for item in MovingLineStage), ("chart.moving_line_stage",))
    add("synthesis_rule", _SYNTHESIS_RULES, ("synthesis.synthesis_rule_ids",))
    add(
        "evidence_polarity",
        (item.value for item in EvidencePolarity),
        ("catalog.entries[].polarity",),
    )
    add(
        "evidence_strength",
        (item.value for item in EvidenceStrength),
        ("catalog.entries[].strength",),
    )
    add("evidence_role", (item.value for item in M1AEvidenceRole), ("catalog.entries[].allowed_roles",))
    return tuple(sorted(definitions, key=lambda item: item.unit_id))


def _candidate_classification_values(
    chart: MeihuaChart,
    catalog: M1ASafeEvidenceCatalog,
    synthesis_payload: dict[str, Any],
) -> dict[str, set[str]]:
    relation_assessments = synthesis_payload["relation_assessments"]
    direction_pair = "|".join(
        f"{item['phase']}:{item['direction']}" for item in relation_assessments
    )
    values: dict[str, set[str]] = {
        "conclusion_level": {synthesis_payload["conclusion_level"]},
        "evidence_sufficiency": {synthesis_payload["evidence_sufficiency"]},
        "initial_relation": {chart.initial_body_use_relation.value},
        "changed_relation": {chart.changed_body_use_relation.value},
        "direction_pair": {direction_pair},
        "moving_line_stage": {chart.moving_line_stage.value},
        "synthesis_rule": set(synthesis_payload["synthesis_rule_ids"]),
        "modifier_rule": {
            rule
            for assessment in relation_assessments
            for rule in assessment["modifier_rule_ids"]
        },
        "evidence_role": {
            role.value for entry in catalog.entries for role in entry.allowed_roles
        },
        "evidence_polarity": {entry.polarity.value for entry in catalog.entries},
        "evidence_strength": {entry.strength.value for entry in catalog.entries},
    }
    return values


def _classification_tags(values: dict[str, set[str]]) -> tuple[str, ...]:
    return tuple(
        sorted(
            _unit_id(dimension, value)
            for dimension, dimension_values in values.items()
            for value in dimension_values
        )
    )


def build_candidate(numbers: tuple[int, int, int]) -> dict[str, Any]:
    """Build one deterministic candidate from the frozen three-number input."""
    first, second, third = numbers
    if not (1 <= first <= 8 and 1 <= second <= 8 and 1 <= third <= 6):
        raise M1ABatch3Error("M1A_BATCH3_NUMBERS_OUT_OF_RANGE")
    cast_at = datetime.fromisoformat(FIXED_CAST_TIME).astimezone(ZoneInfo(FIXED_TIMEZONE))
    chart = cast_meihua(
        MeihuaInput(
            first,
            second,
            third,
            cast_at,
            FIXED_TIMEZONE,
            candidate_question_id(numbers),
        )
    )
    context = build_m1a_program_context(chart)
    catalog = build_m1a_evidence_catalog(context)
    synthesis = context.synthesis.model_dump(mode="json")
    classification_values = _candidate_classification_values(chart, catalog, synthesis)
    tags = _classification_tags(classification_values)
    relation_assessments = synthesis["relation_assessments"]
    safe_entries = [
        {
            "canonical_evidence_id": item.canonical_evidence_id,
            "provider_evidence_ref": item.provider_evidence_ref,
            "safe_evidence_content": item.safe_evidence_content,
            "polarity": item.polarity.value,
            "strength": item.strength.value,
            "allowed_roles": [role.value for role in item.allowed_roles],
            "conditions": list(item.conditions),
        }
        for item in catalog.entries
    ]
    payload: dict[str, Any] = {
        "candidate_id": _candidate_id(numbers),
        "synthetic_numbers": list(numbers),
        "cast_time": chart.input.cast_at.isoformat(),
        "timezone": chart.input.timezone_name,
        "input_nature": INPUT_NATURE,
        "chart_hash": _chart_hash(chart),
        "program_hash": m1a_program_hash(context),
        "provider_catalog_hash": catalog.provider_catalog_hash,
        "private_catalog_hash": catalog.private_catalog_hash,
        "evidence_direction_state": "|".join(
            f"{item['phase']}:{item['direction']}" for item in relation_assessments
        ),
        "evidence_sufficiency": synthesis["evidence_sufficiency"],
        "conclusion_level": synthesis["conclusion_level"],
        "initial_body_use_relation": chart.initial_body_use_relation.value,
        "changed_body_use_relation": chart.changed_body_use_relation.value,
        "initial_direction": relation_assessments[0]["direction"],
        "changed_direction": relation_assessments[1]["direction"],
        "relation_assessments": relation_assessments,
        "moving_line_stage": chart.moving_line_stage.value,
        "strength_modifiers": sorted(
            {
                modifier
                for item in relation_assessments
                for modifier in item["modifier_rule_ids"]
            }
        ),
        "synthesis_rule_ids": synthesis["synthesis_rule_ids"],
        "classification_tags": list(tags),
        "evidence_role_distribution": _counter(
            role.value for item in catalog.entries for role in item.allowed_roles
        ),
        "evidence_polarity_distribution": _counter(item.polarity.value for item in catalog.entries),
        "evidence_strength_distribution": _counter(item.strength.value for item in catalog.entries),
        "safe_evidence_count": len(catalog.entries),
        "condition_count": sum(len(item.conditions) for item in catalog.entries),
        "safe_evidence": safe_entries,
        "versions": {
            "batch3_version": M1A_BATCH3_VERSION,
            "classification_version": M1A_CLASSIFICATION_VERSION,
            "engine_version": context.engine_version,
            "rule_version": context.rule_version,
            "trigram_data_version": context.trigram_data_version,
            "hexagram_data_version": context.hexagram_data_version,
            "catalog_version": catalog.catalog_version,
        },
    }
    payload["base_fixture_signature"] = stable_sha256(
        {
            "classification_version": M1A_CLASSIFICATION_VERSION,
            "classification_tags": payload["classification_tags"],
            "versions": payload["versions"],
        }
    )
    return payload


def generate_candidates() -> list[dict[str, Any]]:
    """Enumerate 8 x 8 x 6 candidates in explicit lexicographic order."""
    candidates = [
        build_candidate((first, second, third))
        for first in range(1, 9)
        for second in range(1, 9)
        for third in range(1, 7)
    ]
    numbers = [tuple(item["synthetic_numbers"]) for item in candidates]
    if len(candidates) != 384 or len(set(numbers)) != 384:
        raise M1ABatch3Error("M1A_BATCH3_CANDIDATE_SET_INVALID")
    return candidates


def build_coverage_matrix(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Report observed units and defined single-axis units without a Cartesian expansion."""
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dynamic_definitions: dict[str, ClassificationDefinition] = {}
    for candidate in candidates:
        for unit_id in candidate["classification_tags"]:
            by_unit[unit_id].append(candidate)
        for assessment in candidate["relation_assessments"]:
            pair = candidate["evidence_direction_state"]
            pair_id = _unit_id("direction_pair", pair)
            dynamic_definitions[pair_id] = ClassificationDefinition(
                "direction_pair",
                pair,
                ("synthesis.relation_assessments[].phase", "synthesis.relation_assessments[].direction"),
                "Ordered initial and changed directions emitted by the authoritative relation assessments.",
            )
            for modifier in assessment["modifier_rule_ids"]:
                modifier_id = _unit_id("modifier_rule", modifier)
                dynamic_definitions[modifier_id] = ClassificationDefinition(
                    "modifier_rule",
                    modifier,
                    ("synthesis.relation_assessments[].modifier_rule_ids",),
                    "An authoritative modifier rule emitted by RelationAssessor.",
                )
    definitions = {item.unit_id: item for item in _defined_classifications()}
    definitions.update(dynamic_definitions)
    units: list[dict[str, Any]] = []
    for unit_id, definition in sorted(definitions.items()):
        matches = by_unit.get(unit_id, [])
        units.append(
            {
                "unit_id": unit_id,
                "dimension": definition.dimension,
                "value": definition.value,
                "definition": definition.definition,
                "source_fields": list(definition.source_fields),
                "reachable": bool(matches),
                "reachable_candidate_count": len(matches),
                "representative_candidate": matches[0]["candidate_id"] if matches else None,
                "coverage_status": "COVERABLE" if matches else "DEFINED_NOT_OBSERVED",
            }
        )
    return {
        "classification_version": M1A_CLASSIFICATION_VERSION,
        "candidate_count": len(candidates),
        "matrix_policy": "DEFINED_SINGLE_AXIS_AND_OBSERVED_COMPOSITES_ONLY",
        "undefined_combinations_excluded": True,
        "units": units,
        "reachable_unit_count": sum(item["reachable"] for item in units),
        "defined_not_observed_unit_count": sum(not item["reachable"] for item in units),
    }


def normalize_safe_evidence_content(value: str) -> str:
    """Remove Evidence numbering, formatting, whitespace, and punctuation deterministically."""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _SAFE_REF_RE.sub("", normalized)
    return "".join(
        character.casefold()
        for character in normalized
        if not unicodedata.category(character).startswith(("P", "Z"))
        and not character.isspace()
    )


def audit_safe_evidence(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit substantive safe-Evidence equivalence after removing display identities."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        for item in candidate["safe_evidence"]:
            content = normalize_safe_evidence_content(item["safe_evidence_content"])
            groups[content].append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "canonical_evidence_id": item["canonical_evidence_id"],
                    "provider_evidence_ref": item["provider_evidence_ref"],
                    "polarity": item["polarity"],
                    "strength": item["strength"],
                    "allowed_roles": item["allowed_roles"],
                    "conditions": item["conditions"],
                }
            )
    equivalence_classes: list[dict[str, Any]] = []
    suspicious: list[str] = []
    for index, (content, members) in enumerate(sorted(groups.items()), start=1):
        metadata_keys = {
            stable_json(
                {
                    "polarity": item["polarity"],
                    "strength": item["strength"],
                    "allowed_roles": item["allowed_roles"],
                    "conditions": item["conditions"],
                }
            )
            for item in members
        }
        class_id = f"M1A3-EQ-{index:03d}"
        is_suspicious = len(metadata_keys) > 1
        if is_suspicious:
            suspicious.append(class_id)
        equivalence_classes.append(
            {
                "equivalence_class_id": class_id,
                "normalized_substantive_content": content,
                "member_count": len(members),
                "canonical_evidence": sorted(
                    {
                        f"{item['candidate_id']}:{item['canonical_evidence_id']}"
                        for item in members
                    }
                ),
                "polarity_identical": len({item["polarity"] for item in members}) == 1,
                "strength_identical": len({item["strength"] for item in members}) == 1,
                "roles_identical": len({tuple(item["allowed_roles"]) for item in members}) == 1,
                "conditions_identical": len(
                    {tuple(item["conditions"]) for item in members}
                )
                == 1,
                "classification": "SUSPECTED_OVER_COLLAPSE" if is_suspicious else "REASONABLE_EQUIVALENCE",
                "reason": (
                    "Substantive content matches but authoritative semantic metadata differs."
                    if is_suspicious
                    else "Substantive content and polarity, strength, roles, and conditions all match."
                ),
            }
        )
    report = {
        "audit_version": M1A_EVIDENCE_AUDIT_VERSION,
        "normalization_steps": [
            "REMOVE_M1AEV_NUMBER",
            "REMOVE_EVIDENCE_REFERENCE_NUMBER",
            "UNICODE_NFKC",
            "REMOVE_WHITESPACE_AND_PUNCTUATION",
            "CASEFOLD",
        ],
        "candidate_count": len(candidates),
        "evidence_observation_count": sum(len(item["safe_evidence"]) for item in candidates),
        "equivalence_class_count": len(equivalence_classes),
        "suspicious_class_ids": suspicious,
        "severe_collapse_detected": bool(suspicious),
        "equivalence_classes": equivalence_classes,
    }
    if suspicious:
        raise M1ASemanticCollapseError(
            "M1A_BATCH3_SUSPECTED_SAFE_EVIDENCE_OVER_COLLAPSE:" + ",".join(suspicious)
        )
    return report


def _legal_domain_goals() -> list[tuple[QuestionDomain, DecisionGoal]]:
    return [
        (domain, goal)
        for domain in QuestionDomain
        for goal in sorted(ALLOWED_GOALS[domain], key=lambda item: item.value)
    ]


def _greedy_candidates(
    candidates: list[dict[str, Any]], reachable_units: set[str]
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    uncovered = set(reachable_units)
    remaining = list(candidates)
    selected: list[dict[str, Any]] = []
    reasons: dict[str, list[str]] = {}
    while uncovered:
        ranked = sorted(
            remaining,
            key=lambda item: (
                -len(set(item["classification_tags"]) & uncovered),
                tuple(item["synthetic_numbers"]),
            ),
        )
        chosen = ranked[0]
        newly_covered = sorted(set(chosen["classification_tags"]) & uncovered)
        if not newly_covered:
            raise M1ABatch3Error("M1A_BATCH3_REACHABLE_UNIT_WITHOUT_CANDIDATE")
        selected.append(chosen)
        reasons[chosen["candidate_id"]] = newly_covered
        uncovered.difference_update(newly_covered)
        remaining.remove(chosen)
    return selected, reasons


def select_fixtures(
    candidates: list[dict[str, Any]], coverage_matrix: dict[str, Any]
) -> list[dict[str, Any]]:
    """Select deterministic greedy coverage, then satisfy the 17 V2 combination floor."""
    reachable_units = {
        item["unit_id"] for item in coverage_matrix["units"] if item["reachable"]
    }
    selected, greedy_reasons = _greedy_candidates(candidates, reachable_units)
    selected_ids = {item["candidate_id"] for item in selected}
    for candidate in candidates:
        if len(selected) >= len(_legal_domain_goals()):
            break
        if candidate["candidate_id"] not in selected_ids:
            selected.append(candidate)
            selected_ids.add(candidate["candidate_id"])
    combinations = _legal_domain_goals()
    horizons = list(TimeHorizon)
    fixtures: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected):
        domain, goal = combinations[index % len(combinations)]
        horizon = horizons[index % len(horizons)]
        normalized_question, question_template_version = generate_structured_question(
            domain, goal, horizon
        )
        newly_covered = greedy_reasons.get(candidate["candidate_id"], [])
        selection_reason = (
            "GREEDY_MAX_UNCOVERED_CLASSIFICATION_UNITS"
            if newly_covered
            else "V2_DOMAIN_GOAL_BASE_FIXTURE_FLOOR"
        )
        fixtures.append(
            {
                "fixture_id": f"M1A-V001-{index + 1:03d}",
                "fixture_version": M1A_FIXTURE_VERSION,
                "candidate_id": candidate["candidate_id"],
                "synthetic_numbers": candidate["synthetic_numbers"],
                "cast_time": candidate["cast_time"],
                "timezone": candidate["timezone"],
                "question_domain": domain.value,
                "decision_goal": goal.value,
                "time_horizon": horizon.value,
                "normalized_question": normalized_question,
                "question_template_version": question_template_version,
                "contract_version": CONTRACT_VERSION_V2,
                "chart_hash": candidate["chart_hash"],
                "program_hash": candidate["program_hash"],
                "provider_catalog_hash": candidate["provider_catalog_hash"],
                "private_catalog_hash": candidate["private_catalog_hash"],
                "classification_tags": candidate["classification_tags"],
                "base_fixture_signature": candidate["base_fixture_signature"],
                "selection_reason": selection_reason,
                "covered_units": newly_covered,
                "safe_evidence_short_references": [
                    {
                        "evidence_ref": item["provider_evidence_ref"],
                        "roles": item["allowed_roles"],
                        "polarity": item["polarity"],
                        "strength": item["strength"],
                        "condition_count": len(item["conditions"]),
                    }
                    for item in candidate["safe_evidence"]
                ],
                "safe_evidence_count": candidate["safe_evidence_count"],
                "condition_count": candidate["condition_count"],
                "engine_version": candidate["versions"]["engine_version"],
                "rule_version": candidate["versions"]["rule_version"],
                "trigram_data_version": candidate["versions"]["trigram_data_version"],
                "hexagram_data_version": candidate["versions"]["hexagram_data_version"],
                "catalog_version": M1A_EVIDENCE_CATALOG_VERSION,
                "prompt_version": M1A_PROMPT_VERSION,
                "validator_version": M1A_VALIDATOR_VERSION,
                "manual_review_status": "UNREVIEWED",
                "sentinel": False,
            }
        )
    if len(fixtures) < 17:
        raise M1ABatch3Error("M1A_BATCH3_FIXTURE_FLOOR_NOT_MET")
    return fixtures


def _mock_replay_hash(fixture: dict[str, Any]) -> str:
    return stable_sha256(
        {
            "fixture_id": fixture["fixture_id"],
            "provider": "MOCK",
            "replay_version": M1A_FIXTURE_VERSION,
            "outcome": "VALID_STATIC_REPLAY",
        }
    )


def build_sentinels(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sentinels: list[dict[str, Any]] = []
    for domain in QuestionDomain:
        fixture = next(item for item in fixtures if item["question_domain"] == domain.value)
        fixture["sentinel"] = True
        configuration_hash = stable_sha256(
            {
                "fixture_id": fixture["fixture_id"],
                "repeat_runs": SENTINEL_REPEAT_RUNS,
                "provider": "MOCK",
            }
        )
        sentinels.append(
            {
                "fixture_id": fixture["fixture_id"],
                "question_domain": fixture["question_domain"],
                "decision_goal": fixture["decision_goal"],
                "time_horizon": fixture["time_horizon"],
                "synthetic_numbers": fixture["synthetic_numbers"],
                "program_hash": fixture["program_hash"],
                "catalog_hash": fixture["provider_catalog_hash"],
                "configuration_hash": configuration_hash,
                "mock_replay_output_hash": _mock_replay_hash(fixture),
                "repeat_run_count": SENTINEL_REPEAT_RUNS,
                "principle_action_conflict_status": "NOT_DETECTED_IN_FIXED_MOCK_REPLAY",
                "evidence_direction_changed": False,
                "program_ownership_changed": False,
            }
        )
    return sentinels


def manual_review_template() -> dict[str, Any]:
    criteria = [
        "program_ai_ownership_fidelity",
        "evidence_fidelity",
        "evidence_direction_fidelity",
        "evidence_strength_fidelity",
        "mixed_evidence_handling",
        "domain_relevance",
        "decision_goal_relevance",
        "real_world_verifiability",
        "action_controllability",
        "action_reversibility",
        "non_coercion",
        "uncertainty_expression",
        "restraint",
        "readability",
        "mind_reading_present",
        "outcome_guarantee_present",
        "irreversible_instruction_present",
        "repeat_output_principle_conflict",
        "safe_evidence_vagueness",
        "human_notes",
    ]
    return {
        "template_version": M1A_MANUAL_REVIEW_VERSION,
        "default_review_status": "UNREVIEWED",
        "scientific_scoring_standard_claimed": False,
        "release_threshold_frozen": False,
        "criteria": [{"criterion": item, "value": None} for item in criteria],
    }


def fixture_schema() -> dict[str, Any]:
    required = [
        "fixture_id",
        "fixture_version",
        "synthetic_numbers",
        "cast_time",
        "timezone",
        "question_domain",
        "decision_goal",
        "time_horizon",
        "normalized_question",
        "question_template_version",
        "contract_version",
        "chart_hash",
        "program_hash",
        "provider_catalog_hash",
        "private_catalog_hash",
        "classification_tags",
        "base_fixture_signature",
        "selection_reason",
        "covered_units",
        "safe_evidence_short_references",
        "engine_version",
        "rule_version",
        "trigram_data_version",
        "hexagram_data_version",
        "catalog_version",
        "prompt_version",
        "validator_version",
        "manual_review_status",
        "sentinel",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:abalo:m1a:fixture:v001",
        "type": "object",
        "required": required,
        "properties": {
            "fixture_id": {"type": "string", "pattern": "^M1A-V001-[0-9]{3}$"},
            "fixture_version": {"const": M1A_FIXTURE_VERSION},
            "synthetic_numbers": {
                "type": "array",
                "prefixItems": [
                    {"type": "integer", "minimum": 1, "maximum": 8},
                    {"type": "integer", "minimum": 1, "maximum": 8},
                    {"type": "integer", "minimum": 1, "maximum": 6},
                ],
                "minItems": 3,
                "maxItems": 3,
            },
            "cast_time": {"const": FIXED_CAST_TIME},
            "timezone": {"const": FIXED_TIMEZONE},
            "manual_review_status": {"const": "UNREVIEWED"},
            "sentinel": {"type": "boolean"},
        },
        "additionalProperties": True,
    }


def runner_output_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:abalo:m1a:runner-output:v001",
        "type": "object",
        "required": [
            "schema_version",
            "batch_id",
            "runner_version",
            "configuration_hash",
            "results",
            "summary",
            "narrative_release_status",
            "should_charge",
            "formal_report_persistence_allowed",
            "closed_beta_allowed",
        ],
        "properties": {
            "schema_version": {"const": M1A_RUNNER_OUTPUT_SCHEMA_VERSION},
            "narrative_release_status": {"const": "UNVERIFIED"},
            "should_charge": {"const": False},
            "formal_report_persistence_allowed": {"const": False},
            "closed_beta_allowed": {"const": False},
        },
        "additionalProperties": True,
    }


def build_batch3_bundle() -> dict[str, Any]:
    candidates = generate_candidates()
    coverage = build_coverage_matrix(candidates)
    evidence_audit = audit_safe_evidence(candidates)
    fixtures = select_fixtures(candidates, coverage)
    sentinels = build_sentinels(fixtures)
    covered = {unit for fixture in fixtures for unit in fixture["covered_units"]}
    reachable = {item["unit_id"] for item in coverage["units"] if item["reachable"]}
    if covered != reachable:
        raise M1ABatch3Error("M1A_BATCH3_FIXTURE_COVERAGE_INCOMPLETE")
    return {
        "manifest": {
            "batch3_version": M1A_BATCH3_VERSION,
            "input_nature": INPUT_NATURE,
            "candidate_count": len(candidates),
            "fixture_count": len(fixtures),
            "fixed_cast_time": FIXED_CAST_TIME,
            "timezone": FIXED_TIMEZONE,
            "domain_goal_combination_count": len(_legal_domain_goals()),
            "time_horizons": [item.value for item in TimeHorizon],
            "sentinel_count": len(sentinels),
            "external_model_called": False,
            "narrative_release_status": "UNVERIFIED",
            "should_charge": False,
            "formal_report_persistence_allowed": False,
            "closed_beta_allowed": False,
        },
        "candidates": candidates,
        "coverage_matrix": coverage,
        "evidence_equivalence_audit": evidence_audit,
        "fixtures": fixtures,
        "sentinels": sentinels,
        "manual_review_template": manual_review_template(),
        "fixture_schema": fixture_schema(),
        "runner_output_schema": runner_output_schema(),
    }


def write_batch3_bundle(output_dir: Path) -> dict[str, Any]:
    """Write all Batch 3 assets with stable names, ordering, and final newlines."""
    bundle = build_batch3_bundle()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "manifest.json": bundle["manifest"],
        "candidates.json": bundle["candidates"],
        "coverage_matrix.json": bundle["coverage_matrix"],
        "evidence_equivalence_audit.json": bundle["evidence_equivalence_audit"],
        "fixtures.json": bundle["fixtures"],
        "sentinels.json": bundle["sentinels"],
        "manual_review_template.json": bundle["manual_review_template"],
        "fixture.schema.json": bundle["fixture_schema"],
        "runner_output.schema.json": bundle["runner_output_schema"],
    }
    for name, payload in files.items():
        (output_dir / name).write_text(stable_json(payload, indent=2) + "\n", encoding="utf-8")
    return bundle
