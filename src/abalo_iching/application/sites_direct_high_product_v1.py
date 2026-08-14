"""Offline product projection for Direct Reading V2 page 8 and page 9.

This module never casts and never calls a model.  It only projects one
already-prepared deterministic request and one released nine-section reading
into typed page responsibilities.  Page 8 keeps the four model sections next
to facts from the same prepared chart; its fifth scene is program-only.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingProvider,
    DirectReadingPreparedRequest,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)
from abalo_iching.application.sites_question_context_v1 import normalize_question_text
from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider
from abalo_iching.meihua.relations import relation_between_body_and_use
from abalo_iching.meihua.seasonal_strength import seasonal_strength_for
from abalo_iching.meihua.trigrams import trigram_from_name


PRODUCT_CONTRACT_VERSION = "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1"
PROGRAM_STRENGTH_SOURCE = "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH"
_HEADING = re.compile(r"(?m)^## ([^\r\n]+)(?:\r?\n)")
_TAIL_HEADINGS = (
    "适合做什么",
    "不适合做什么",
    "反向风险",
    "哪些现实信号会改变判断",
)


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _canonical_sha(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


class StrictProductModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DirectHighEntryMode(StrEnum):
    CLEAR = "CLEAR"
    CONFIRMED = "CONFIRMED"
    SKIP = "SKIP"


class SourceSectionV1(StrictProductModel):
    heading: str
    markdown: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9A-F]{64}$")

    @model_validator(mode="after")
    def offsets_match(self) -> SourceSectionV1:
        if self.end_offset <= self.start_offset:
            raise ValueError("SECTION_OFFSET_ORDER")
        if _sha_text(self.markdown) != self.sha256:
            raise ValueError("SECTION_SHA_MISMATCH")
        return self


class HexagramProgramFactV1(StrictProductModel):
    source: Literal["SAME_PREPARED_CHART"] = "SAME_PREPARED_CHART"
    role: Literal["BASE", "MUTUAL", "CHANGED"]
    king_wen_number: int = Field(ge=1, le=64)
    name: str
    upper_trigram: str
    lower_trigram: str


class MovingLineProgramFactV1(StrictProductModel):
    source: Literal["SAME_PREPARED_CHART"] = "SAME_PREPARED_CHART"
    position: int = Field(ge=1, le=6)
    name: str
    canonical_line_text: str
    canonical_data_version: str


class ProgramStrengthV1(StrictProductModel):
    source: Literal[PROGRAM_STRENGTH_SOURCE] = PROGRAM_STRENGTH_SOURCE
    body_trigram: str
    initial_use_trigram: str
    changed_use_trigram: str
    initial_relation: str
    changed_relation: str
    body_strength: str
    program_fact_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")


class HexagramPage8SceneV1(StrictProductModel):
    program_fact: HexagramProgramFactV1
    model_section: SourceSectionV1


class MovingLinePage8SceneV1(StrictProductModel):
    program_fact: MovingLineProgramFactV1
    model_section: SourceSectionV1


class Page8ProductV1(StrictProductModel):
    responsibility: Literal["BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH"] = (
        "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH"
    )
    base_hexagram: HexagramPage8SceneV1
    mutual_hexagram: HexagramPage8SceneV1
    moving_line: MovingLinePage8SceneV1
    changed_hexagram: HexagramPage8SceneV1
    program_strength: ProgramStrengthV1
    model_calls_for_mapping: Literal[0] = 0
    additional_casts_for_mapping: Literal[0] = 0


class Page9ProductV1(StrictProductModel):
    responsibility: Literal["JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS"] = (
        "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS"
    )
    judgment: SourceSectionV1
    suitable_actions: SourceSectionV1
    unsuitable_actions: SourceSectionV1
    reverse_risk: SourceSectionV1
    change_signals: SourceSectionV1
    model_calls_for_mapping: Literal[0] = 0
    additional_casts_for_mapping: Literal[0] = 0


class DirectHighProductPresentationV1(StrictProductModel):
    contract_version: Literal[PRODUCT_CONTRACT_VERSION] = PRODUCT_CONTRACT_VERSION
    source_reading_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    reconstructed_reading_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    reconstructed_equals_source: Literal[True] = True
    prepared_chart_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    page8: Page8ProductV1
    page9: Page9ProductV1


class DirectHighProductAuditV1(StrictProductModel):
    entry_mode: DirectHighEntryMode
    original_question_sha256_before: str = Field(pattern=r"^[0-9A-F]{64}$")
    original_question_sha256_sent: str = Field(pattern=r"^[0-9A-F]{64}$")
    original_question_sha256_after: str = Field(pattern=r"^[0-9A-F]{64}$")
    original_question_preserved: Literal[True] = True
    prepare_attempts: Literal[1] = 1
    deterministic_cast_count: Literal[1] = 1
    fixed_high_attempts: Literal[1] = 1
    provider_attempts: Literal[1] = 1
    automatic_retries: Literal[0] = 0
    router_attempts: Literal[0] = 0
    router_live_calls: Literal[0] = 0
    router_model_calls: Literal[0] = 0


class DirectHighProductResultV1(StrictProductModel):
    contract_version: Literal[PRODUCT_CONTRACT_VERSION] = PRODUCT_CONTRACT_VERSION
    status: str
    released: bool
    direct_reading: dict[str, Any] | None = None
    presentation: DirectHighProductPresentationV1 | None = None
    product_audit: DirectHighProductAuditV1
    validation_errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def release_is_atomic(self) -> DirectHighProductResultV1:
        if self.released != (
            self.status == "SUCCESS"
            and self.direct_reading is not None
            and self.presentation is not None
            and not self.validation_errors
        ):
            raise ValueError("PRODUCT_RELEASE_INVARIANT")
        return self


def _program_strength(prepared: DirectReadingPreparedRequest) -> ProgramStrengthV1:
    facts = prepared.chart_facts
    base = facts.base_hexagram
    changed = facts.changed_hexagram
    if facts.moving_line.position <= 3:
        body_name, initial_use_name, changed_use_name = (
            base.upper_trigram,
            base.lower_trigram,
            changed.lower_trigram,
        )
    else:
        body_name, initial_use_name, changed_use_name = (
            base.lower_trigram,
            base.upper_trigram,
            changed.upper_trigram,
        )
    body = trigram_from_name(body_name)
    initial_use = trigram_from_name(initial_use_name)
    changed_use = trigram_from_name(changed_use_name)
    calendar = LunarPythonCalendarProvider().get_calendar_snapshot(
        prepared.generated_at, "Asia/Shanghai"
    )
    values = {
        "source": PROGRAM_STRENGTH_SOURCE,
        "body_trigram": body_name,
        "initial_use_trigram": initial_use_name,
        "changed_use_trigram": changed_use_name,
        "initial_relation": relation_between_body_and_use(
            body.element, initial_use.element
        ).value,
        "changed_relation": relation_between_body_and_use(
            body.element, changed_use.element
        ).value,
        "body_strength": seasonal_strength_for(
            body.element, calendar.month_element
        ).value,
    }
    return ProgramStrengthV1(**values, program_fact_sha256=_canonical_sha(values))


def _sections(text: str, expected: tuple[str, ...]) -> tuple[SourceSectionV1, ...]:
    matches = tuple(_HEADING.finditer(text))
    if len(matches) != len(expected) or not matches or matches[0].start() != 0:
        raise ValueError("NINE_SECTION_MAPPING")
    sections: list[SourceSectionV1] = []
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        if heading != expected[index]:
            raise ValueError("NINE_SECTION_MAPPING")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        markdown = text[match.start() : end]
        body = text[match.end() : end]
        if not body.strip():
            raise ValueError("EMPTY_SECTION")
        sections.append(
            SourceSectionV1(
                heading=heading,
                markdown=markdown,
                start_offset=match.start(),
                end_offset=end,
                sha256=_sha_text(markdown),
            )
        )
    if "".join(section.markdown for section in sections) != text:
        raise ValueError("SOURCE_RECONSTRUCTION_MISMATCH")
    return tuple(sections)


def build_direct_high_product_presentation(
    prepared: DirectReadingPreparedRequest,
    direct_response: dict[str, Any],
) -> DirectHighProductPresentationV1:
    """Project one released reading without a cast or model call."""
    if direct_response.get("status") != "SUCCESS":
        raise ValueError("DIRECT_READING_NOT_RELEASED")
    reading = direct_response.get("direct_reading")
    if not isinstance(reading, dict) or reading.get("validation_status") != "PASSED":
        raise ValueError("DIRECT_READING_NOT_RELEASED")
    text = reading.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("DIRECT_READING_TEXT_MISSING")
    facts = reading.get("chart_facts")
    expected_facts = prepared.chart_facts.model_dump(mode="json")
    if facts != expected_facts:
        raise ValueError("PRESENTATION_CHART_LINEAGE_MISMATCH")

    base = prepared.chart_facts.base_hexagram
    mutual = prepared.chart_facts.mutual_hexagram
    moving = prepared.chart_facts.moving_line
    changed = prepared.chart_facts.changed_hexagram
    expected = (
        "判断",
        f"本卦：{base.name}",
        f"互卦：{mutual.name}",
        f"动爻：{moving.name}",
        f"变卦：{changed.name}",
        *_TAIL_HEADINGS,
    )
    parts = _sections(text, expected)
    reconstructed = "".join(part.markdown for part in parts)
    source_sha = _sha_text(text)
    reconstructed_sha = _sha_text(reconstructed)
    if source_sha != reconstructed_sha or reconstructed != text:
        raise ValueError("SOURCE_RECONSTRUCTION_MISMATCH")

    def hex_fact(value: Any) -> HexagramProgramFactV1:
        return HexagramProgramFactV1(**value.model_dump(mode="json"))

    page8 = Page8ProductV1(
        base_hexagram=HexagramPage8SceneV1(
            program_fact=hex_fact(base), model_section=parts[1]
        ),
        mutual_hexagram=HexagramPage8SceneV1(
            program_fact=hex_fact(mutual), model_section=parts[2]
        ),
        moving_line=MovingLinePage8SceneV1(
            program_fact=MovingLineProgramFactV1(
                source="SAME_PREPARED_CHART", **moving.model_dump(mode="json")
            ),
            model_section=parts[3],
        ),
        changed_hexagram=HexagramPage8SceneV1(
            program_fact=hex_fact(changed), model_section=parts[4]
        ),
        program_strength=_program_strength(prepared),
    )
    page9 = Page9ProductV1(
        judgment=parts[0],
        suitable_actions=parts[5],
        unsuitable_actions=parts[6],
        reverse_risk=parts[7],
        change_signals=parts[8],
    )
    return DirectHighProductPresentationV1(
        source_reading_sha256=source_sha,
        reconstructed_reading_sha256=reconstructed_sha,
        prepared_chart_sha256=_canonical_sha(
            prepared.chart_facts.model_dump(mode="json")
        ),
        page8=page8,
        page9=page9,
    )


def process_direct_high_product_request(
    *,
    entry_mode: DirectHighEntryMode,
    original_question: str,
    numbers: tuple[int, int, int],
    provider: DirectReadingProvider,
    clock: Any = None,
    request_id: str | None = None,
) -> DirectHighProductResultV1:
    """Run one direct-high transaction: one prepare/cast and one provider call."""
    if type(original_question) is not str:
        raise ValueError("ORIGINAL_QUESTION_TYPE")
    if normalize_question_text(original_question) != original_question:
        raise ValueError("ORIGINAL_QUESTION_MUST_BE_CANONICAL")
    question_sha = _sha_text(original_question)
    prepared = prepare_direct_reading_v2_request(
        {"question_text": original_question, "numbers": numbers},
        clock=clock,
        request_id=request_id,
    )
    if isinstance(prepared, dict):
        raise ValueError("DIRECT_HIGH_PREPARE_FAILED")
    if prepared.request.question_text != original_question:
        raise ValueError("ORIGINAL_QUESTION_CHANGED")
    response = process_prepared_direct_reading_v2_request(prepared, provider=provider)
    validation_errors = list(response.get("validation_errors") or [])
    presentation: DirectHighProductPresentationV1 | None = None
    if response.get("status") == "SUCCESS":
        try:
            presentation = build_direct_high_product_presentation(prepared, response)
        except (TypeError, ValueError):
            validation_errors.append("P8_P9_PRODUCT_MAPPING_FAILED")
            response = {**response, "status": "BLOCKED_OUTPUT"}
    released = (
        response.get("status") == "SUCCESS"
        and presentation is not None
        and not validation_errors
    )
    reading = response.get("direct_reading") if released else None
    after_sha = _sha_text(prepared.request.question_text)
    return DirectHighProductResultV1(
        status=str(response.get("status", "UNAVAILABLE")),
        released=released,
        direct_reading=reading if isinstance(reading, dict) else None,
        presentation=presentation,
        product_audit=DirectHighProductAuditV1(
            entry_mode=entry_mode,
            original_question_sha256_before=question_sha,
            original_question_sha256_sent=prepared.question_sha256,
            original_question_sha256_after=after_sha,
        ),
        validation_errors=validation_errors,
    )


__all__ = [
    "DirectHighEntryMode",
    "DirectHighProductPresentationV1",
    "DirectHighProductResultV1",
    "PRODUCT_CONTRACT_VERSION",
    "PROGRAM_STRENGTH_SOURCE",
    "build_direct_high_product_presentation",
    "process_direct_high_product_request",
]
