from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy

from .models import Gate2PromptPackage, Gate2ProviderResult, Gate2Usage


class FakeGate2Provider:
    """无网络 Fake Provider；只返回预先注入的合成结果。"""

    provider_name = "FAKE"

    def __init__(self, outputs: Iterable[dict[str, object] | Exception]) -> None:
        self._outputs = iter(outputs)
        self.call_count = 0
        self.received_prompt_hashes: list[str] = []

    def generate(self, prompt: Gate2PromptPackage) -> Gate2ProviderResult:
        self.call_count += 1
        self.received_prompt_hashes.append(prompt.prompt_sha256)
        try:
            item = next(self._outputs)
        except StopIteration as exc:
            raise RuntimeError("Fake Provider 没有剩余预置输出") from exc
        if isinstance(item, Exception):
            raise item
        return Gate2ProviderResult(
            response_id=f"fake-response-{self.call_count:03d}",
            provider_name=self.provider_name,
            model="fake-structured-model",
            raw_output=deepcopy(item),
            usage=Gate2Usage(),
            latency_ms=0,
            cost_usd=0.0,
        )
