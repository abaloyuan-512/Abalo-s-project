import json
from pathlib import Path

import pytest

from scripts.run_meihua_live_eval_v001 import DATASET, _request

from abalo_iching.interpretation.enums import KnowledgeAccessMode
from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.models import AINarrativeContent, KnowledgeEvidence
from abalo_iching.interpretation.prompt_builder import PromptBuilder
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.interpretation.validators import (
    VALIDATOR_CONTRACT_VERSION,
    InterpretationValidator,
    _CONDITION_TEMPLATE,
)
from abalo_iching.meihua.enums import EvidenceType


FIXTURE = Path("tests/fixtures/case001_first_smoke_safe_parsed_results.json")


def context():
    case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][0]
    request = _request(case)
    knowledge = select_knowledge(
        request.chart,
        policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
    )
    synthesis = ConclusionSynthesizer().synthesize(request.chart, knowledge)
    attempts = json.loads(FIXTURE.read_text(encoding="utf-8"))["attempts"]
    return request, knowledge, synthesis, attempts


def validate(payload, request, knowledge, synthesis):
    return InterpretationValidator().validate(payload, request, knowledge, synthesis)


def test_first_smoke_safe_parsed_results_pass_validator_v2(capsys):
    request, knowledge, synthesis, attempts = context()
    assert VALIDATOR_CONTRACT_VERSION == "MEIHUA_INTERPRETATION_VALIDATOR_V2"
    for item in attempts:
        result = AINarrativeContent.model_validate(item["parsed_result"])
        assert validate(result, request, knowledge, synthesis) == result
        print(f"CASE001_ATTEMPT{item['attempt_number']}_FIXTURE_VALIDATION=PASS")
    assert capsys.readouterr().out.splitlines() == [
        "CASE001_ATTEMPT1_FIXTURE_VALIDATION=PASS",
        "CASE001_ATTEMPT2_FIXTURE_VALIDATION=PASS",
    ]


def test_case001_selected_draft_action_knowledge_is_allowed():
    request, knowledge, synthesis, attempts = context()
    payload = attempts[0]["parsed_result"]
    validate(payload, request, knowledge, synthesis)
    prompt = json.loads(PromptBuilder().build(request, knowledge, synthesis).user_payload_json)
    assert {"D-H-1", "D-L-1-1"} <= set(prompt["evidence_role_constraints"]["action_option_ids"])


def test_unselected_or_unrelated_knowledge_is_not_action_evidence():
    request, knowledge, synthesis, attempts = context()
    payload = attempts[0]["parsed_result"] | {}
    payload = json.loads(json.dumps(payload))
    payload["real_world_advice"][0]["evidence_ids"] = ["D-H-2"]
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, request, knowledge, synthesis)
    assert {"unknown_evidence_id", "action_evidence_role_mismatch"} <= set(exc.value.errors)

    unrelated_payload = knowledge.knowledge_evidence[0].model_dump(mode="json")
    unrelated_payload.update({"evidence_id": "D-H-2", "king_wen_number": 2})
    unrelated = KnowledgeEvidence.model_validate(unrelated_payload)
    forged = knowledge.model_copy(update={
        "allowed_knowledge_evidence_ids": [*knowledge.allowed_knowledge_evidence_ids, "D-H-2"],
        "knowledge_evidence": [*knowledge.knowledge_evidence, unrelated],
    })
    with pytest.raises(InterpretationValidationError, match="action_evidence_role_mismatch"):
        validate(payload, request, forged, synthesis)


def test_seasonal_evidence_does_not_become_action_evidence():
    request, knowledge, synthesis, attempts = context()
    relation_action_ids = set(synthesis.supporting_evidence_ids) | set(synthesis.blocking_evidence_ids)
    seasonal = next(
        item.evidence_id
        for item in request.chart.evidence
        if item.evidence_type in {
            EvidenceType.BODY_SEASONAL_STRENGTH,
            EvidenceType.INITIAL_USE_SEASONAL_STRENGTH,
            EvidenceType.CHANGED_USE_SEASONAL_STRENGTH,
        }
        and item.evidence_id not in relation_action_ids
    )
    payload = json.loads(json.dumps(attempts[0]["parsed_result"]))
    payload["real_world_advice"][0]["evidence_ids"] = [seasonal]
    with pytest.raises(InterpretationValidationError, match="action_evidence_role_mismatch"):
        validate(payload, request, knowledge, synthesis)


def test_production_rejects_draft_and_empty_action_tendency_is_not_allowed():
    request, knowledge, synthesis, attempts = context()
    production_forgery = knowledge.model_copy(update={"access_mode": "PRODUCTION", "is_preview": False})
    with pytest.raises(InterpretationValidationError, match="preview_knowledge_in_production"):
        validate(attempts[0]["parsed_result"], request, production_forgery, synthesis)

    no_action = knowledge.knowledge_evidence[0].model_copy(update={"action_tendency": None})
    no_action_selection = knowledge.model_copy(update={
        "knowledge_evidence": [no_action, knowledge.knowledge_evidence[1]],
    })
    payload = json.loads(json.dumps(attempts[0]["parsed_result"]))
    payload["real_world_advice"][0]["evidence_ids"] = ["D-H-1"]
    with pytest.raises(InterpretationValidationError, match="action_evidence_role_mismatch"):
        validate(payload, request, no_action_selection, synthesis)


def test_prohibited_inference_and_condition_roles_remain_enforced():
    request, knowledge, synthesis, attempts = context()
    payload = json.loads(json.dumps(attempts[0]["parsed_result"]))
    payload["real_world_advice"][0]["text"] = (
        "可以考虑核对这一限制：" + knowledge.knowledge_evidence[0].prohibited_inferences[0]
    )
    payload["real_world_advice"][0]["evidence_ids"] = ["D-H-1"]
    with pytest.raises(InterpretationValidationError, match="knowledge_prohibited_inference"):
        validate(payload, request, knowledge, synthesis)

    payload = json.loads(json.dumps(attempts[0]["parsed_result"]))
    payload["conditions_that_change_outcome"] = [{
        "text": _CONDITION_TEMPLATE,
        "evidence_ids": ["D-H-1"],
        "narrative_kind": "CONDITION_TO_VERIFY",
        "subject_scope": "SITUATION",
        "epistemic_basis": "UNCERTAINTY",
    }]
    with pytest.raises(InterpretationValidationError, match="condition_not_program_grounded"):
        validate(payload, request, knowledge, synthesis)
