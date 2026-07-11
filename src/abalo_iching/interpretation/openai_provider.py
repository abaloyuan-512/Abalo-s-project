"""OpenAI Responses API adapter; no call occurs unless this provider is invoked."""

from __future__ import annotations

import os
from collections.abc import Callable
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from .exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderIncompleteError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from .models import AINarrativeContent, PromptPackage, ProviderResult

DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_MAX_OUTPUT_TOKENS = 2000
MIN_MAX_OUTPUT_TOKENS = 500
MAX_MAX_OUTPUT_TOKENS = 4000


def configured_max_output_tokens() -> int:
    raw = os.getenv("ABALO_OPENAI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProviderConfigurationError("ABALO_OPENAI_MAX_OUTPUT_TOKENS must be an integer") from exc
    if not MIN_MAX_OUTPUT_TOKENS <= value <= MAX_MAX_OUTPUT_TOKENS:
        raise ProviderConfigurationError(
            f"ABALO_OPENAI_MAX_OUTPUT_TOKENS must be between {MIN_MAX_OUTPUT_TOKENS} and {MAX_MAX_OUTPUT_TOKENS}"
        )
    return value


class OpenAIInterpretationProvider:
    def __init__(
        self,
        *,
        client_factory: Callable[..., Any] = OpenAI,
        timeout_seconds: float = 45.0,
        max_retries: int = 1,
    ) -> None:
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
        max_output_tokens = configured_max_output_tokens()
        if not os.getenv("OPENAI_API_KEY"):
            raise ProviderConfigurationError("OPENAI_API_KEY is required for the live provider")
        model = os.getenv("ABALO_OPENAI_MODEL", DEFAULT_MODEL)
        started = perf_counter()
        try:
            client = self._client_factory(timeout=self._timeout_seconds, max_retries=self._max_retries)
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_payload_json},
                ],
                text_format=AINarrativeContent,
                store=False,
                tools=[],
                max_output_tokens=max_output_tokens,
            )
            if getattr(response, "status", None) == "incomplete":
                raise ProviderIncompleteError("OpenAI response was incomplete")
            parsed = getattr(response, "output_parsed", None)
            if parsed is None:
                for output in getattr(response, "output", ()):
                    for content in getattr(output, "content", ()):
                        if getattr(content, "type", None) == "refusal":
                            raise ProviderRefusalError("OpenAI refused the structured interpretation request")
                raise ProviderSchemaError("OpenAI returned no parsed structured output")
            usage = getattr(response, "usage", None)
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)
            return ProviderResult(
                parsed_output=parsed,
                response_id=getattr(response, "id", None),
                model=getattr(response, "model", model),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=int((perf_counter() - started) * 1000),
                attempt_number=attempt_number,
                provider_name="OPENAI_RESPONSES_API",
                prompt_version=prompt.prompt_version,
            )
        except (ProviderIncompleteError, ProviderRefusalError, ProviderSchemaError):
            raise
        except APITimeoutError as exc:
            raise ProviderTimeoutError("OpenAI request timed out") from exc
        except RateLimitError as exc:
            raise ProviderRateLimitError("OpenAI rate limit reached") from exc
        except AuthenticationError as exc:
            raise ProviderAuthenticationError("OpenAI authentication failed") from exc
        except APIConnectionError as exc:
            raise ProviderConnectionError("OpenAI connection failed") from exc
        except ValidationError as exc:
            raise ProviderSchemaError("OpenAI structured response failed schema parsing") from exc
