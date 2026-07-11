from abalo_iching.interpretation.enums import NarrativeReleaseStatus
from abalo_iching.interpretation.release import narrative_release_snapshot
from abalo_iching.interpretation.models import ProviderResult
from abalo_iching.interpretation.service import InterpretationService


class OpenAILikeProvider:
    def __init__(self, output):
        self.output = output

    def generate(self, prompt, *, attempt_number):
        return ProviderResult(
            parsed_output=self.output,
            response_id="resp-mocked",
            model="mocked-live-model",
            input_tokens=10,
            output_tokens=10,
            total_tokens=20,
            latency_ms=1,
            attempt_number=attempt_number,
            provider_name="OPENAI_RESPONSES_API",
            prompt_version=prompt.prompt_version,
        )


def test_default_narrative_release_is_unverified_with_empty_live_eval_snapshot():
    snapshot = narrative_release_snapshot()
    assert snapshot.narrative_release_status is NarrativeReleaseStatus.UNVERIFIED
    assert snapshot.live_eval_version is None
    assert snapshot.live_eval_model is None
    assert snapshot.live_eval_completed_at is None
    assert snapshot.live_eval_case_count == 0


def test_environment_variable_cannot_promote_release_status(monkeypatch):
    monkeypatch.setenv("ABALO_NARRATIVE_RELEASE_STATUS", "APPROVED_FOR_CLOSED_BETA")
    assert narrative_release_snapshot().narrative_release_status is NarrativeReleaseStatus.UNVERIFIED


def test_unverified_openai_like_result_is_preview_nonchargeable_and_not_persistable(
    phase2_request, valid_interpretation
):
    result = InterpretationService(OpenAILikeProvider(valid_interpretation)).interpret(phase2_request)
    assert result.not_a_live_openai_result is False
    assert result.is_preview is True
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
