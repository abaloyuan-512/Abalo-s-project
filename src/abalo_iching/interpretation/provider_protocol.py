"""Provider abstraction used by offline tests and the live adapter."""

from typing import Protocol

from .models import PromptPackage, ProviderResult


class InterpretationProvider(Protocol):
    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult: ...
