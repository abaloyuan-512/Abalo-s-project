import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.run_meihua_live_eval_v001 import DATASET, _request

from abalo_iching.interpretation.enums import (
    EpistemicBasis,
    KnowledgeAccessMode,
    NarrativeKind,
)
from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.evidence_references import build_evidence_reference_catalog
from abalo_iching.interpretation.historical_replay import replay_legacy_v3_output_text
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.models import AINarrativeDraftContent
from abalo_iching.interpretation.narrative_assembly import (
    NARRATIVE_ASSEMBLY_VERSION,
    PROVIDER_SCHEMA_VERSION,
    assemble_narrative,
)
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider
from abalo_iching.interpretation.service import InterpretationService
from abalo_iching.interpretation.validators import InterpretationValidator


SELECTED = json.loads(
    Path("tests/fixtures/metadata_replay_v2_selected_attempt1.json").read_text(encoding="utf-8")
)
CASE001 = json.loads(Path("tests/fixtures/case001_first_smoke_safe_parsed_results.json").read_text(encoding="utf-8"))


def test_provider_draft_schema_excludes_program_owned_metadata(valid_narrative_draft):
    claim_fields = type(valid_narrative_draft.plain_language_explanation[0]).model_fields
    assert "narrative_kind" not in claim_fields
    assert "epistemic_basis" not in claim_fields
    assert PROVIDER_SCHEMA_VERSION == "MEIHUA_AI_NARRATIVE_DRAFT_SCHEMA_V3"
    assert NARRATIVE_ASSEMBLY_VERSION == "MEIHUA_NARRATIVE_ASSEMBLY_V1"


def test_provider_cannot_submit_fixed_metadata(valid_narrative_draft):
    payload = valid_narrative_draft.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_ids"] = ["E01"]
    payload["plain_language_explanation"][0]["narrative_kind"] = "ACTION_OPTION"
    payload["plain_language_explanation"][0]["epistemic_basis"] = "UNCERTAINTY"
    with pytest.raises(ValidationError):
        AINarrativeDraftContent.model_validate(payload)


def test_assembler_sets_all_four_fixed_mappings(valid_narrative_draft, phase2_evidence_catalog):
    assembled = assemble_narrative(valid_narrative_draft, phase2_evidence_catalog)
    expected = {
        "plain_language_explanation": (NarrativeKind.EXPLANATION, EpistemicBasis.CHART_EVIDENCE),
        "real_world_advice": (NarrativeKind.ACTION_OPTION, EpistemicBasis.ACTION_OPTION),
        "conditions_that_change_outcome": (NarrativeKind.CONDITION_TO_VERIFY, EpistemicBasis.UNCERTAINTY),
        "review_questions": (NarrativeKind.REVIEW_QUESTION, EpistemicBasis.UNCERTAINTY),
    }
    for field, (kind, basis) in expected.items():
        for claim in getattr(assembled, field):
            assert claim.narrative_kind is kind
            assert claim.epistemic_basis is basis


def test_service_assembles_provider_draft_before_validation(valid_narrative_draft, phase2_request):
    result = InterpretationService(FakeInterpretationProvider([valid_narrative_draft])).interpret(phase2_request)
    assert result.interpretation.ai_content.real_world_advice[0].narrative_kind is NarrativeKind.ACTION_OPTION
    assert result.interpretation.ai_content.real_world_advice[0].epistemic_basis is EpistemicBasis.ACTION_OPTION


def test_legacy_wrong_metadata_cannot_override_program_values():
    payload = copy.deepcopy(SELECTED["CASE-002_low_1"])
    for claims in payload.values():
        for claim in claims:
            claim["narrative_kind"] = "REVIEW_QUESTION"
            claim["epistemic_basis"] = "UNCERTAINTY"
    case = next(x for x in json.loads(DATASET.read_text(encoding="utf-8"))["cases"] if x["case_id"] == "CASE-002")
    request = _request(case)
    knowledge = select_knowledge(request.chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW))
    synthesis = ConclusionSynthesizer().synthesize(request.chart, knowledge)
    catalog = build_evidence_reference_catalog(request, knowledge, synthesis)
    assembled = replay_legacy_v3_output_text(json.dumps(payload, ensure_ascii=False), request, catalog)
    assert all(x.narrative_kind is NarrativeKind.EXPLANATION for x in assembled.plain_language_explanation)
    assert all(x.epistemic_basis is EpistemicBasis.CHART_EVIDENCE for x in assembled.plain_language_explanation)
    assert all(x.narrative_kind is NarrativeKind.ACTION_OPTION for x in assembled.real_world_advice)
    assert all(x.epistemic_basis is EpistemicBasis.ACTION_OPTION for x in assembled.real_world_advice)


def test_assembled_unknown_evidence_is_still_rejected(valid_narrative_draft, phase2_evidence_catalog):
    payload = valid_narrative_draft.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_refs"] = ["EV999"]
    with pytest.raises(ValueError, match="UNKNOWN_EVIDENCE_REF"):
        assemble_narrative(payload, phase2_evidence_catalog)


@pytest.mark.parametrize(
    ("fixture_key", "case_id", "effort"),
    [
        ("CASE-002_low_1", "CASE-002", "low"),
        ("CASE-002_medium_1", "CASE-002", "medium"),
        ("CASE-009_low_1", "CASE-009", "low"),
        ("CASE-010_low_1", "CASE-010", "low"),
    ],
)
def test_selected_real_attempt1_replays_pass_safely(fixture_key, case_id, effort):
    case = next(x for x in json.loads(DATASET.read_text(encoding="utf-8"))["cases"] if x["case_id"] == case_id)
    request = _request(case)
    knowledge = select_knowledge(
        request.chart,
        policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
    )
    synthesis = ConclusionSynthesizer().synthesize(request.chart, knowledge)
    catalog = build_evidence_reference_catalog(request, knowledge, synthesis)
    assembled = replay_legacy_v3_output_text(json.dumps(SELECTED[fixture_key], ensure_ascii=False), request, catalog)
    assert InterpretationValidator().validate(assembled, request, knowledge, synthesis) == assembled
    assert effort in {"low", "medium"}


def test_draft_production_and_condition_safety_rules_are_unchanged():
    case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][0]
    request = _request(case)
    preview = select_knowledge(
        request.chart,
        policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
    )
    synthesis = ConclusionSynthesizer().synthesize(request.chart, preview)
    payload = copy.deepcopy(CASE001["attempts"][0]["parsed_result"])
    catalog = build_evidence_reference_catalog(request, preview, synthesis)
    assembled = replay_legacy_v3_output_text(json.dumps(payload, ensure_ascii=False), request, catalog)
    forged = preview.model_copy(update={"access_mode": "PRODUCTION", "is_preview": False})
    with pytest.raises(InterpretationValidationError, match="preview_knowledge_in_production"):
        InterpretationValidator().validate(assembled, request, forged, synthesis)
