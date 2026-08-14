from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from abalo_iching.application import sites_direct_reading_v2 as service
from abalo_iching.application.sites_direct_reading_v2 import (
    MAX_OUTPUT_TOKENS,
    MODEL,
    REASONING_EFFORT,
    DirectReadingProvider,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)
from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider
from abalo_iching.meihua.relations import relation_between_body_and_use
from abalo_iching.meihua.seasonal_strength import seasonal_strength_for
from abalo_iching.meihua.trigrams import trigram_from_name


TAIL_HEADINGS = (
    "适合做什么",
    "不适合做什么",
    "反向风险",
    "哪些现实信号会改变判断",
)


@dataclass(frozen=True)
class FrozenStabilityCase:
    slot: int
    case_id: str
    domain: str
    input_type: str
    question_text: str
    numbers: tuple[int, int, int]
    input_sha256: str


@dataclass(frozen=True)
class MechanicalMapping:
    headings: tuple[str, ...]
    page8_model_sections: tuple[str, ...]
    page8_program_strength: dict[str, str]
    page9_model_sections: tuple[str, ...]
    source_sha256: str
    reconstructed_sha256: str
    reconstructed_equals_source: bool
    model_calls_for_render: int = 0
    additional_casts: int = 0


def _executor_failure_row(
    case: FrozenStabilityCase,
    exc: Exception,
    *,
    cast_count: int | None,
    provider_attempts: int,
) -> dict[str, Any]:
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": "EXECUTOR_FAILED",
        "consumed": True,
        "deterministic_cast_count": cast_count,
        "fixed_high_attempts": provider_attempts,
        "provider_attempts": provider_attempts,
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": [f"EXECUTOR:{type(exc).__name__}"],
        "usage": None,
        "usage_unavailable_reason": "EXECUTOR_FAILED",
        "latency_ms": None,
        "latency_unavailable_reason": "EXECUTOR_FAILED",
        "reading_utf8_sha256": None,
        "released_direct_reading": None,
        "mechanical_mapping": None,
    }


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def load_frozen_cases(document: dict[str, Any]) -> tuple[FrozenStabilityCase, ...]:
    cases = tuple(
        FrozenStabilityCase(
            slot=int(row["slot"]),
            case_id=str(row["case_id"]),
            domain=str(row["domain"]),
            input_type=str(row["input_type"]),
            question_text=str(row["question_text"]),
            numbers=tuple(row["numbers"]),
            input_sha256=str(row["input_sha256"]),
        )
        for row in document["cases"]
    )
    if tuple(case.slot for case in cases) != tuple(range(1, len(cases) + 1)):
        raise ValueError("CASE_SLOT_ORDER")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("DUPLICATE_CASE_ID")
    for case in cases:
        payload = {"question_text": case.question_text, "numbers": list(case.numbers)}
        if canonical_sha(payload) != case.input_sha256:
            raise ValueError(f"INPUT_SHA_MISMATCH:{case.case_id}")
    return cases


def _program_strength(prepared: Any) -> dict[str, str]:
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
        prepared.generated_at,
        "Asia/Shanghai",
    )
    return {
        "source": "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH",
        "body_trigram": body_name,
        "initial_use_trigram": initial_use_name,
        "changed_use_trigram": changed_use_name,
        "initial_relation": relation_between_body_and_use(
            body.element, initial_use.element
        ).value,
        "changed_relation": relation_between_body_and_use(
            body.element, changed_use.element
        ).value,
        "body_strength": seasonal_strength_for(body.element, calendar.month_element).value,
    }


def mechanical_mapping(
    text: str,
    chart_facts: dict[str, Any],
    page8_program_strength: dict[str, str],
    expected_source_sha256: str | None = None,
) -> MechanicalMapping:
    base = chart_facts["base_hexagram"]
    mutual = chart_facts["mutual_hexagram"]
    moving = chart_facts["moving_line"]
    changed = chart_facts["changed_hexagram"]
    expected = (
        "判断",
        f"本卦：{base['name']}",
        f"互卦：{mutual['name']}",
        f"动爻：{moving['name']}",
        f"变卦：{changed['name']}",
        *TAIL_HEADINGS,
    )
    parts = tuple(part.rstrip() for part in re.split(r"(?=^## )", text, flags=re.MULTILINE) if part)
    headings = tuple(part.splitlines()[0].removeprefix("## ").strip() for part in parts)
    if headings != expected or any("\n" not in part or not part.split("\n", 1)[1].strip() for part in parts):
        raise ValueError("NINE_SECTION_MAPPING")
    reconstructed = "\n\n".join(parts)
    source_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
    reconstructed_sha = hashlib.sha256(reconstructed.encode("utf-8")).hexdigest().upper()
    if expected_source_sha256 is not None and source_sha != expected_source_sha256:
        raise ValueError("SOURCE_SHA_MISMATCH")
    if reconstructed != text or source_sha != reconstructed_sha:
        raise ValueError("SOURCE_RECONSTRUCTION_MISMATCH")
    return MechanicalMapping(
        headings=headings,
        page8_model_sections=parts[1:5],
        page8_program_strength=page8_program_strength,
        page9_model_sections=(parts[0], *parts[5:9]),
        source_sha256=source_sha,
        reconstructed_sha256=reconstructed_sha,
        reconstructed_equals_source=True,
    )


def execute_case(case: FrozenStabilityCase, provider: DirectReadingProvider) -> dict[str, Any]:
    if MAX_OUTPUT_TOKENS != 12_000 or MODEL != "gpt-5.6-sol" or REASONING_EFFORT != "high":
        raise RuntimeError("FIXED_HIGH_CONFIGURATION_DRIFT")
    payload = {"question_text": case.question_text, "numbers": list(case.numbers)}
    if canonical_sha(payload) != case.input_sha256:
        raise RuntimeError("FROZEN_INPUT_DRIFT")
    cast_count = 0
    original_cast = service.cast_meihua

    def counted_cast(value: Any) -> Any:
        nonlocal cast_count
        cast_count += 1
        return original_cast(value)

    provider_attempts = 0

    class CountingProvider:
        def generate(self, **kwargs: Any) -> Any:
            nonlocal provider_attempts
            provider_attempts += 1
            return provider.generate(**kwargs)

    service.cast_meihua = counted_cast
    try:
        try:
            prepared = prepare_direct_reading_v2_request(payload)
            if isinstance(prepared, dict):
                raise RuntimeError("FROZEN_CASE_PREPARE_FAILED")
            result = process_prepared_direct_reading_v2_request(
                prepared,
                provider=CountingProvider(),
            )
            if cast_count != 1:
                raise RuntimeError(f"CAST_COUNT:{cast_count}")
            if provider_attempts != 1:
                raise RuntimeError(f"PROVIDER_ATTEMPTS:{provider_attempts}")
        except Exception as exc:
            return _executor_failure_row(
                case,
                exc,
                cast_count=cast_count,
                provider_attempts=provider_attempts,
            )
    finally:
        service.cast_meihua = original_cast

    released = result.get("direct_reading") if result["status"] == "SUCCESS" else None
    mapping: MechanicalMapping | None = None
    if released is not None:
        try:
            mapping = mechanical_mapping(
                released["text"],
                prepared.chart_facts.model_dump(mode="json"),
                _program_strength(prepared),
            )
        except (KeyError, TypeError, ValueError) as exc:
            result = {
                **result,
                "status": "MAPPING_FAILED",
                "validation_errors": [f"MECHANICAL_MAPPING:{type(exc).__name__}"],
            }
            released = None
    audit = result["audit"]
    usage = audit.get("usage")
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": result["status"],
        "consumed": True,
        "deterministic_cast_count": cast_count,
        "fixed_high_attempts": 1,
        "provider_attempts": provider_attempts,
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": list(result.get("validation_errors", [])),
        "usage": usage,
        "usage_unavailable_reason": None if usage is not None else "PROVIDER_USAGE_UNAVAILABLE",
        "latency_ms": audit.get("latency_ms"),
        "latency_unavailable_reason": (
            None if audit.get("latency_ms") is not None else "PROVIDER_LATENCY_UNAVAILABLE"
        ),
        "reading_utf8_sha256": mapping.source_sha256 if mapping else None,
        "released_direct_reading": released,
        "mechanical_mapping": mapping.__dict__ if mapping else None,
    }


def run_sequential_batch(
    cases: Sequence[FrozenStabilityCase],
    provider_factory: Callable[[FrozenStabilityCase], DirectReadingProvider],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        try:
            row = execute_case(case, provider_factory(case))
        except Exception as exc:
            row = _executor_failure_row(
                case,
                exc,
                cast_count=None,
                provider_attempts=0,
            )
        rows.append(row)
        if row["status"] != "SUCCESS":
            break
    authorized = len(cases)
    actual = sum(int(row["provider_attempts"]) for row in rows)
    success_count = sum(row["status"] == "SUCCESS" for row in rows)
    return {
        "authorized_case_count": authorized,
        "actual_provider_attempts": actual,
        "remaining_unexecuted": authorized - actual,
        "success_count": success_count,
        "success_denominator": authorized,
        "technical_success_rate": success_count / authorized,
        "stopped_on_first_failure": bool(rows and rows[-1]["status"] != "SUCCESS"),
        "cases": rows,
    }
