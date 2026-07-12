"""Build a static system prompt and a narrow narrative-only JSON payload."""

from __future__ import annotations

import json
from importlib.resources import files

from .evidence_references import (
    ROLE_ACTION_OPTION,
    ROLE_CONDITION,
    ROLE_EXPLANATION,
    ROLE_REVIEW_QUESTION,
    build_evidence_reference_catalog,
)
from .models import InterpretationRequest, KnowledgeSelection, PromptPackage, SynthesisResult
from .narrative_assembly import NARRATIVE_ASSEMBLY_VERSION, PROVIDER_SCHEMA_VERSION

PROMPT_VERSION = "MEIHUA_INTERPRETATION_PROMPT_V5"
REPAIR_PROMPT_VERSION = "MEIHUA_REPAIR_PROMPT_V4"


def load_system_prompt() -> str:
    return files("abalo_iching.interpretation.prompts").joinpath("meihua_interpretation_v1.txt").read_text(
        encoding="utf-8"
    )


class PromptBuilder:
    def build(
        self,
        request: InterpretationRequest,
        knowledge: KnowledgeSelection,
        synthesis: SynthesisResult,
        *,
        repair_errors: list[str] | None = None,
    ) -> PromptPackage:
        catalog = build_evidence_reference_catalog(request, knowledge, synthesis)
        repair_errors = repair_errors or []
        repair_context = None
        if repair_errors:
            repair_context = {
                "error_codes": repair_errors,
                "only_modify_ai_narrative_fields": True,
                "must_not_modify": [
                    "program_facts",
                    "program_conclusion",
                    "timing",
                    "evidence_direction",
                ],
            }
            if "action_evidence_role_mismatch" in repair_errors:
                repair_context.update(
                    {
                        "error_field": "real_world_advice",
                        "allowed_action_option_refs": catalog.refs_for_role(ROLE_ACTION_OPTION),
                        "forbidden_evidence_rule": (
                            "Use only allowed_action_option_refs. Do not output canonical Evidence IDs."
                        ),
                    }
                )
        payload = {
            "prompt_version": PROMPT_VERSION,
            "task": "Generate AINarrativeDraftContent only. Each claim contains only text, evidence_refs and subject_scope.",
            "provider_schema_version": PROVIDER_SCHEMA_VERSION,
            "narrative_assembly_version": NARRATIVE_ASSEMBLY_VERSION,
            "user_data_untrusted": {
                "normalized_question": request.normalized_question,
                "decision_goal": request.decision_goal,
                "real_world_context": request.real_world_context,
                "question_domain": request.question_domain.value,
            },
            "evidence_reference_catalog": {
                "catalog_version": catalog.catalog_version,
                "catalog_sha256": catalog.catalog_sha256,
                "entries": [
                    {
                        "evidence_ref": item.evidence_ref,
                        "allowed_roles": list(item.allowed_roles),
                        "evidence_source_type": item.evidence_source_type,
                        "display_payload_hash": item.display_payload_hash,
                        "safe_evidence_content": item.safe_display_payload,
                    }
                    for item in catalog.entries
                ],
            },
            "evidence_role_constraints": {
                "explanation_refs": catalog.refs_for_role(ROLE_EXPLANATION),
                "action_option_refs": catalog.refs_for_role(ROLE_ACTION_OPTION),
                "condition_refs": catalog.refs_for_role(ROLE_CONDITION),
                "review_question_refs": catalog.refs_for_role(ROLE_REVIEW_QUESTION),
            },
            "evidence_role_instructions": {
                "real_world_advice_must_use_action_option_refs": True,
                "conditions_must_use_condition_refs": True,
                "knowledge_must_not_modify_program_facts_conclusion_or_timing": True,
                "draft_evidence_is_internal_preview_only": True,
                "provider_must_not_output_canonical_evidence_id": True,
                "provider_must_not_construct_evidence_refs": True,
                "provider_must_not_output_narrative_kind": True,
                "provider_must_not_output_epistemic_basis": True,
                "fixed_metadata_is_attached_by_program": True,
            },
            "program_owned_constraints": {
                "supporting_evidence_count": len(synthesis.supporting_evidence_ids),
                "blocking_evidence_count": len(synthesis.blocking_evidence_ids),
                "condition_evidence_count": len(catalog.refs_for_role(ROLE_CONDITION)),
                "ai_must_not_output_chart_facts": True,
                "ai_must_not_output_conclusion": True,
                "ai_must_not_output_timing": True,
            },
            "repair_prompt_version": REPAIR_PROMPT_VERSION if repair_context else None,
            "repair_context": repair_context,
        }
        return PromptPackage(
            system_prompt=load_system_prompt(),
            user_payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            prompt_version=PROMPT_VERSION,
        )
