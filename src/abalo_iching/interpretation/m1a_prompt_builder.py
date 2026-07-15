"""Build and fail-closed validate the M1-A Provider prompt whitelist."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from importlib.resources import files

from .m1a_context import M1AEvidenceRole, M1AIntakeView, M1AProgramContext, m1a_program_hash
from .m1a_evidence_catalog import M1ASafeEvidenceCatalog
from .models import PromptPackage

M1A_PROMPT_VERSION = "MEIHUA_M1A_PROMPT_V1"
M1A_PROVIDER_SCHEMA_VERSION = "MEIHUA_M1A_NARRATIVE_DRAFT_SCHEMA_V1"
M1A_NARRATIVE_ASSEMBLY_VERSION = "MEIHUA_M1A_NARRATIVE_ASSEMBLY_V1"
M1A_CONTRACT_VERSION = "MEIHUA_M1A_PROVIDER_CONTRACT_V1"

_PAYLOAD_FIELDS = {
    "task",
    "prompt_version",
    "provider_schema_version",
    "narrative_assembly_version",
    "m1a_contract_version",
    "structured_intake",
    "normalized_question",
    "evidence_reference_catalog",
    "evidence_role_constraints",
    "domain_narrative_constraints",
    "program_owned_constraints",
    "version_snapshot",
    "repair_context",
}
_FORBIDDEN_KEYS = {
    "numbers",
    "first_number",
    "second_number",
    "third_number",
    "chart",
    "meihua_chart",
    "meihua_input",
    "base_hexagram",
    "mutual_hexagram",
    "changed_hexagram",
    "moving_line",
    "body_trigram",
    "initial_use_trigram",
    "changed_use_trigram",
    "body_use",
    "seasonal_strength",
    "five_elements",
    "conclusion",
    "conclusion_level",
    "deterministic_conclusion",
    "program_timing",
    "real_world_context",
    "canonical_evidence_id",
    "evidence_type",
    "source_ref",
    "rule_statement",
    "fact",
    "private_mapping_hash",
    "private_catalog_hash",
}
_INTAKE_FIELDS = {
    "question_id",
    "question_domain",
    "decision_goal",
    "time_horizon",
    "normalized_question",
    "question_template_version",
    "contract_version",
    "is_synthetic",
}

DOMAIN_NARRATIVE_CONSTRAINTS: dict[str, dict[str, list[str]]] = {
    "WORK_CAREER": {
        "allowed_focus": ["工作准备", "求职流程", "能力验证", "沟通反馈", "可逆试验"],
        "prohibited": ["保证录用、升职或收入", "读心招聘方", "替用户作出辞职决定"],
    },
    "PROJECT_COOPERATION": {
        "allowed_focus": ["项目推进", "分工", "承诺", "资源", "沟通边界"],
        "prohibited": ["投资证券借贷融资担保收益回本建议", "读心合作方", "保证项目成功"],
    },
    "RELATIONSHIP_COMMUNICATION": {
        "allowed_focus": ["用户自身沟通", "边界", "投入", "观察", "复盘"],
        "prohibited": ["判断对方是否爱用户", "第三方心理或未来行为结论", "操控监视跟踪强迫"],
    },
    "PERSONAL_PLANNING": {
        "allowed_focus": ["目标安排", "优先级", "精力分配", "节奏", "自身承诺与边界"],
        "prohibited": ["医疗心理诊断", "投资借贷收益建议", "法律或宿命结论", "替用户作出不可逆决定"],
    },
}

GOAL_NARRATIVE_CONSTRAINTS: dict[str, str] = {
    "IDENTIFY_OBSTACLES": "聚焦可核实的阻力、支持条件和现实信号。",
    "PLAN_NEXT_STEP": "聚焦用户可控、可逆的下一步。",
    "PREPARE_COMMUNICATION": "聚焦沟通准备、表达、询问与反馈。",
    "ADJUST_COMMITMENT_BOUNDARIES": "聚焦用户自身投入、承诺和边界调整。",
    "OBSERVE_VERIFY_SIGNALS": "聚焦观察、核实、记录与复盘信号。",
}


class M1APromptPayloadError(ValueError):
    pass


def _enum_value(value: object) -> str:
    resolved = getattr(value, "value", None)
    if not isinstance(resolved, str):
        raise M1APromptPayloadError("M1A_STRUCTURED_INTAKE_TYPE_INVALID")
    return resolved


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def load_m1a_system_prompt() -> str:
    return files("abalo_iching.interpretation.prompts").joinpath("meihua_m1a_v1.txt").read_text(encoding="utf-8")


class M1APromptBuilder:
    def build(
        self,
        intake: M1AIntakeView,
        context: M1AProgramContext,
        catalog: M1ASafeEvidenceCatalog,
        *,
        repair_errors: list[str] | None = None,
    ) -> PromptPackage:
        self._validate_intake(intake)
        catalog.validate_integrity(context)
        program_hash = m1a_program_hash(context)
        if program_hash != catalog.program_hash:
            raise M1APromptPayloadError("M1A_PROGRAM_HASH_CHANGED_BEFORE_PROMPT")
        domain = _enum_value(intake.question_domain)
        goal = _enum_value(intake.decision_goal)
        horizon = _enum_value(intake.time_horizon)
        if domain not in DOMAIN_NARRATIVE_CONSTRAINTS or goal not in GOAL_NARRATIVE_CONSTRAINTS:
            raise M1APromptPayloadError("M1A_PRODUCT_SEMANTICS_NOT_VALIDATED")
        repair_context = None
        if repair_errors:
            repair_context = {
                "error_codes": sorted(set(repair_errors)),
                "only_modify_ai_narrative": True,
                "must_preserve_program_hash": program_hash,
                "must_preserve_catalog_sha256": catalog.provider_catalog_hash,
                "attempt": 2,
            }
        payload = {
            "task": "Generate only the four AI narrative draft sections using supplied short Evidence references.",
            "prompt_version": M1A_PROMPT_VERSION,
            "provider_schema_version": M1A_PROVIDER_SCHEMA_VERSION,
            "narrative_assembly_version": M1A_NARRATIVE_ASSEMBLY_VERSION,
            "m1a_contract_version": M1A_CONTRACT_VERSION,
            "structured_intake": {
                "question_domain": domain,
                "decision_goal": goal,
                "time_horizon": horizon,
                "question_template_version": intake.question_template_version,
                "contract_version": intake.contract_version,
                "is_synthetic": intake.is_synthetic,
            },
            "normalized_question": intake.normalized_question,
            "evidence_reference_catalog": catalog.to_provider_payload(),
            "evidence_role_constraints": {
                "explanation_refs": catalog.refs_for_role(M1AEvidenceRole.EXPLANATION),
                "action_option_refs": catalog.refs_for_role(M1AEvidenceRole.ACTION_OPTION),
                "condition_refs": catalog.refs_for_role(M1AEvidenceRole.CONDITION),
                "review_question_refs": catalog.refs_for_role(M1AEvidenceRole.REVIEW_QUESTION),
            },
            "domain_narrative_constraints": {
                **DOMAIN_NARRATIVE_CONSTRAINTS[domain],
                "decision_goal_constraint": GOAL_NARRATIVE_CONSTRAINTS[goal],
            },
            "program_owned_constraints": {
                "program_hash": program_hash,
                "use_only_supplied_evidence": True,
                "must_not_output_program_facts": True,
                "must_not_output_program_conclusion": True,
                "must_not_output_time_judgment": True,
                "must_not_change_evidence_direction_or_strength": True,
                "authoritative_metadata_added_by_program": True,
            },
            "version_snapshot": {
                "engine_version": context.engine_version,
                "rule_version": context.rule_version,
                "trigram_data_version": context.trigram_data_version,
                "hexagram_data_version": context.hexagram_data_version,
                "calendar_provider": context.calendar_provider,
                "safe_evidence_catalog_version": catalog.catalog_version,
            },
            "repair_context": repair_context,
        }
        self.validate_payload(payload, context=context, catalog=catalog, is_repair=bool(repair_errors))
        return PromptPackage(
            system_prompt=load_m1a_system_prompt(),
            user_payload_json=_stable_json(payload),
            prompt_version=M1A_PROMPT_VERSION,
        )

    def validate_payload(
        self,
        payload: dict[str, object],
        *,
        context: M1AProgramContext,
        catalog: M1ASafeEvidenceCatalog,
        is_repair: bool,
    ) -> None:
        if set(payload) != _PAYLOAD_FIELDS:
            raise M1APromptPayloadError("M1A_PROVIDER_PAYLOAD_NOT_EXACT_WHITELIST")
        keys = {key.lower() for key in _walk_keys(payload)}
        if keys & _FORBIDDEN_KEYS or any("knowledge" in key for key in keys):
            raise M1APromptPayloadError("M1A_PROVIDER_PAYLOAD_FORBIDDEN_FIELD")
        repair_context = payload["repair_context"]
        if (repair_context is not None) is not is_repair:
            raise M1APromptPayloadError("M1A_REPAIR_CONTEXT_ATTEMPT_MISMATCH")
        if m1a_program_hash(context) != catalog.program_hash:
            raise M1APromptPayloadError("M1A_PROGRAM_HASH_CHANGED_DURING_PROMPT")
        catalog.validate_integrity(context)
        provider_catalog = payload["evidence_reference_catalog"]
        if provider_catalog != catalog.to_provider_payload():
            raise M1APromptPayloadError("M1A_PROVIDER_CATALOG_PAYLOAD_MISMATCH")
        assert isinstance(provider_catalog, dict)
        for entry in provider_catalog["entries"]:
            assert isinstance(entry, dict)
            display_material = {key: value for key, value in entry.items() if key != "display_payload_hash"}
            expected = hashlib.sha256(_stable_json(display_material).encode("utf-8")).hexdigest()
            if expected != entry["display_payload_hash"]:
                raise M1APromptPayloadError("M1A_PROVIDER_DISPLAY_HASH_NOT_REPRODUCIBLE")

    @staticmethod
    def _validate_intake(intake: M1AIntakeView) -> None:
        if not is_dataclass(intake) or {item.name for item in fields(intake)} != _INTAKE_FIELDS:
            raise M1APromptPayloadError("M1A_INTAKE_NOT_EXACT_NARROW_BOUNDARY")
        boundary_validator = getattr(intake, "validate_m1a_boundary", None)
        if not callable(boundary_validator):
            raise M1APromptPayloadError("M1A_INTAKE_SELF_VALIDATION_UNAVAILABLE")
        try:
            validation_result = boundary_validator()
        except (TypeError, ValueError) as exc:
            raise M1APromptPayloadError("M1A_INTAKE_SELF_VALIDATION_FAILED") from exc
        if validation_result is not None:
            raise M1APromptPayloadError("M1A_INTAKE_SELF_VALIDATION_INVALID_RESULT")
        if intake.is_synthetic is not True:
            raise M1APromptPayloadError("M1A_REAL_INPUT_FORBIDDEN")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                intake.question_id,
                intake.normalized_question,
                intake.question_template_version,
                intake.contract_version,
            )
        ):
            raise M1APromptPayloadError("M1A_INTAKE_TEXT_OR_VERSION_INVALID")
