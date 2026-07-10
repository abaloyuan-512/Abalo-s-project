"""Deterministic 旺相休囚死 classification for a solar-term month."""

from .calendar_provider import CalendarSnapshot
from .enums import (
    SEASONAL_STRENGTH_LABELS_ZH,
    SEASONAL_STRENGTH_RANK,
    Element,
    SeasonalStrength,
)
from .models import ElementSeasonStrength, SeasonContext
from .relations import controls, generates

_ELEMENT_ORDER = (Element.WOOD, Element.FIRE, Element.EARTH, Element.METAL, Element.WATER)


def seasonal_strength_for(element: Element, month_element: Element) -> SeasonalStrength:
    if element is month_element:
        return SeasonalStrength.PROSPEROUS
    if generates(month_element, element):
        return SeasonalStrength.SUPPORTED
    if generates(element, month_element):
        return SeasonalStrength.RESTING
    if controls(element, month_element):
        return SeasonalStrength.CONFINED
    if controls(month_element, element):
        return SeasonalStrength.DEAD
    raise AssertionError(f"Unreachable seasonal relationship: {element}, {month_element}")


def build_season_context(
    snapshot: CalendarSnapshot,
    body_element: Element,
    initial_use_element: Element,
    changed_use_element: Element,
) -> SeasonContext:
    strengths = tuple(
        ElementSeasonStrength(
            element=element,
            state=(state := seasonal_strength_for(element, snapshot.month_element)),
            label_zh=SEASONAL_STRENGTH_LABELS_ZH[state],
            rank=SEASONAL_STRENGTH_RANK[state],
        )
        for element in _ELEMENT_ORDER
    )
    by_element = {item.element: item.state for item in strengths}
    return SeasonContext(
        current_solar_term=snapshot.current_solar_term,
        current_solar_term_started_at=snapshot.current_solar_term_started_at,
        month_branch=snapshot.month_branch,
        month_start_solar_term=snapshot.month_start_solar_term,
        month_element=snapshot.month_element,
        element_strengths=strengths,
        body_strength=by_element[body_element],
        initial_use_strength=by_element[initial_use_element],
        changed_use_strength=by_element[changed_use_element],
    )
