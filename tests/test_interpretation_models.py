import pytest
from pydantic import ValidationError

from abalo_iching.interpretation.enums import QuestionDomain
from abalo_iching.interpretation.models import AINarrativeClaim, AINarrativeContent, InterpretationRequest


def test_request_has_no_external_draft_switch_and_defaults_to_simplified_chinese(phase2_chart):
    request = InterpretationRequest(
        question_id="q",
        question_domain=QuestionDomain.RELATIONSHIP,
        normalized_question="是否继续了解？",
        decision_goal="决定下一步",
        time_horizon="当前阶段",
        chart=phase2_chart,
    )
    assert "allow_draft_knowledge" not in InterpretationRequest.model_fields
    assert request.language == "zh-CN"


@pytest.mark.parametrize("field", ["normalized_question", "decision_goal", "time_horizon"])
def test_request_rejects_empty_required_question_fields(phase2_request, field):
    with pytest.raises(ValidationError):
        phase2_request.model_copy(update={field: ""}).model_validate(
            {**phase2_request.model_dump(), field: ""}
        )


def test_request_rejects_multiple_core_questions(phase2_request):
    payload = phase2_request.model_dump()
    payload["normalized_question"] = "要继续吗？要退出吗？"
    with pytest.raises(ValidationError, match="一个请求只能包含一个核心问题"):
        InterpretationRequest.model_validate(payload)


def test_request_domain_is_closed(phase2_request):
    payload = phase2_request.model_dump()
    payload["question_domain"] = "MEDICAL"
    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate(payload)


def test_claim_requires_real_evidence_id():
    with pytest.raises(ValidationError):
        AINarrativeClaim(
            text="这是一个测试主张",
            evidence_ids=[],
            narrative_kind="EXPLANATION",
            subject_scope="SITUATION",
            epistemic_basis="CHART_EVIDENCE",
        )


@pytest.mark.parametrize("field", ["plain_language_explanation", "real_world_advice", "review_questions"])
def test_required_ai_content_groups_cannot_be_empty(valid_interpretation, field):
    payload = valid_interpretation.model_dump(mode="json")
    payload[field] = []
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)


def test_all_ai_content_groups_empty_are_rejected(valid_interpretation):
    payload = {field: [] for field in type(valid_interpretation).model_fields}
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)


@pytest.mark.parametrize("field", list(AINarrativeContent.model_fields))
def test_ai_content_groups_reject_more_than_four_claims(valid_interpretation, field):
    payload = valid_interpretation.model_dump(mode="json")
    sample = payload["plain_language_explanation"][0]
    payload[field] = [sample] * 5
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)


def test_ai_claim_rejects_text_over_300_characters(valid_interpretation):
    payload = valid_interpretation.model_dump(mode="json")
    payload["plain_language_explanation"][0]["text"] = "测" * 301
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)


def test_ai_claim_rejects_duplicate_or_more_than_six_evidence_ids(valid_interpretation):
    payload = valid_interpretation.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_ids"] = ["E02", "E02"]
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)
    payload["plain_language_explanation"][0]["evidence_ids"] = [f"E{i:02d}" for i in range(7)]
    with pytest.raises(ValidationError):
        AINarrativeContent.model_validate(payload)
