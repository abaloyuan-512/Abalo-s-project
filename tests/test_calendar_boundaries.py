import json
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider

FIXTURE = Path(__file__).parent / "fixtures" / "solar_term_boundaries_2026_v1.json"
PAYLOAD = json.loads(FIXTURE.read_text(encoding="utf-8"))
BOUNDARIES = PAYLOAD["boundaries"]
ZONES = ("Asia/Shanghai", "UTC", "America/Los_Angeles")
BOUNDARY_CASES = list(product(BOUNDARIES, ZONES))


@pytest.mark.parametrize(
    "boundary,timezone_name",
    BOUNDARY_CASES,
    ids=[f"{item['term']}-{zone}" for item, zone in BOUNDARY_CASES],
)
def test_month_changes_once_at_frozen_jie_boundary(boundary: dict[str, str], timezone_name: str) -> None:
    provider = LunarPythonCalendarProvider()
    local_boundary = datetime.fromisoformat(boundary["at"]).astimezone(ZoneInfo(timezone_name))
    observations = []

    for delta in (-1, 0, 1):
        instant = local_boundary + timedelta(seconds=delta)
        snapshot = provider.get_calendar_snapshot(instant, timezone_name)
        observations.append(snapshot)
        assert snapshot.normalized_cast_at.isoformat() == instant.isoformat()

    assert [item.month_branch for item in observations] == [
        boundary["previous_branch"],
        boundary["branch"],
        boundary["branch"],
    ]
    assert observations[0].month_start_solar_term == boundary["previous_term"]
    assert observations[1].month_start_solar_term == boundary["term"]
    assert observations[2].month_start_solar_term == boundary["term"]
    assert observations[1].current_solar_term == boundary["term"]
    assert observations[1].current_solar_term_started_at == local_boundary


def test_boundary_fixture_is_frozen_to_expected_library_and_timezone() -> None:
    assert PAYLOAD["fixture_version"] == "SOLAR_TERM_BOUNDARIES_2026_V1"
    assert PAYLOAD["calendar_data_version"] == "lunar_python/1.4.8"
    assert PAYLOAD["base_timezone"] == "Asia/Shanghai"
    assert len(BOUNDARIES) == 12
