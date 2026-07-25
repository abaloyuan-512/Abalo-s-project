from __future__ import annotations

import json
import os
from collections.abc import Callable
from time import perf_counter, sleep
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from .live_provider import (
    DEFAULT_MODEL,
    Gate2LiveProviderError,
    _safe_validation_detail,
)
from .models import (
    Gate2BackgroundCheckpoint,
    Gate2ExperimentOutput,
    Gate2PromptPackage,
    Gate2ProviderResult,
    Gate2Usage,
)
from .pricing import Gate2TokenPricing


STAGE_C1_REASONING_EFFORT = "medium"
STAGE_C1_MAX_OUTPUT_TOKENS = 10_000
STAGE_C1_POLL_INTERVAL_SECONDS = 2.0
STAGE_C1_MAX_POLL_ATTEMPTS = 300
_RUNNING_STATUSES = {"queued", "in_progress"}
_TERMINAL_STATUSES = {"completed", "incomplete", "failed", "cancelled"}


def _usage_from_response(response: Any) -> Gate2Usage:
    usage_object = getattr(response, "usage", None)
    input_details = getattr(usage_object, "input_tokens_details", None)
    output_details = getattr(usage_object, "output_tokens_details", None)
    input_tokens = int(getattr(usage_object, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage_object, "output_tokens", 0) or 0)
    return Gate2Usage(
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
            getattr(usage_object, "total_tokens", input_tokens + output_tokens) or 0
        ),
    )


def _incomplete_reason(response: Any) -> str | None:
    details = getattr(response, "incomplete_details", None)
    reason = getattr(details, "reason", None)
    return str(reason) if reason else None


def _raw_output_from_response(response: Any) -> dict[str, Any] | None:
    output_text = getattr(response, "output_text", None)
    if not output_text:
        return None
    try:
        decoded = json.loads(output_text)
    except (TypeError, json.JSONDecodeError):
        return {"unparsed_output_text": str(output_text)}
    return decoded if isinstance(decoded, dict) else {"decoded_output": decoded}


class OpenAIGate2BackgroundProvider:
    """阶段 C.1专用后台 Provider。

    POST只创建一次生成；后续操作只按响应ID轮询同一请求。SDK自动重试保持为0。
    """

    provider_name = "OPENAI_RESPONSES_API_GATE2_CALIBRATION_BACKGROUND"
    output_model = Gate2ExperimentOutput
    stage_label = "C.1"
    offline_simulation = False

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        reasoning_effort: str = STAGE_C1_REASONING_EFFORT,
        max_output_tokens: int = STAGE_C1_MAX_OUTPUT_TOKENS,
        pricing: Gate2TokenPricing | None = None,
        client_factory: Callable[..., Any] = OpenAI,
        request_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = STAGE_C1_POLL_INTERVAL_SECONDS,
        max_poll_attempts: int = STAGE_C1_MAX_POLL_ATTEMPTS,
        sleep_fn: Callable[[float], None] = sleep,
        on_checkpoint: Callable[[Gate2BackgroundCheckpoint], None] | None = None,
    ) -> None:
        if max_output_tokens < 1 or max_output_tokens > 25_000:
            raise ValueError(
                f"阶段 {self.stage_label} max_output_tokens必须在1到25000之间"
            )
        if request_timeout_seconds <= 0:
            raise ValueError(f"阶段 {self.stage_label}单次HTTP超时必须大于0")
        if poll_interval_seconds < 0:
            raise ValueError(f"阶段 {self.stage_label}轮询间隔不能为负数")
        if max_poll_attempts < 1:
            raise ValueError(f"阶段 {self.stage_label}最大轮询次数必须至少为1")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.pricing = pricing or Gate2TokenPricing(model=model)
        if self.pricing.model != model:
            raise ValueError("模型与价格坐标不一致")
        self._client_factory = client_factory
        self._request_timeout_seconds = request_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._max_poll_attempts = max_poll_attempts
        self._sleep = sleep_fn
        self._on_checkpoint = on_checkpoint
        self.call_count = 0
        self.poll_count = 0

    def generate(self, prompt: Gate2PromptPackage) -> Gate2ProviderResult:
        """创建一次后台响应并轮询至终态。"""

        client = self._client()
        started = perf_counter()
        self.call_count += 1
        try:
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
                text_format=self.output_model,
                reasoning={"effort": self.reasoning_effort},
                background=True,
                store=False,
                tools=[],
                max_output_tokens=self.max_output_tokens,
            )
        except Exception as exc:
            self._raise_api_error(
                exc,
                phase="background_start",
                latency_ms=int((perf_counter() - started) * 1000),
            )
        return self._await_terminal(client, response, started=started)

    def resume(
        self,
        prompt: Gate2PromptPackage,
        *,
        response_id: str,
    ) -> Gate2ProviderResult:
        """只恢复轮询已有响应，不创建新生成。"""

        if not response_id or len(response_id) > 160:
            raise ValueError(f"阶段 {self.stage_label}恢复响应ID无效")
        client = self._client()
        started = perf_counter()
        try:
            response = client.responses.retrieve(response_id)
            self.poll_count += 1
        except Exception as exc:
            self._raise_api_error(
                exc,
                phase="background_resume",
                response_id=response_id,
                latency_ms=int((perf_counter() - started) * 1000),
            )
        if str(getattr(response, "id", "")) != response_id:
            raise Gate2LiveProviderError(
                "background_response_id_mismatch",
                "后台恢复返回了不同的响应ID；拒绝继续",
                response_id=response_id,
                api_status=str(getattr(response, "status", "unknown")),
                latency_ms=int((perf_counter() - started) * 1000),
                background_mode=True,
                poll_count=self.poll_count,
            )
        return self._await_terminal(client, response, started=started)

    def _client(self) -> Any:
        if not os.getenv("OPENAI_API_KEY"):
            raise Gate2LiveProviderError(
                "api_key_missing",
                "OPENAI_API_KEY未进入当前调用进程",
                background_mode=True,
            )
        return self._client_factory(
            timeout=self._request_timeout_seconds,
            max_retries=0,
        )

    def _await_terminal(
        self,
        client: Any,
        response: Any,
        *,
        started: float,
    ) -> Gate2ProviderResult:
        response_id = str(getattr(response, "id", "") or "")
        if not response_id:
            raise Gate2LiveProviderError(
                "background_response_id_missing",
                "后台请求没有返回可恢复的响应ID",
                api_status=str(getattr(response, "status", "unknown")),
                latency_ms=int((perf_counter() - started) * 1000),
                background_mode=True,
            )

        self._record_checkpoint(response, generation_calls=self.call_count)
        status = str(getattr(response, "status", "unknown"))
        while status in _RUNNING_STATUSES:
            if self.poll_count >= self._max_poll_attempts:
                raise Gate2LiveProviderError(
                    "background_poll_limit_reached",
                    f"后台响应仍在运行；已保存响应ID，阶段 {self.stage_label}不创建新请求",
                    response_id=response_id,
                    api_status=status,
                    usage=_usage_from_response(response),
                    latency_ms=int((perf_counter() - started) * 1000),
                    cost_usd=self._known_cost(response),
                    background_mode=True,
                    poll_count=self.poll_count,
                    raw_output=_raw_output_from_response(response),
                )
            self._sleep(self._poll_interval_seconds)
            try:
                response = client.responses.retrieve(response_id)
                self.poll_count += 1
            except Exception as exc:
                self._raise_api_error(
                    exc,
                    phase="background_poll",
                    response_id=response_id,
                    api_status=status,
                    latency_ms=int((perf_counter() - started) * 1000),
                    response_context=response,
                )
            if str(getattr(response, "id", "")) != response_id:
                raise Gate2LiveProviderError(
                    "background_response_id_mismatch",
                    "后台轮询返回了不同的响应ID；拒绝继续",
                    response_id=response_id,
                    api_status=str(getattr(response, "status", "unknown")),
                    latency_ms=int((perf_counter() - started) * 1000),
                    background_mode=True,
                    poll_count=self.poll_count,
                )
            self._record_checkpoint(response, generation_calls=self.call_count)
            status = str(getattr(response, "status", "unknown"))

        if status not in _TERMINAL_STATUSES:
            raise Gate2LiveProviderError(
                "background_unknown_status",
                f"后台响应进入未知状态：{status}"[:800],
                response_id=response_id,
                api_status=status,
                usage=_usage_from_response(response),
                latency_ms=int((perf_counter() - started) * 1000),
                cost_usd=self._known_cost(response),
                background_mode=True,
                poll_count=self.poll_count,
                raw_output=_raw_output_from_response(response),
            )

        usage = _usage_from_response(response)
        cost_usd = self._known_cost(response)
        raw_output = _raw_output_from_response(response)
        incomplete_reason = _incomplete_reason(response)
        if status == "incomplete":
            raise Gate2LiveProviderError(
                "response_incomplete",
                f"OpenAI后台响应不完整；阶段 {self.stage_label}不自动续写或重发",
                response_id=response_id,
                api_status=status,
                incomplete_reason=incomplete_reason,
                usage=usage,
                latency_ms=int((perf_counter() - started) * 1000),
                cost_usd=cost_usd,
                background_mode=True,
                poll_count=self.poll_count,
                raw_output=raw_output,
            )
        if status in {"failed", "cancelled"}:
            raise Gate2LiveProviderError(
                f"background_{status}",
                f"OpenAI后台响应终态为{status}；阶段 {self.stage_label}不自动重发",
                response_id=response_id,
                api_status=status,
                usage=usage,
                latency_ms=int((perf_counter() - started) * 1000),
                cost_usd=cost_usd,
                background_mode=True,
                poll_count=self.poll_count,
                raw_output=raw_output,
            )

        try:
            if raw_output is None or "unparsed_output_text" in raw_output:
                raise ValueError("后台响应没有完整JSON对象")
            parsed = self.output_model.model_validate(raw_output)
        except (ValidationError, ValueError) as exc:
            detail = (
                _safe_validation_detail(exc)
                if isinstance(exc, ValidationError)
                else str(exc)
            )
            raise Gate2LiveProviderError(
                "structured_output_schema_invalid",
                f"OpenAI后台结构化输出未通过阶段 C Schema：{detail}"[:800],
                response_id=response_id,
                api_status=status,
                usage=usage,
                latency_ms=int((perf_counter() - started) * 1000),
                cost_usd=cost_usd,
                background_mode=True,
                poll_count=self.poll_count,
                raw_output=raw_output,
            ) from exc

        return Gate2ProviderResult(
            response_id=response_id,
            provider_name=self.provider_name,
            model=str(getattr(response, "model", self.model)),
            raw_output=parsed.model_dump(mode="json"),
            usage=usage,
            latency_ms=int((perf_counter() - started) * 1000),
            cost_usd=float(cost_usd or 0),
            api_status=status,
            incomplete_reason=incomplete_reason,
            background_mode=True,
            poll_count=self.poll_count,
        )

    def _record_checkpoint(self, response: Any, *, generation_calls: int) -> None:
        if self._on_checkpoint is None:
            return
        status = str(getattr(response, "status", "unknown"))
        checkpoint = Gate2BackgroundCheckpoint(
            response_id=str(getattr(response, "id", "")),
            api_status=status,
            terminal=status in _TERMINAL_STATUSES,
            generation_calls=min(generation_calls, 1),
            poll_count=self.poll_count,
            usage=_usage_from_response(response),
            cost_usd=self._known_cost(response),
            incomplete_reason=_incomplete_reason(response),
        )
        try:
            self._on_checkpoint(checkpoint)
        except Exception as exc:
            raise Gate2LiveProviderError(
                "checkpoint_write_failed",
                f"后台响应ID持久化失败：{type(exc).__name__}",
                response_id=checkpoint.response_id,
                api_status=checkpoint.api_status,
                usage=checkpoint.usage,
                cost_usd=checkpoint.cost_usd,
                background_mode=True,
                poll_count=checkpoint.poll_count,
            ) from exc

    def _known_cost(self, response: Any) -> float | None:
        usage = _usage_from_response(response)
        if usage.total_tokens == 0:
            return None
        return float(self.pricing.calculate(usage))

    def _raise_api_error(
        self,
        exc: Exception,
        *,
        phase: str,
        response_id: str | None = None,
        api_status: str | None = None,
        latency_ms: int = 0,
        response_context: Any | None = None,
    ) -> None:
        common = {
            "response_id": response_id,
            "api_status": api_status,
            "incomplete_reason": (
                _incomplete_reason(response_context)
                if response_context is not None
                else None
            ),
            "usage": (
                _usage_from_response(response_context)
                if response_context is not None
                else Gate2Usage()
            ),
            "latency_ms": latency_ms,
            "cost_usd": (
                self._known_cost(response_context)
                if response_context is not None
                else None
            ),
            "background_mode": True,
            "poll_count": self.poll_count,
            "raw_output": (
                _raw_output_from_response(response_context)
                if response_context is not None
                else None
            ),
        }
        if isinstance(exc, Gate2LiveProviderError):
            raise exc
        if isinstance(exc, AuthenticationError):
            raise Gate2LiveProviderError(
                "authentication_failed", "OpenAI API身份验证失败", **common
            ) from exc
        if isinstance(exc, RateLimitError):
            raise Gate2LiveProviderError(
                "rate_limit", "OpenAI API当前达到速率或额度限制", **common
            ) from exc
        if isinstance(exc, APITimeoutError):
            raise Gate2LiveProviderError(
                f"{phase}_timeout",
                "OpenAI后台请求通信超时；保留已有响应ID，不自动重发",
                **common,
            ) from exc
        if isinstance(exc, APIConnectionError):
            raise Gate2LiveProviderError(
                f"{phase}_connection_failed",
                "OpenAI后台请求连接失败；保留已有响应ID，不自动重发",
                **common,
            ) from exc
        raise Gate2LiveProviderError(
            f"{phase}_error",
                f"OpenAI阶段 {self.stage_label}后台Provider失败：{type(exc).__name__}",
            **common,
        ) from exc
