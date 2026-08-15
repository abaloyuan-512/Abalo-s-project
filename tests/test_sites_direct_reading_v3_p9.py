from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application.sites_direct_reading_v3 import (
    MODEL,
    DirectReadingProviderResult,
    DirectReadingUsage,
    process_direct_reading_v2_request,
    public_direct_reading_payload,
)
from tests.test_sites_direct_reading_v2 import _complete_text


FINALE = "\n\n## 观象寄语\n\n可以开始寻找新的承接，但不宜冲动离开。\n先核实职责、资源与缓冲，再决定是否转换。"
FIXED_CLOCK = lambda: datetime(2026, 8, 16, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


class Provider:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls = 0

    def generate(self, **_kwargs) -> DirectReadingProviderResult:
        self.calls += 1
        return DirectReadingProviderResult(
            output_text=self.output_text,
            api_status="completed",
            incomplete_details=None,
            response_id="resp-v3-p9",
            model=MODEL,
            usage=DirectReadingUsage(input_tokens=200, output_tokens=2_000, total_tokens=2_200),
            latency_ms=1,
        )


def run(output_text: str) -> tuple[dict, Provider]:
    provider = Provider(output_text)
    result = process_direct_reading_v2_request(
        {"question_text": "我要不要考虑换工作这件事？", "numbers": [5, 6, 3]},
        provider=provider,
        clock=FIXED_CLOCK,
        request_id="drv2-v3p9finale0000",
    )
    return result, provider


def test_v3_releases_nine_section_reading_and_two_line_p9_from_one_call() -> None:
    result, provider = run(_complete_text() + FINALE)

    assert provider.calls == 1
    assert result["status"] == "SUCCESS"
    assert "观象寄语" not in result["direct_reading"]["text"]
    assert result["page9_finale"] == {
        "content_version": "GUANXIANG_P9_FINALE_V1",
        "source": "SAME_PROVIDER_OUTPUT",
        "answer": ["可以开始寻找新的承接，但不宜冲动离开。", "先核实职责、资源与缓冲，再决定是否转换。"],
        "additional_model_calls": 0,
    }
    public = public_direct_reading_payload(result)
    assert public["page9_finale"] == result["page9_finale"]
    assert "audit" not in public


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "\n\n## 观象寄语\n\n只有一句。",
        "\n\n## 观象寄语\n\n2026年9月1日一定成功。\n立刻行动。",
    ],
)
def test_v3_fails_closed_without_a_valid_safe_finale(suffix: str) -> None:
    result, provider = run(_complete_text() + suffix)

    assert provider.calls == 1
    assert result["status"] == "BLOCKED_OUTPUT"
    assert result["direct_reading"] is None
    assert result["page9_finale"] is None
    assert result["validation_errors"]
