from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.models import MeihuaInput

CAST_AT = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.mark.parametrize("moving_line", [1, 2, 3])
def test_lower_moving_lines_make_upper_body(moving_line: int) -> None:
    chart = cast_meihua(MeihuaInput(1, 3, moving_line, CAST_AT, "Asia/Shanghai"))
    assert chart.body_trigram is chart.upper_trigram
    assert chart.initial_use_trigram is chart.lower_trigram
    assert chart.changed_use_trigram is chart.changed_hexagram.lower_trigram


@pytest.mark.parametrize("moving_line", [4, 5, 6])
def test_upper_moving_lines_make_lower_body(moving_line: int) -> None:
    chart = cast_meihua(MeihuaInput(1, 3, moving_line, CAST_AT, "Asia/Shanghai"))
    assert chart.body_trigram is chart.lower_trigram
    assert chart.initial_use_trigram is chart.upper_trigram
    assert chart.changed_use_trigram is chart.changed_hexagram.upper_trigram
