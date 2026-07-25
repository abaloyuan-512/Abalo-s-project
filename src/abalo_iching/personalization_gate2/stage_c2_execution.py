from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import httpx
from openai import OpenAI

from .background_provider import OpenAIGate2BackgroundProvider
from .background_runner import Gate2BackgroundCalibrationRunner
from .budget import Gate2CalibrationBudgetGuard
from .stage_c2_contract import (
    STAGE_C2_SCHEMA_VERSION,
    Gate2ExperimentOutputV3,
    Gate2StageC2PromptBuilder,
    Gate2StageC2Validator,
    gate2_output_schema_v3_sha256,
    gate2_validator_v4_sha256,
)


class OfflineGate2StageC2BackgroundProvider(OpenAIGate2BackgroundProvider):
    """只接受注入客户端的 C.2 后台模拟 Provider；没有真实网络默认值。"""

    provider_name = "OFFLINE_SIMULATED_RESPONSES_API_GATE2_STAGE_C2"
    output_model = Gate2ExperimentOutputV3
    stage_label = "C.2"
    offline_simulation = True

    def __init__(
        self,
        *,
        client_factory: Callable[..., Any],
        **kwargs: Any,
    ) -> None:
        if client_factory is OpenAI:
            raise ValueError("阶段 C.2离线Provider禁止使用默认OpenAI网络客户端")
        super().__init__(client_factory=client_factory, **kwargs)

    def _client(self) -> Any:
        client = self._client_factory(
            timeout=self._request_timeout_seconds,
            max_retries=0,
        )
        if isinstance(client, OpenAI):
            http_client = getattr(client, "_client", None)
            transport = getattr(http_client, "_transport", None)
            if not isinstance(transport, httpx.MockTransport):
                client.close()
                raise ValueError(
                    "阶段 C.2离线Provider只允许使用httpx.MockTransport的OpenAI客户端"
                )
        return client

    def _known_cost(self, response: Any) -> float:
        return 0.0


class Gate2StageC2OfflineBackgroundRunner(Gate2BackgroundCalibrationRunner):
    """C.2零美元后台执行链路；只接受离线模拟 Provider。"""

    stage_label = "C.2"
    provider_type: ClassVar[type[OpenAIGate2BackgroundProvider]] = (
        OfflineGate2StageC2BackgroundProvider
    )
    output_model = Gate2ExperimentOutputV3
    schema_version = STAGE_C2_SCHEMA_VERSION
    schema_sha256_factory = staticmethod(gate2_output_schema_v3_sha256)
    validator_sha256_factory = staticmethod(gate2_validator_v4_sha256)
    offline_only = True

    def __init__(self, *, repository_root: Path) -> None:
        super().__init__(
            repository_root=repository_root,
            budget_guard=Gate2CalibrationBudgetGuard(
                declared_account_balance_usd=Decimal("0"),
                authorized_spend_usd=Decimal("0"),
                required_reserve_usd=Decimal("0"),
            ),
            prompt_builder=Gate2StageC2PromptBuilder(),
            validator=Gate2StageC2Validator(),
        )


class OpenAIGate2StageC2BackgroundProvider(OpenAIGate2BackgroundProvider):
    """C.2真实后台Provider；只能由显式授权入口调用。"""

    provider_name = "OPENAI_RESPONSES_API_GATE2_STAGE_C2_BACKGROUND"
    output_model = Gate2ExperimentOutputV3
    stage_label = "C.2"


class Gate2StageC2BackgroundRunner(Gate2BackgroundCalibrationRunner):
    """C.2真实后台Runner；预算和授权由外层入口硬门控制。"""

    stage_label = "C.2"
    provider_type: ClassVar[type[OpenAIGate2BackgroundProvider]] = (
        OpenAIGate2StageC2BackgroundProvider
    )
    output_model = Gate2ExperimentOutputV3
    schema_version = STAGE_C2_SCHEMA_VERSION
    schema_sha256_factory = staticmethod(gate2_output_schema_v3_sha256)
    validator_sha256_factory = staticmethod(gate2_validator_v4_sha256)

    def __init__(
        self,
        *,
        repository_root: Path,
        budget_guard: Gate2CalibrationBudgetGuard,
    ) -> None:
        super().__init__(
            repository_root=repository_root,
            budget_guard=budget_guard,
            prompt_builder=Gate2StageC2PromptBuilder(),
            validator=Gate2StageC2Validator(),
        )
