from __future__ import annotations

from typing import Protocol

from .models import Gate2PromptPackage, Gate2ProviderResult


class Gate2Provider(Protocol):
    provider_name: str

    def generate(self, prompt: Gate2PromptPackage) -> Gate2ProviderResult:
        """返回一次原始结构化输出；实验运行器不会自动重试或修复。"""
