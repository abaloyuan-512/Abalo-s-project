"""Exact solar-term adapter; the only module allowed to import lunar_python."""

from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lunar_python import Solar

from .enums import Element
from .exceptions import CalendarCalculationError, InputValidationError

_BEIJING_ZONE = ZoneInfo("Asia/Shanghai")

_MONTH_BY_JIE = {
    "立春": ("寅", Element.WOOD),
    "惊蛰": ("卯", Element.WOOD),
    "清明": ("辰", Element.EARTH),
    "立夏": ("巳", Element.FIRE),
    "芒种": ("午", Element.FIRE),
    "小暑": ("未", Element.EARTH),
    "立秋": ("申", Element.METAL),
    "白露": ("酉", Element.METAL),
    "寒露": ("戌", Element.EARTH),
    "立冬": ("亥", Element.WATER),
    "大雪": ("子", Element.WATER),
    "小寒": ("丑", Element.EARTH),
}


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
    normalized_cast_at: datetime
    current_solar_term: str
    current_solar_term_started_at: datetime
    month_branch: str
    month_start_solar_term: str
    month_element: Element
    provider_version: str


class CalendarProvider(Protocol):
    def get_calendar_snapshot(self, cast_at: datetime, timezone_name: str) -> CalendarSnapshot: ...


def normalize_cast_at(cast_at: datetime, timezone_name: str) -> datetime:
    if not isinstance(cast_at, datetime):
        raise InputValidationError("cast_at must be a datetime")
    if cast_at.tzinfo is None or cast_at.utcoffset() is None:
        raise InputValidationError("cast_at must be timezone-aware")
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise InputValidationError("timezone_name must be a non-empty IANA timezone name")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise InputValidationError(f"Unknown IANA timezone: {timezone_name}") from exc
    return cast_at.astimezone(zone)


def _solar_to_datetime(solar: object, target_zone: ZoneInfo) -> datetime:
    beijing = datetime(
        solar.getYear(),
        solar.getMonth(),
        solar.getDay(),
        solar.getHour(),
        solar.getMinute(),
        solar.getSecond(),
        tzinfo=_BEIJING_ZONE,
    )
    return beijing.astimezone(target_zone)


class LunarPythonCalendarProvider:
    """Adapt lunar_python's Beijing-time solar terms to the requested civil timezone."""

    def get_calendar_snapshot(self, cast_at: datetime, timezone_name: str) -> CalendarSnapshot:
        normalized = normalize_cast_at(cast_at, timezone_name)
        target_zone = ZoneInfo(timezone_name)
        beijing_time = normalized.astimezone(_BEIJING_ZONE)
        try:
            solar = Solar.fromYmdHms(
                beijing_time.year,
                beijing_time.month,
                beijing_time.day,
                beijing_time.hour,
                beijing_time.minute,
                beijing_time.second,
            )
            lunar = solar.getLunar()
            current_term = lunar.getPrevJieQi(False)
            month_jie = lunar.getPrevJie(False)
            if current_term is None or month_jie is None:
                raise CalendarCalculationError("lunar_python returned no previous solar term or month Jie")
            current_term_name = current_term.getName()
            month_jie_name = month_jie.getName()
            try:
                month_branch, month_element = _MONTH_BY_JIE[month_jie_name]
            except KeyError as exc:
                raise CalendarCalculationError(f"Unsupported month-start solar term: {month_jie_name}") from exc
            return CalendarSnapshot(
                normalized_cast_at=normalized,
                current_solar_term=current_term_name,
                current_solar_term_started_at=_solar_to_datetime(current_term.getSolar(), target_zone),
                month_branch=month_branch,
                month_start_solar_term=month_jie_name,
                month_element=month_element,
                provider_version=f"lunar_python/{version('lunar_python')}",
            )
        except CalendarCalculationError:
            raise
        except Exception as exc:
            raise CalendarCalculationError(f"Solar-term calculation failed: {exc}") from exc
