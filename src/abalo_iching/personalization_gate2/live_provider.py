from __future__ import annotations

import json
import os
import re
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

from .models import (
    Gate2ExperimentOutput,
    Gate2PromptPackage,
    Gate2ProviderResult,
    Gate2Usage,
)
from .pricing import Gate2TokenPricing


DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_MAX_OUTPUT_TOKENS = 6000


class Gate2LiveProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _safe_validation_detail(exc: ValidationError) -> str:
    detail = str(exc)
    detail = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_API_KEY]", detail)
    detail = re.sub(r"[A-Za-z]:\\[^\s\"']+", "[REDACTED_LOCAL_PATH]", detail)
    return detail[:1200]


class OpenAIGate2Provider:
    """Gate 2 阶段 C 专用 Responses API Provider。

    它与正式解释 Provider 隔离，固定单次调用、零 SDK 自动重试、store=false、tools=[]。
    """

    provider_name = "OPENAI_RESPONSES_API_GATE2_CALIBRATION"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        pricing: Gate2TokenPricing | None = None,
        client_factory: Callable[..., Any] = OpenAI,
        timeout_seconds: float = 120.0,
    ) -> None:
        if max_output_tokens < 1 or max_output_tokens > 8000:
            raise ValueError("Gate 2 阶段 C max_output_tokens 必须在1到8000之间")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.pricing = pricing or Gate2TokenPricing(model=model)
        if self.pricing.model != model:
            raise ValueError("模型与价格坐标不一致")
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds
        self.call_count = 0

    def generate(self, prompt: Gate2PromptPackage) -> Gate2ProviderResult:
        if not os.getenv("OPENAI_API_KEY"):
            raise Gate2LiveProviderError(
                "api_key_missing",
                "OPENAI_API_KEY 未进入当前调用进程",
            )
        self.call_count += 1
        started = perf_counter()
        try:
            client = self._client_factory(
                timeout=self._timeout_seconds,
                max_retries=0,
            )
            response = client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": prompt.system_instructions},
                    {
                        "role": "user",
                        "content": json.dumps(
                            prompt.input_payload,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    },
                ],
                text_format=Gate2ExperimentOutput,
                reasoning={"effort": self.reasoning_effort},
                store=False,
                tools=[],
                max_output_tokens=self.max_output_tokens,
            )
            if getattr(response, "status", None) == "incomplete":
                raise Gate2LiveProviderError(
                    "response_incomplete",
                    "OpenAI 返回 incomplete，阶段 C 不自动续写或重试",
                )
            parsed = getattr(response, "output_parsed", None)
            if parsed is None:
                for output in getattr(response, "output", ()):
                    for content in getattr(output, "content", ()):
                        if getattr(content, "type", None) == "refusal":
                            raise Gate2LiveProviderError(
                                "response_refusal",
                                "OpenAI 拒绝了结构化校准请求",
                            )
                raise Gate2LiveProviderError(
                    "structured_output_missing",
                    "OpenAI 未返回可解析的结构化输出",
                )

            raw_output = parsed.model_dump(mode="json")
            output_text = getattr(response, "output_text", None)
            if output_text:
                try:
                    decoded = json.loads(output_text)
                except json.JSONDecodeError:
                    decoded = None
                if isinstance(decoded, dict):
                    raw_output = decoded

            usage_object = getattr(response, "usage", None)
            input_details = getattr(usage_object, "input_tokens_details", None)
            output_details = getattr(usage_object, "output_tokens_details", None)
            input_tokens = int(getattr(usage_object, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage_object, "output_tokens", 0) or 0)
            usage = Gate2Usage(
                input_tokens=input_tokens,
                cached_input_tokens=int(getattr(input_details, "cached_tokens", 0) or 0),
                cache_write_tokens=int(
                    getattr(input_details, "cache_write_tokens", 0) or 0
                ),
                output_tokens=output_tokens,
                reasoning_tokens=int(
                    getattr(output_details, "reasoning_tokens", 0) or 0
                ),
                total_tokens=int(
                    getattr(
                        usage_object,
                        "total_tokens",
                        input_tokens + output_tokens,
                    )
                    or 0
                ),
            )
            return Gate2ProviderResult(
                response_id=str(getattr(response, "id", "missing-response-id")),
                provider_name=self.provider_name,
                model=str(getattr(response, "model", self.model)),
                raw_output=raw_output,
                usage=usage,
                latency_ms=int((perf_counter() - started) * 1000),
                cost_usd=float(self.pricing.calculate(usage)),
            )
        except Gate2LiveProviderError:
            raise
        except ValidationError as exc:
            raise Gate2LiveProviderError(
                "structured_output_schema_invalid",
                f"OpenAI结构化输出未通过阶段 C Schema：{_safe_validation_detail(exc)}",
            ) from exc
        except AuthenticationError as exc:
            raise Gate2LiveProviderError(
                "authentication_failed", "OpenAI API 身份验证失败"
            ) from exc
        except RateLimitError as exc:
            raise Gate2LiveProviderError(
                "rate_limit", "OpenAI API 当前达到速率或额度限制"
            ) from exc
        except APITimeoutError as exc:
            raise Gate2LiveProviderError(
                "timeout", "OpenAI API 请求超时；阶段 C 不自动重试"
            ) from exc
        except APIConnectionError as exc:
            raise Gate2LiveProviderError(
                "connection_failed", "OpenAI API 连接失败；阶段 C 不自动重试"
            ) from exc
        except Exception as exc:
            raise Gate2LiveProviderError(
                "provider_error", f"OpenAI 阶段 C Provider 失败：{type(exc).__name__}"
            ) from exc
