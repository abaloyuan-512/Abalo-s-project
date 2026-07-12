"""Build a static system prompt and a narrow narrative-only JSON payload."""

from __future__ import annotations

import json
from importlib.resources import files

from abalo_iching.meihua.enums import EvidenceType

from .evidence_roles import evidence_role_constraints
from .models import InterpretationRequest, KnowledgeSelection, PromptPackage, SynthesisResult

PROMPT_VERSION = "MEIHUA_INTERPRETATION_PROMPT_V3"
REPAIR_PROMPT_VERSION = "MEIHUA_REPAIR_PROMPT_V2"


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
        narrative_types = {
            EvidenceType.INITIAL_BODY_USE_RELATION,
            EvidenceType.CHANGED_BODY_USE_RELATION,
            EvidenceType.BODY_SEASONAL_STRENGTH,
            EvidenceType.INITIAL_USE_SEASONAL_STRENGTH,
            EvidenceType.CHANGED_USE_SEASONAL_STRENGTH,
            EvidenceType.MOVING_LINE_STAGE,
        }
        evidence = [
            {
                "evidence_id": item.evidence_id,
                "fact": item.fact,
                "rule_statement": item.rule_statement,
                "polarity": item.polarity.value,
                "strength": item.strength.value,
            }
            for item in request.chart.evidence
            if item.evidence_type in narrative_types
        ]
        roles = evidence_role_constraints(request, knowledge, synthesis)
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
                        "allowed_action_option_ids": sorted(roles.action_option_ids),
                        "forbidden_evidence_rule": (
                            "Do not cite Evidence IDs outside allowed_action_option_ids in real_world_advice."
                        ),
                    }
                )
        payload = {
            "prompt_version": PROMPT_VERSION,
            "task": "Generate AINarrativeContent only. Program facts, conclusion and timing are rendered elsewhere.",
            "user_data_untrusted": {
                "normalized_question": request.normalized_question,
                "decision_goal": request.decision_goal,
                "real_world_context": request.real_world_context,
                "question_domain": request.question_domain.value,
            },
            "allowed_narrative_evidence": evidence,
            "allowed_knowledge_evidence": [
                {
                    "evidence_id": item.evidence_id,
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
                for item in knowledge.knowledge_evidence
                if item.evidence_id in roles.selected_knowledge_ids
            ],
            "evidence_role_constraints": roles.as_prompt_payload(),
            "evidence_role_instructions": {
                "real_world_advice_must_use_action_option_ids": True,
                "conditions_must_use_condition_ids": True,
                "knowledge_must_not_modify_program_facts_conclusion_or_timing": True,
                "draft_evidence_is_internal_preview_only": True,
            },
            "program_owned_constraints": {
                "supporting_evidence_ids": synthesis.supporting_evidence_ids,
                "blocking_evidence_ids": synthesis.blocking_evidence_ids,
                "condition_evidence_ids": [
                    item.evidence_ids[0]
                    for item in synthesis.relation_assessments
                    if item.conditions or item.warnings
                ],
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
