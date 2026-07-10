"""Phase 1 deterministic Meihua Yishu chart construction."""

from .calendar_provider import CalendarProvider, LunarPythonCalendarProvider
from .enums import MovingLineStage
from .evidence import build_evidence
from .hexagrams import hexagram_from_lines
from .models import BodyUseAssignment, MeihuaChart, MeihuaInput, RuleVersions, TimingContext
from .relations import relation_between_body_and_use
from .seasonal_strength import build_season_context
from .trigrams import mod_one_based, trigram_from_cast_number, validate_cast_numbers

RULE_VERSION = "MEIHUA_RULE_SPEC_V1"
ENGINE_VERSION = "MEIHUA_ENGINE_PHASE1_V1"

_MOVING_STAGE = {
    1: MovingLineStage.GERMINATION,
    2: MovingLineStage.EARLY_FORMATION,
    3: MovingLineStage.INTERNAL_THRESHOLD,
    4: MovingLineStage.EXTERNAL_TURNING_POINT,
    5: MovingLineStage.CORE_DECISION,
    6: MovingLineStage.CLOSING_OR_EXCESS,
}


def cast_meihua(
    chart_input: MeihuaInput,
    calendar_provider: CalendarProvider | None = None,
) -> MeihuaChart:
    """Calculate a complete Phase 1 chart without AI or non-deterministic steps."""
    if not isinstance(chart_input, MeihuaInput):
        from .exceptions import InputValidationError

        raise InputValidationError("chart_input must be a MeihuaInput")
    validate_cast_numbers(chart_input.first_number, chart_input.second_number, chart_input.third_number)

    provider = calendar_provider or LunarPythonCalendarProvider()
    calendar = provider.get_calendar_snapshot(chart_input.cast_at, chart_input.timezone_name)
    normalized_input = MeihuaInput(
        first_number=chart_input.first_number,
        second_number=chart_input.second_number,
        third_number=chart_input.third_number,
        cast_at=calendar.normalized_cast_at,
        timezone_name=chart_input.timezone_name,
        question_id=chart_input.question_id,
    )

    upper = trigram_from_cast_number(chart_input.first_number)
    lower = trigram_from_cast_number(chart_input.second_number)
    moving_line = mod_one_based(chart_input.third_number, 6)
    base_lines = lower.lines_bottom_up + upper.lines_bottom_up
    base_hexagram = hexagram_from_lines(base_lines)

    mutual_lower_lines = base_lines[1:4]
    mutual_upper_lines = base_lines[2:5]
    mutual_hexagram = hexagram_from_lines(mutual_lower_lines + mutual_upper_lines)

    changed_lines = list(base_lines)
    changed_lines[moving_line - 1] ^= 1
    changed_hexagram = hexagram_from_lines(changed_lines)

    if moving_line <= 3:
        body = upper
        initial_use = lower
        changed_use = changed_hexagram.lower_trigram
    else:
        body = lower
        initial_use = upper
        changed_use = changed_hexagram.upper_trigram
    body_use = BodyUseAssignment(body, initial_use, changed_use)

    initial_relation = relation_between_body_and_use(body.element, initial_use.element)
    changed_relation = relation_between_body_and_use(body.element, changed_use.element)
    mutual_lower_relation = relation_between_body_and_use(body.element, mutual_hexagram.lower_trigram.element)
    mutual_upper_relation = relation_between_body_and_use(body.element, mutual_hexagram.upper_trigram.element)
    moving_stage = _MOVING_STAGE[moving_line]

    season = build_season_context(
        calendar,
        body.element,
        initial_use.element,
        changed_use.element,
    )
    evidence = build_evidence(
        base_hexagram,
        body_use,
        initial_relation,
        changed_relation,
        mutual_lower_relation,
        mutual_upper_relation,
        moving_line,
        moving_stage,
        season,
    )
    versions = RuleVersions(
        rule_version=RULE_VERSION,
        trigram_data_version=upper.data_version,
        hexagram_data_version=base_hexagram.data_version,
        calendar_provider=calendar.provider_version,
        engine_version=ENGINE_VERSION,
    )
    return MeihuaChart(
        input=normalized_input,
        upper_trigram=upper,
        lower_trigram=lower,
        moving_line=moving_line,
        base_hexagram=base_hexagram,
        mutual_hexagram=mutual_hexagram,
        changed_hexagram=changed_hexagram,
        body_use_assignment=body_use,
        initial_body_use_relation=initial_relation,
        changed_body_use_relation=changed_relation,
        mutual_lower_to_body_relation=mutual_lower_relation,
        mutual_upper_to_body_relation=mutual_upper_relation,
        moving_line_stage=moving_stage,
        season_context=season,
        evidence=evidence,
        timing=TimingContext(),
        versions=versions,
    )
