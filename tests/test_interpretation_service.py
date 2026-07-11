import pytest

from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider
from abalo_iching.interpretation.enums import KnowledgeAccessMode
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy
from abalo_iching.interpretation.service import InterpretationService


def test_service_returns_validated_fake_result(phase2_request, valid_interpretation):
    provider = FakeInterpretationProvider([valid_interpretation])
    result = InterpretationService(provider).interpret(phase2_request)
    assert result.status.value == "SUCCESS"
    assert result.not_a_live_openai_result is True
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
    assert result.is_preview is True
    assert result.interpretation.model_metadata.provider_name == "FAKE"
    assert result.interpretation.model_metadata.attempt_number == 1
    assert result.interpretation.ai_content == valid_interpretation
    assert result.interpretation.program_content.conclusion_level is result.synthesis.conclusion_level


def test_first_validation_failure_is_repaired_once(phase2_request, valid_interpretation):
    invalid = valid_interpretation.model_dump(mode="json")
    invalid["plain_language_explanation"][0]["text"] = "下个月发生"
    provider = FakeInterpretationProvider([invalid, valid_interpretation])
    result = InterpretationService(provider).interpret(phase2_request)
    assert provider.call_count == 2
    assert provider.attempt_numbers == [1, 2]
    assert result.interpretation.model_metadata.attempt_number == 2


def test_two_validation_failures_raise_without_returning_partial_output(phase2_request, valid_interpretation):
    invalid = valid_interpretation.model_dump(mode="json")
    invalid["plain_language_explanation"][0]["text"] = "2026-08-08发生"
    provider = FakeInterpretationProvider([invalid, invalid])
    with pytest.raises(InterpretationValidationError) as exc:
        InterpretationService(provider).interpret(phase2_request)
    assert exc.value.attempts == 2
    assert exc.value.should_charge is False
    assert len(exc.value.provider_attempts) == 2
    assert all(item["total_tokens"] == 0 for item in exc.value.provider_attempts)
    assert provider.call_count == 2


def test_empty_ai_content_fails_twice_without_charge_or_formal_report(phase2_request):
    empty = {
        "plain_language_explanation": [],
        "real_world_advice": [],
        "conditions_that_change_outcome": [],
        "review_questions": [],
    }
    provider = FakeInterpretationProvider([empty, empty])
    with pytest.raises(InterpretationValidationError) as exc:
        InterpretationService(provider).interpret(phase2_request)
    assert exc.value.status == "FAILED_VALIDATION"
    assert exc.value.should_charge is False
    assert exc.value.persist_as_formal_report_allowed is False
    assert provider.call_count == 2


def test_empty_ai_content_can_be_repaired_once(phase2_request, valid_interpretation):
    empty = {
        "plain_language_explanation": [],
        "real_world_advice": [],
        "conditions_that_change_outcome": [],
        "review_questions": [],
    }
    provider = FakeInterpretationProvider([empty, valid_interpretation])
    result = InterpretationService(provider).interpret(phase2_request)
    assert provider.call_count == 2
    assert result.status.value == "SUCCESS"
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False


def test_service_records_timezone_provenance_without_fabricating_system_version(phase2_request, valid_interpretation):
    result = InterpretationService(FakeInterpretationProvider([valid_interpretation])).interpret(phase2_request)
    metadata = result.interpretation.model_metadata
    assert metadata.tzdata_package_version
    assert metadata.timezone_source
    assert metadata.system_tz_database_note == "SYSTEM_TZ_DATABASE_VERSION_UNAVAILABLE"


def test_internal_modes_are_preview_nonchargeable_and_not_persistable(phase2_request, valid_interpretation):
    service = InterpretationService(
        FakeInterpretationProvider([valid_interpretation]),
        knowledge_access_policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW),
    )
    result = service.interpret(phase2_request)
    assert result.is_preview is True
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
