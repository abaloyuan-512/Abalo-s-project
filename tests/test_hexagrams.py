import unicodedata

import pytest

from abalo_iching.meihua.exceptions import DataIntegrityError
from abalo_iching.meihua.hexagrams import (
    hexagram_from_lines,
    hexagram_from_number,
    hexagram_from_trigrams,
    load_hexagrams,
)


def test_64_hexagram_dataset_is_complete_and_unique() -> None:
    hexagrams = load_hexagrams()
    assert len(hexagrams) == 64
    assert {item.king_wen_number for item in hexagrams} == set(range(1, 65))
    assert len({item.unicode_symbol for item in hexagrams}) == 64
    assert len({(item.upper_trigram.name_zh, item.lower_trigram.name_zh) for item in hexagrams}) == 64
    for item in hexagrams:
        assert item.lines_bottom_up == item.lower_trigram.lines_bottom_up + item.upper_trigram.lines_bottom_up
        assert ord(item.unicode_symbol) == 0x4DBF + item.king_wen_number
        assert unicodedata.name(item.unicode_symbol).startswith("HEXAGRAM FOR")


@pytest.mark.parametrize(
    "upper,lower,number,name,symbol",
    [
        ("乾", "乾", 1, "乾", "䷀"),
        ("坤", "坤", 2, "坤", "䷁"),
        ("坎", "震", 3, "屯", "䷂"),
        ("艮", "坎", 4, "蒙", "䷃"),
        ("震", "离", 55, "丰", "䷶"),
        ("震", "乾", 34, "大壮", "䷡"),
        ("兑", "巽", 28, "大过", "䷛"),
        ("艮", "坤", 23, "剥", "䷖"),
    ],
)
def test_required_manual_hexagram_checks(upper: str, lower: str, number: int, name: str, symbol: str) -> None:
    item = hexagram_from_trigrams(upper, lower)
    assert (item.king_wen_number, item.name_zh, item.unicode_symbol) == (number, name, symbol)


def test_hexagram_lookup_by_lines_and_number() -> None:
    assert hexagram_from_lines((1, 0, 1, 1, 0, 0)) is hexagram_from_number(55)


@pytest.mark.parametrize("lines", [(1, 0, 1), (1, 0, 1, 1, 0, 2)])
def test_invalid_hexagram_lines_are_rejected(lines: tuple[int, ...]) -> None:
    with pytest.raises(DataIntegrityError):
        hexagram_from_lines(lines)


def test_unknown_hexagram_number_and_combo_are_rejected() -> None:
    with pytest.raises(DataIntegrityError):
        hexagram_from_number(65)
    with pytest.raises(DataIntegrityError):
        hexagram_from_trigrams("乾", "不存在")
