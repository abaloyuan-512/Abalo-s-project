from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError

from abalo_iching.interpretation.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderIncompleteError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from abalo_iching.interpretation.models import PromptPackage
from abalo_iching.interpretation.openai_provider import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    OpenAIInterpretationProvider,
)


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.responses = FakeResponses(response)


class RaisingResponses:
    def __init__(self, error):
        self.error = error

    def parse(self, **kwargs):
        raise self.error


class RaisingClient:
    def __init__(self, error):
        self.responses = RaisingResponses(error)


def test_provider_requires_environment_key_without_disclosing_details(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderConfigurationError, match="OPENAI_API_KEY is required"):
        OpenAIInterpretationProvider(client_factory=lambda **_: None).generate(
            PromptPackage("system", "{}", "v1"), attempt_number=1
        )


def test_provider_uses_responses_parse_pydantic_store_false_and_no_tools(monkeypatch, valid_interpretation):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    monkeypatch.delenv("ABALO_OPENAI_MODEL", raising=False)
    response = SimpleNamespace(
        id="resp_test",
        model=DEFAULT_MODEL,
        status="completed",
        output_parsed=valid_interpretation,
        usage=SimpleNamespace(input_tokens=11, output_tokens=7, total_tokens=18),
        output=[],
    )
    client = FakeClient(response)
    provider = OpenAIInterpretationProvider(client_factory=lambda **_: client)
    result = provider.generate(PromptPackage("system", "{}", "v1"), attempt_number=1)
    assert client.responses.kwargs["model"] == DEFAULT_MODEL
    assert client.responses.kwargs["text_format"] is type(valid_interpretation)
    assert "model_metadata" not in client.responses.kwargs["text_format"].model_fields
    assert client.responses.kwargs["store"] is False
    assert client.responses.kwargs["tools"] == []
    assert client.responses.kwargs["max_output_tokens"] == DEFAULT_MAX_OUTPUT_TOKENS
    assert result.total_tokens == 18
    assert result.provider_name == "OPENAI_RESPONSES_API"


def test_model_can_be_overridden_only_by_abalo_environment(monkeypatch, valid_interpretation):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    monkeypatch.setenv("ABALO_OPENAI_MODEL", "test-model")
    response = SimpleNamespace(id="r", model="test-model", status="completed", output_parsed=valid_interpretation, usage=None, output=[])
    client = FakeClient(response)
    OpenAIInterpretationProvider(client_factory=lambda **_: client).generate(PromptPackage("s", "{}", "v"), attempt_number=1)
    assert client.responses.kwargs["model"] == "test-model"


def test_valid_max_output_tokens_environment_override_is_passed(monkeypatch, valid_interpretation):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    monkeypatch.setenv("ABALO_OPENAI_MAX_OUTPUT_TOKENS", "2500")
    response = SimpleNamespace(id="r", model="m", status="completed", output_parsed=valid_interpretation, usage=None, output=[])
    client = FakeClient(response)
    OpenAIInterpretationProvider(client_factory=lambda **_: client).generate(PromptPackage("s", "{}", "v"), attempt_number=1)
    assert client.responses.kwargs["max_output_tokens"] == 2500


@pytest.mark.parametrize("value", ["not-an-int", "499", "4001"])
def test_invalid_max_output_tokens_configuration_is_rejected(monkeypatch, value):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    monkeypatch.setenv("ABALO_OPENAI_MAX_OUTPUT_TOKENS", value)
    with pytest.raises(ProviderConfigurationError, match="ABALO_OPENAI_MAX_OUTPUT_TOKENS"):
        OpenAIInterpretationProvider(client_factory=lambda **_: None).generate(
            PromptPackage("s", "{}", "v"), attempt_number=1
        )


def test_incomplete_response_is_mapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        output_parsed=None,
        output=[],
    )
    with pytest.raises(ProviderIncompleteError):
        OpenAIInterpretationProvider(client_factory=lambda **_: FakeClient(response)).generate(
            PromptPackage("s", "{}", "v"), attempt_number=1
        )


def test_refusal_and_missing_parse_are_mapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    refusal = SimpleNamespace(
        status="completed",
        output_parsed=None,
        output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
    )
    with pytest.raises(ProviderRefusalError):
        OpenAIInterpretationProvider(client_factory=lambda **_: FakeClient(refusal)).generate(
            PromptPackage("s", "{}", "v"), attempt_number=1
        )
    missing = SimpleNamespace(status="completed", output_parsed=None, output=[])
    with pytest.raises(ProviderSchemaError):
        OpenAIInterpretationProvider(client_factory=lambda **_: FakeClient(missing)).generate(
            PromptPackage("s", "{}", "v"), attempt_number=1
        )


@pytest.mark.parametrize(
    ("sdk_error", "local_error"),
    [
        (APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses")), ProviderTimeoutError),
        (
            APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses")),
            ProviderConnectionError,
        ),
        (
            RateLimitError(
                "rate limited",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
                ),
                body=None,
            ),
            ProviderRateLimitError,
        ),
        (
            AuthenticationError(
                "unauthorized",
                response=httpx.Response(
                    401,
                    request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
                ),
                body=None,
            ),
            ProviderAuthenticationError,
        ),
    ],
)
def test_transport_failures_are_safely_mapped(monkeypatch, sdk_error, local_error):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder-not-a-real-key")
    with pytest.raises(local_error) as exc:
        OpenAIInterpretationProvider(client_factory=lambda **_: RaisingClient(sdk_error)).generate(
            PromptPackage("s", "{}", "v"), attempt_number=1
        )
    assert exc.value.should_charge is False
