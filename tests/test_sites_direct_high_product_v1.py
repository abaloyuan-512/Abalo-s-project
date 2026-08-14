from __future__ import annotations

import ast
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_direct_high_product_v1 import (
    PROGRAM_STRENGTH_SOURCE,
    DirectHighEntryMode,
    build_direct_high_product_presentation,
    process_direct_high_product_request,
)
from abalo_iching.application.sites_direct_reading_v2 import (
    MODEL,
    DirectReadingProviderResult,
    DirectReadingUsage,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)


FIXED_CLOCK = lambda: datetime(2026, 8, 11, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
QUESTION = "我要不要考虑换工作这件事？"


def frozen_success() -> tuple[dict, str]:
    ledger = json.loads(Path("outputs/v011_stability_run_ledger.json").read_text(encoding="utf-8"))
    released = copy.deepcopy(ledger["cases"][0]["released_direct_reading"])
    return released, released["text"]


class Provider:
    def __init__(self, text: str, *, fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls = 0

    def generate(self, **_kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture failure")
        return DirectReadingProviderResult(
            output_text=self.text,
            api_status="completed",
            incomplete_details=None,
            response_id="fixture-response",
            model=MODEL,
            usage=DirectReadingUsage(input_tokens=10, output_tokens=100, total_tokens=110),
            latency_ms=1,
        )


def prepared_and_response():
    released, text = frozen_success()
    prepared = prepare_direct_reading_v2_request(
        {"question_text": ledger_question(), "numbers": [38, 71, 24]},
        clock=FIXED_CLOCK,
        request_id="drv2-aaaaaaaaaaaaaaaa",
    )
    assert prepared.chart_facts.model_dump(mode="json") == released["chart_facts"]
    response = {"status": "SUCCESS", "direct_reading": released, "validation_errors": []}
    return prepared, response, text


def ledger_question() -> str:
    ledger = json.loads(Path("evals/meihua/direct_reading_v2_stability_v010/frozen_cases.json").read_text(encoding="utf-8"))
    return ledger["cases"][0]["question_text"]


def test_mechanical_p8_p9_projection_is_byte_exact_and_program_fifth_scene() -> None:
    prepared, response, text = prepared_and_response()
    product = build_direct_high_product_presentation(prepared, response)

    sections = [
        product.page9.judgment,
        product.page8.base_hexagram.model_section,
        product.page8.mutual_hexagram.model_section,
        product.page8.moving_line.model_section,
        product.page8.changed_hexagram.model_section,
        product.page9.suitable_actions,
        product.page9.unsuitable_actions,
        product.page9.reverse_risk,
        product.page9.change_signals,
    ]
    assert "".join(section.markdown for section in sections) == text
    assert product.source_reading_sha256 == hashlib.sha256(text.encode()).hexdigest().upper()
    assert product.reconstructed_reading_sha256 == product.source_reading_sha256
    assert all(text[item.start_offset:item.end_offset] == item.markdown for item in sections)
    assert product.page8.program_strength.source == PROGRAM_STRENGTH_SOURCE
    assert product.page8.model_calls_for_mapping == product.page8.additional_casts_for_mapping == 0
    assert product.page9.model_calls_for_mapping == product.page9.additional_casts_for_mapping == 0
    assert not hasattr(product.page8, "judgment")
    assert not hasattr(product.page9, "base_hexagram")


def test_v009_quality_anchor_maps_byte_exact_with_current_presenter() -> None:
    anchor = json.loads(Path("outputs/v009_canary_real_result.json").read_text(encoding="utf-8"))
    prepared = prepare_direct_reading_v2_request(
        {
            "question_text": anchor["input"]["question_text"],
            "numbers": anchor["input"]["numbers"],
        },
        clock=FIXED_CLOCK,
        request_id="drv2-v009anchor000000",
    )
    assert prepared.chart_facts.model_dump(mode="json") == anchor["chart_facts"]
    product = build_direct_high_product_presentation(
        prepared,
        {"status": "SUCCESS", "direct_reading": anchor["direct_reading"], "validation_errors": []},
    )
    assert product.source_reading_sha256 == anchor["reading_utf8_sha256"]
    assert product.reconstructed_reading_sha256 == "40376C23B51D91A36049242A3DCE24C2FD97C14AC57EBB17B0AD56AC3FF0CAAD"
    assert product.page8.responsibility == "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH"
    assert product.page9.responsibility == "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS"


@pytest.mark.parametrize("mode", tuple(DirectHighEntryMode))
def test_three_entry_modes_are_one_cast_one_high_zero_router(monkeypatch, mode) -> None:
    original = high_service.cast_meihua
    casts = 0

    def counted(value):
        nonlocal casts
        casts += 1
        return original(value)

    monkeypatch.setattr(high_service, "cast_meihua", counted)
    pre = prepare_direct_reading_v2_request(
        {"question_text": ledger_question(), "numbers": [38, 71, 24]}, clock=FIXED_CLOCK
    )
    _released, text = frozen_success()
    casts = 0
    provider = Provider(text)
    result = process_direct_high_product_request(
        entry_mode=mode,
        original_question=ledger_question(),
        numbers=(38, 71, 24),
        provider=provider,
        clock=FIXED_CLOCK,
        request_id=f"drv2-{mode.value.lower():0<16}",
    )
    assert result.released is True
    assert casts == provider.calls == 1
    assert result.product_audit.entry_mode is mode
    assert result.product_audit.router_attempts == result.product_audit.router_model_calls == 0
    assert result.product_audit.original_question_sha256_before == result.product_audit.original_question_sha256_sent == result.product_audit.original_question_sha256_after


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reordered", "lineage"])
def test_mapping_failures_release_no_pages(mutation: str) -> None:
    prepared, response, _text = prepared_and_response()
    if mutation == "missing":
        response["direct_reading"]["text"] = response["direct_reading"]["text"].replace("## 反向风险", "### 反向风险")
    elif mutation == "duplicate":
        response["direct_reading"]["text"] += "\n\n## 判断\n\n重复"
    elif mutation == "reordered":
        response["direct_reading"]["text"] = response["direct_reading"]["text"].replace("## 判断", "## 适合做什么", 1)
    else:
        response["direct_reading"]["chart_facts"]["base_hexagram"]["name"] = "离线伪盘"
    with pytest.raises(ValueError):
        build_direct_high_product_presentation(prepared, response)


def test_provider_failure_is_one_attempt_and_releases_no_pages() -> None:
    provider = Provider("", fail=True)
    result = process_direct_high_product_request(
        entry_mode=DirectHighEntryMode.CLEAR,
        original_question=QUESTION,
        numbers=(5, 6, 3),
        provider=provider,
        clock=FIXED_CLOCK,
    )
    assert provider.calls == 1
    assert result.status == "UNAVAILABLE"
    assert result.released is False
    assert result.direct_reading is result.presentation is None
    assert result.product_audit.automatic_retries == 0


def test_product_module_has_no_router_or_model_provider_imports() -> None:
    source_path = Path("src/abalo_iching/application/sites_direct_high_product_v1.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any("router" in name.lower() for name in imports)
    assert "OpenAI" not in source
    assert "cast_meihua" not in source
