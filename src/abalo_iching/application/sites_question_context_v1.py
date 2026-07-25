"""Versioned, non-calculative context for the Sites V3 experience.

The fields in this module help present an already-computed chart in practical
language.  They must never be passed into the deterministic chart engine.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

CONTEXT_VERSION = "SITES_QUESTION_CONTEXT_V1"
MIN_QUESTION_LENGTH = 6
MAX_QUESTION_LENGTH = 160


class DecisionStage(StrEnum):
    EXPLORING = "EXPLORING"
    PREPARING = "PREPARING"
    ALREADY_ACTING = "ALREADY_ACTING"
    WAITING_FEEDBACK = "WAITING_FEEDBACK"


class KeyUncertainty(StrEnum):
    CONDITIONS = "CONDITIONS"
    OTHER_RESPONSE = "OTHER_RESPONSE"
    OWN_COMMITMENT = "OWN_COMMITMENT"
    TIMING = "TIMING"


def normalize_question_text(value: object) -> str:
    """Normalize a bounded display question without interpreting its meaning."""
    if not isinstance(value, str):
        raise ValueError("question_text must be a string")
    # NFC preserves the user's Chinese punctuation while still normalizing
    # canonically equivalent characters for stable display and hashing.
    normalized = unicodedata.normalize("NFC", value)
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in normalized):
        raise ValueError("question_text contains control characters")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not MIN_QUESTION_LENGTH <= len(normalized) <= MAX_QUESTION_LENGTH:
        raise ValueError("question_text length is out of range")
    return normalized


def parse_question_context(stage: object, uncertainty: object) -> tuple[DecisionStage, KeyUncertainty]:
    if not isinstance(stage, str) or not isinstance(uncertainty, str):
        raise ValueError("question context fields must be strings")
    try:
        return DecisionStage(stage), KeyUncertainty(uncertainty)
    except ValueError as exc:
        raise ValueError("unknown question context value") from exc
