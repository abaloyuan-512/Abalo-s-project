from dataclasses import FrozenInstanceError

import pytest

from abalo_iching.meihua.enums import Element
from abalo_iching.meihua.exceptions import DataIntegrityError
from abalo_iching.meihua.trigrams import (
    load_trigrams,
    trigram_from_cast_number,
    trigram_from_lines,
    trigram_from_name,
    trigram_from_number,
)

EXPECTED = [
    (1, "乾", "☰", Element.METAL, (1, 1, 1)),
    (2, "兑", "☱", Element.METAL, (1, 1, 0)),
    (3, "离", "☲", Element.FIRE, (1, 0, 1)),
    (4, "震", "☳", Element.WOOD, (1, 0, 0)),
    (5, "巽", "☴", Element.WOOD, (0, 1, 1)),
    (6, "坎", "☵", Element.WATER, (0, 1, 0)),
    (7, "艮", "☶", Element.EARTH, (0, 0, 1)),
    (8, "坤", "☷", Element.EARTH, (0, 0, 0)),
]


def test_all_eight_frozen_trigrams() -> None:
    trigrams = load_trigrams()
    assert len(trigrams) == 8
    for number, name, symbol, element, lines in EXPECTED:
        trigram = trigram_from_number(number)
        assert (trigram.name_zh, trigram.symbol, trigram.element, trigram.lines_bottom_up) == (
            name,
            symbol,
            element,
            lines,
        )
        assert trigram_from_name(name) is trigram
        assert trigram_from_lines(lines) is trigram


def test_trigram_objects_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        trigram_from_number(1).name_zh = "changed"


def test_cast_number_uses_one_based_modulus() -> None:
    assert trigram_from_cast_number(8).name_zh == "坤"
    assert trigram_from_cast_number(9).name_zh == "乾"
    assert trigram_from_cast_number(999).name_zh == "艮"


@pytest.mark.parametrize("call", [lambda: trigram_from_number(9), lambda: trigram_from_name("不存在"), lambda: trigram_from_lines((1, 2, 1))])
def test_unknown_trigram_lookup_raises_data_error(call: object) -> None:
    with pytest.raises(DataIntegrityError):
        call()
