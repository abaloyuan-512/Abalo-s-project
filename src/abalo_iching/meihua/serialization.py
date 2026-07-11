"""Stable JSON serialization and deserialization for MeihuaChart."""

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .enums import (
    BodyUseRelation,
    Element,
    EvidencePolarity,
    EvidenceStrength,
    EvidenceType,
    MovingLineStage,
    SeasonalStrength,
    TimingLevel,
)
from .hexagrams import hexagram_from_number
from .models import (
    BodyUseAssignment,
    ElementSeasonStrength,
    Evidence,
    MeihuaChart,
    MeihuaInput,
    RuleVersions,
    SeasonContext,
    TimingContext,
)
from .trigrams import trigram_from_number


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_primitive(item) for key, item in value.items()}
    return value


def chart_to_dict(chart: MeihuaChart) -> dict[str, Any]:
    if not isinstance(chart, MeihuaChart):
        raise TypeError("chart must be a MeihuaChart")
    return _to_primitive(chart)


def chart_to_json(chart: MeihuaChart, *, indent: int | None = 2) -> str:
    return json.dumps(chart_to_dict(chart), ensure_ascii=False, indent=indent, sort_keys=True)


def chart_from_dict(data: dict[str, Any]) -> MeihuaChart:
    """Deserialize trusted internal data; callers must not pass external JSON here."""
    input_data = data["input"]
    chart_input = MeihuaInput(
        first_number=input_data["first_number"],
        second_number=input_data["second_number"],
        third_number=input_data["third_number"],
        cast_at=datetime.fromisoformat(input_data["cast_at"]),
        timezone_name=input_data["timezone_name"],
        question_id=input_data.get("question_id"),
    )
    body_use_data = data["body_use_assignment"]
    body_use = BodyUseAssignment(
        body_trigram=trigram_from_number(body_use_data["body_trigram"]["number"]),
        initial_use_trigram=trigram_from_number(body_use_data["initial_use_trigram"]["number"]),
        changed_use_trigram=trigram_from_number(body_use_data["changed_use_trigram"]["number"]),
    )
    season_data = data["season_context"]
    element_strengths = tuple(
        ElementSeasonStrength(
            element=Element(item["element"]),
            state=SeasonalStrength(item["state"]),
            label_zh=item["label_zh"],
            rank=item["rank"],
        )
        for item in season_data["element_strengths"]
    )
    season = SeasonContext(
        current_solar_term=season_data["current_solar_term"],
        current_solar_term_started_at=datetime.fromisoformat(season_data["current_solar_term_started_at"]),
        month_branch=season_data["month_branch"],
        month_start_solar_term=season_data["month_start_solar_term"],
        month_element=Element(season_data["month_element"]),
        element_strengths=element_strengths,
        body_strength=SeasonalStrength(season_data["body_strength"]),
        initial_use_strength=SeasonalStrength(season_data["initial_use_strength"]),
        changed_use_strength=SeasonalStrength(season_data["changed_use_strength"]),
    )
    evidence = tuple(
        Evidence(
            evidence_id=item["evidence_id"],
            evidence_type=EvidenceType(item["evidence_type"]),
            source_ref=item["source_ref"],
            polarity=EvidencePolarity(item["polarity"]),
            strength=EvidenceStrength(item["strength"]),
            fact=item["fact"],
            rule_statement=item["rule_statement"],
            data_version=item["data_version"],
        )
        for item in data["evidence"]
    )
    timing_data = data["timing"]
    versions_data = data["versions"]
    return MeihuaChart(
        input=chart_input,
        upper_trigram=trigram_from_number(data["upper_trigram"]["number"]),
        lower_trigram=trigram_from_number(data["lower_trigram"]["number"]),
        moving_line=data["moving_line"],
        base_hexagram=hexagram_from_number(data["base_hexagram"]["king_wen_number"]),
        mutual_hexagram=hexagram_from_number(data["mutual_hexagram"]["king_wen_number"]),
        changed_hexagram=hexagram_from_number(data["changed_hexagram"]["king_wen_number"]),
        body_use_assignment=body_use,
        initial_body_use_relation=BodyUseRelation(data["initial_body_use_relation"]),
        changed_body_use_relation=BodyUseRelation(data["changed_body_use_relation"]),
        mutual_lower_to_body_relation=BodyUseRelation(data["mutual_lower_to_body_relation"]),
        mutual_upper_to_body_relation=BodyUseRelation(data["mutual_upper_to_body_relation"]),
        moving_line_stage=MovingLineStage(data["moving_line_stage"]),
        season_context=season,
        evidence=evidence,
        timing=TimingContext(
            exact_date_feature_enabled=timing_data["exact_date_feature_enabled"],
            level=TimingLevel(timing_data["level"]),
            candidate_dates=tuple(timing_data["candidate_dates"]),
        ),
        versions=RuleVersions(**versions_data),
    )


def chart_from_json(payload: str) -> MeihuaChart:
    """Deserialize trusted internal JSON; preserved for Phase 1 compatibility."""
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise TypeError("Serialized chart must be a JSON object")
    return chart_from_dict(data)


chart_from_dict_trusted = chart_from_dict
chart_from_json_trusted = chart_from_json


def chart_from_untrusted_json(payload: str) -> MeihuaChart:
    """Reject externally supplied derived facts unless they exactly match a fresh deterministic cast."""
    from .engine import cast_meihua
    from .exceptions import InputValidationError

    try:
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get("input"), dict):
            raise InputValidationError("External chart payload must contain an input object")
        input_data = data["input"]
        chart_input = MeihuaInput(
            first_number=input_data["first_number"],
            second_number=input_data["second_number"],
            third_number=input_data["third_number"],
            cast_at=datetime.fromisoformat(input_data["cast_at"]),
            timezone_name=input_data["timezone_name"],
            question_id=input_data.get("question_id"),
        )
        recomputed = cast_meihua(chart_input)
    except InputValidationError:
        raise
    except Exception as exc:
        raise InputValidationError("External chart payload is malformed") from exc
    if chart_to_dict(recomputed) != data:
        raise InputValidationError("External chart payload contains forged or inconsistent derived fields")
    return recomputed
