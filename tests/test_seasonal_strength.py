from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider
from abalo_iching.meihua.enums import Element, SeasonalStrength
from abalo_iching.meihua.seasonal_strength import seasonal_strength_for


@pytest.mark.parametrize(
    "element,expected",
    [
        (Element.WOOD, SeasonalStrength.PROSPEROUS),
        (Element.FIRE, SeasonalStrength.SUPPORTED),
        (Element.WATER, SeasonalStrength.RESTING),
        (Element.EARTH, SeasonalStrength.DEAD),
        (Element.METAL, SeasonalStrength.CONFINED),
    ],
)
def test_all_five_strengths_in_wood_month(element: Element, expected: SeasonalStrength) -> None:
    assert seasonal_strength_for(element, Element.WOOD) is expected


@pytest.mark.parametrize(
    "month,day,term,branch,element",
    [
        (2, 15, "立春", "寅", Element.WOOD),
        (3, 15, "惊蛰", "卯", Element.WOOD),
        (4, 15, "清明", "辰", Element.EARTH),
        (5, 15, "立夏", "巳", Element.FIRE),
        (6, 15, "芒种", "午", Element.FIRE),
        (7, 15, "小暑", "未", Element.EARTH),
        (8, 15, "立秋", "申", Element.METAL),
        (9, 15, "白露", "酉", Element.METAL),
        (10, 15, "寒露", "戌", Element.EARTH),
        (11, 15, "立冬", "亥", Element.WATER),
        (12, 15, "大雪", "子", Element.WATER),
        (1, 15, "小寒", "丑", Element.EARTH),
    ],
)
def test_solar_term_months(month: int, day: int, term: str, branch: str, element: Element) -> None:
    year = 2027 if month == 1 else 2026
    cast_at = datetime(year, month, day, 12, tzinfo=ZoneInfo("Asia/Shanghai"))
    snapshot = LunarPythonCalendarProvider().get_calendar_snapshot(cast_at, "Asia/Shanghai")
    assert (snapshot.month_start_solar_term, snapshot.month_branch, snapshot.month_element) == (term, branch, element)
    assert snapshot.current_solar_term_started_at.tzinfo is not None


def test_casting_instant_is_normalized_to_requested_iana_zone() -> None:
    instant = datetime(2026, 7, 10, 4, tzinfo=ZoneInfo("UTC"))
    snapshot = LunarPythonCalendarProvider().get_calendar_snapshot(instant, "Asia/Shanghai")
    assert snapshot.normalized_cast_at.hour == 12
    assert getattr(snapshot.normalized_cast_at.tzinfo, "key") == "Asia/Shanghai"
