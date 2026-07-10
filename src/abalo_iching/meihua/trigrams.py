"""Load and query the single versioned trigram data source."""

import json
from functools import lru_cache
from importlib.resources import files

from .enums import Element
from .exceptions import DataIntegrityError, InputValidationError
from .models import Trigram

_DATA_RESOURCE = files("abalo_iching.data.meihua").joinpath("trigrams_v1.json")


def _validate_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputValidationError(f"{field_name} must be an int, excluding bool")
    if not 1 <= value <= 999:
        raise InputValidationError(f"{field_name} must be between 1 and 999")
    return value


def mod_one_based(value: int, modulus: int) -> int:
    """Return a one-based modulus after enforcing the Phase 1 integer contract."""
    checked = _validate_integer(value, "value")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus < 1:
        raise InputValidationError("modulus must be a positive int")
    remainder = checked % modulus
    return modulus if remainder == 0 else remainder


def validate_cast_numbers(first_number: object, second_number: object, third_number: object) -> None:
    _validate_integer(first_number, "first_number")
    _validate_integer(second_number, "second_number")
    _validate_integer(third_number, "third_number")


@lru_cache(maxsize=1)
def load_trigrams() -> tuple[Trigram, ...]:
    try:
        payload = json.loads(_DATA_RESOURCE.read_text(encoding="utf-8"))
        rows = payload["trigrams"]
        version = payload["data_version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DataIntegrityError(f"Cannot load trigram data: {exc}") from exc

    trigrams = tuple(
        Trigram(
            number=int(row["number"]),
            name_zh=str(row["name_zh"]),
            symbol=str(row["symbol"]),
            element=Element(row["element"]),
            lines_bottom_up=tuple(row["lines_bottom_up"]),
            data_version=str(row["data_version"]),
        )
        for row in rows
    )
    if len(trigrams) != 8:
        raise DataIntegrityError("Trigram data must contain exactly 8 records")
    if {item.number for item in trigrams} != set(range(1, 9)):
        raise DataIntegrityError("Trigram numbers must be exactly 1 through 8")
    if len({item.name_zh for item in trigrams}) != 8 or len({item.lines_bottom_up for item in trigrams}) != 8:
        raise DataIntegrityError("Trigram names and line structures must be unique")
    for item in trigrams:
        if item.data_version != version or len(item.lines_bottom_up) != 3 or set(item.lines_bottom_up) - {0, 1}:
            raise DataIntegrityError(f"Invalid trigram record: {item.name_zh}")
    return trigrams


def trigram_from_number(number: int) -> Trigram:
    for trigram in load_trigrams():
        if trigram.number == number:
            return trigram
    raise DataIntegrityError(f"Unknown trigram number: {number}")


def trigram_from_cast_number(value: int) -> Trigram:
    return trigram_from_number(mod_one_based(value, 8))


def trigram_from_name(name_zh: str) -> Trigram:
    for trigram in load_trigrams():
        if trigram.name_zh == name_zh:
            return trigram
    raise DataIntegrityError(f"Unknown trigram name: {name_zh}")


def trigram_from_lines(lines_bottom_up: tuple[int, int, int] | list[int]) -> Trigram:
    lines = tuple(lines_bottom_up)
    for trigram in load_trigrams():
        if trigram.lines_bottom_up == lines:
            return trigram
    raise DataIntegrityError(f"Unknown trigram line structure: {lines}")
