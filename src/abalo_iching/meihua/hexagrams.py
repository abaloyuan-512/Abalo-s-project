"""Load and query the versioned 64-hexagram table."""

import json
from functools import lru_cache
from importlib.resources import files

from .exceptions import DataIntegrityError
from .models import Hexagram
from .trigrams import trigram_from_lines, trigram_from_name

_DATA_RESOURCE = files("abalo_iching.data.meihua").joinpath("hexagrams_v1.json")


@lru_cache(maxsize=1)
def load_hexagrams() -> tuple[Hexagram, ...]:
    try:
        payload = json.loads(_DATA_RESOURCE.read_text(encoding="utf-8"))
        rows = payload["hexagrams"]
        version = payload["data_version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DataIntegrityError(f"Cannot load hexagram data: {exc}") from exc

    hexagrams: list[Hexagram] = []
    for row in rows:
        upper = trigram_from_name(str(row["upper_trigram"]))
        lower = trigram_from_name(str(row["lower_trigram"]))
        lines = tuple(row["lines_bottom_up"])
        expected_lines = lower.lines_bottom_up + upper.lines_bottom_up
        if lines != expected_lines:
            raise DataIntegrityError(f"Hexagram line mismatch for King Wen {row['king_wen_number']}")
        hexagrams.append(
            Hexagram(
                king_wen_number=int(row["king_wen_number"]),
                name_zh=str(row["name_zh"]),
                full_name_zh=str(row["full_name_zh"]),
                unicode_symbol=str(row["unicode_symbol"]),
                upper_trigram=upper,
                lower_trigram=lower,
                lines_bottom_up=lines,
                data_version=str(row["data_version"]),
            )
        )

    result = tuple(hexagrams)
    if len(result) != 64:
        raise DataIntegrityError("Hexagram data must contain exactly 64 records")
    if {item.king_wen_number for item in result} != set(range(1, 65)):
        raise DataIntegrityError("King Wen numbers must be exactly 1 through 64")
    if len({item.unicode_symbol for item in result}) != 64:
        raise DataIntegrityError("Unicode hexagram symbols must be unique")
    if len({(item.upper_trigram.name_zh, item.lower_trigram.name_zh) for item in result}) != 64:
        raise DataIntegrityError("Upper/lower trigram combinations must be unique")
    if any(item.data_version != version for item in result):
        raise DataIntegrityError("Hexagram item data version mismatch")
    return result


def hexagram_from_number(king_wen_number: int) -> Hexagram:
    for hexagram in load_hexagrams():
        if hexagram.king_wen_number == king_wen_number:
            return hexagram
    raise DataIntegrityError(f"Unknown King Wen number: {king_wen_number}")


def hexagram_from_trigrams(upper_name: str, lower_name: str) -> Hexagram:
    for hexagram in load_hexagrams():
        if hexagram.upper_trigram.name_zh == upper_name and hexagram.lower_trigram.name_zh == lower_name:
            return hexagram
    raise DataIntegrityError(f"Unknown trigram combination: upper={upper_name}, lower={lower_name}")


def hexagram_from_lines(lines_bottom_up: tuple[int, ...] | list[int]) -> Hexagram:
    lines = tuple(lines_bottom_up)
    if len(lines) != 6 or set(lines) - {0, 1}:
        raise DataIntegrityError(f"Invalid six-line structure: {lines}")
    lower = trigram_from_lines(lines[:3])
    upper = trigram_from_lines(lines[3:])
    return hexagram_from_trigrams(upper.name_zh, lower.name_zh)
