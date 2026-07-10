from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.models import MeihuaInput

CAST_AT = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.mark.parametrize(
    "numbers,upper,lower,number",
    [
        ((1, 1, 1), "乾", "乾", 1),
        ((8, 8, 6), "坤", "坤", 2),
        ((999, 999, 999), "震", "坎", 40),
        ((100, 27, 368), "兑", "巽", 28),
        ((4, 5, 2), "兑", "乾", 43),
    ],
)
def test_mutual_hexagram_slices_are_bottom_up(
    numbers: tuple[int, int, int], upper: str, lower: str, number: int
) -> None:
    chart = cast_meihua(MeihuaInput(*numbers, CAST_AT, "Asia/Shanghai"))
    assert chart.mutual_hexagram.lower_trigram.lines_bottom_up == chart.base_hexagram.lines_bottom_up[1:4]
    assert chart.mutual_hexagram.upper_trigram.lines_bottom_up == chart.base_hexagram.lines_bottom_up[2:5]
    assert (
        chart.mutual_hexagram.upper_trigram.name_zh,
        chart.mutual_hexagram.lower_trigram.name_zh,
        chart.mutual_hexagram.king_wen_number,
    ) == (upper, lower, number)
