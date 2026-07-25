from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_UP

from .models import Gate2PromptPackage, Gate2Usage


PRICING_VERSION = "openai_gpt_5_6_sol_standard_2026_07_21"
PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing"
PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class Gate2TokenPricing:
    model: str = "gpt-5.6-sol"
    input_per_million_usd: Decimal = Decimal("5")
    cached_input_per_million_usd: Decimal = Decimal("0.5")
    cache_write_per_million_usd: Decimal = Decimal("6.25")
    output_per_million_usd: Decimal = Decimal("30")
    version: str = PRICING_VERSION
    source: str = PRICING_SOURCE

    def calculate(self, usage: Gate2Usage) -> Decimal:
        cached = min(usage.cached_input_tokens, usage.input_tokens)
        remaining = usage.input_tokens - cached
        cache_write = min(usage.cache_write_tokens, remaining)
        uncached = remaining - cache_write
        total = (
            Decimal(uncached) * self.input_per_million_usd
            + Decimal(cached) * self.cached_input_per_million_usd
            + Decimal(cache_write) * self.cache_write_per_million_usd
            + Decimal(usage.output_tokens) * self.output_per_million_usd
        ) / PER_MILLION
        return total.quantize(Decimal("0.000001"), rounding=ROUND_UP)

    def conservative_preflight_estimate(
        self,
        prompt: Gate2PromptPackage,
        *,
        max_output_tokens: int,
    ) -> Decimal:
        payload_bytes = len(
            json.dumps(
                prompt.input_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        instruction_bytes = len(prompt.system_instructions.encode("utf-8"))
        schema_bytes = len(
            json.dumps(
                prompt.input_payload.get("output_schema", {}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        # UTF-8 字节数作为输入 token 的保守上界，并增加协议固定开销。
        input_token_upper_bound = payload_bytes + instruction_bytes + schema_bytes + 2048
        total = (
            Decimal(input_token_upper_bound) * self.cache_write_per_million_usd
            + Decimal(max_output_tokens) * self.output_per_million_usd
        ) / PER_MILLION
        return total.quantize(Decimal("0.000001"), rounding=ROUND_UP)
