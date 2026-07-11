import pytest

from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider
from abalo_iching.interpretation.models import PromptPackage


def test_fake_provider_returns_injected_output(valid_interpretation):
    provider = FakeInterpretationProvider([valid_interpretation])
    result = provider.generate(PromptPackage("system", "{}", "v1"), attempt_number=1)
    assert result.parsed_output == valid_interpretation
    assert result.provider_name == "FAKE"
    assert result.total_tokens == 0


def test_fake_provider_can_inject_refusal_timeout_or_rate_limit():
    provider = FakeInterpretationProvider([TimeoutError("simulated")])
    with pytest.raises(TimeoutError, match="simulated"):
        provider.generate(PromptPackage("system", "{}", "v1"), attempt_number=1)


def test_fake_provider_can_model_first_failure_second_success(valid_interpretation):
    provider = FakeInterpretationProvider([{"bad": "schema"}, valid_interpretation])
    assert provider.generate(PromptPackage("system", "{}", "v1"), attempt_number=1).parsed_output == {"bad": "schema"}
    assert provider.generate(PromptPackage("system", "{}", "v1"), attempt_number=2).parsed_output == valid_interpretation
