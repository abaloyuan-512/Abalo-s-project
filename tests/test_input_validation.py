from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider, normalize_cast_at
from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.exceptions import CalendarCalculationError, InputValidationError
from abalo_iching.meihua.models import MeihuaInput
from abalo_iching.meihua.trigrams import mod_one_based

VALID_TIME = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.mark.parametrize("value,modulus,expected", [(1, 8, 1), (8, 8, 8), (9, 8, 1), (999, 8, 7), (6, 6, 6), (12, 6, 6)])
def test_mod_one_based(value: int, modulus: int, expected: int) -> None:
    assert mod_one_based(value, modulus) == expected


@pytest.mark.parametrize("bad", [True, False, 0, -1, 1000, 1.0, "1", None])
def test_numbers_reject_invalid_types_and_range(bad: object) -> None:
    with pytest.raises(InputValidationError):
        cast_meihua(MeihuaInput(bad, 1, 1, VALID_TIME, "Asia/Shanghai"))


@pytest.mark.parametrize("bad_modulus", [True, 0, -1, 8.0, "8"])
def test_modulus_must_be_positive_integer(bad_modulus: object) -> None:
    with pytest.raises(InputValidationError):
        mod_one_based(1, bad_modulus)


def test_chart_input_type_is_required() -> None:
    with pytest.raises(InputValidationError):
        cast_meihua({"first_number": 1})


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(InputValidationError, match="timezone-aware"):
        cast_meihua(MeihuaInput(1, 1, 1, datetime(2026, 7, 10, 12), "Asia/Shanghai"))


def test_unknown_iana_timezone_is_rejected() -> None:
    with pytest.raises(InputValidationError, match="Unknown IANA timezone"):
        normalize_cast_at(VALID_TIME, "Mars/Olympus_Mons")


@pytest.mark.parametrize("bad", [None, "", 3])
def test_timezone_name_must_be_non_empty_string(bad: object) -> None:
    with pytest.raises(InputValidationError):
        normalize_cast_at(VALID_TIME, bad)


def test_non_datetime_cast_at_is_rejected() -> None:
    with pytest.raises(InputValidationError):
        normalize_cast_at("2026-07-10", "Asia/Shanghai")


def test_calendar_library_failure_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object) -> object:
        raise RuntimeError("forced failure")

    monkeypatch.setattr("abalo_iching.meihua.calendar_provider.Solar.fromYmdHms", fail)
    with pytest.raises(CalendarCalculationError, match="Solar-term calculation failed"):
        LunarPythonCalendarProvider().get_calendar_snapshot(VALID_TIME, "Asia/Shanghai")
