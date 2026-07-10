from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.models import MeihuaInput

CAST_AT = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.mark.parametrize("moving_line,expected_number", [(1, 44), (2, 13), (3, 10), (4, 9), (5, 14), (6, 43)])
def test_each_moving_line_flips_only_one_line(moving_line: int, expected_number: int) -> None:
    chart = cast_meihua(MeihuaInput(1, 1, moving_line, CAST_AT, "Asia/Shanghai"))
    changed = chart.changed_hexagram.lines_bottom_up
    base = chart.base_hexagram.lines_bottom_up
    assert chart.changed_hexagram.king_wen_number == expected_number
    assert [index for index, pair in enumerate(zip(base, changed), start=1) if pair[0] != pair[1]] == [moving_line]
    assert changed[moving_line - 1] == 0
