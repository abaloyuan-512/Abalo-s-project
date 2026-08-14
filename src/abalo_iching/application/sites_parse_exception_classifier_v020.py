"""Safe eight-code classification for one Responses parse boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)


FailureCode = Literal[
    "TIMEOUT",
    "CONNECTION",
    "AUTHENTICATION",
    "RATE_LIMIT",
    "BAD_REQUEST",
    "SERVER_ERROR",
    "PARSE_OR_SCHEMA",
    "UNKNOWN_PROVIDER_ERROR",
]
FailureStage = Literal[
    "BEFORE_PARSE_BOUNDARY", "IN_PARSE_BOUNDARY", "AFTER_PARSE_RESPONSE"
]


@dataclass(frozen=True)
class ParseOrSchemaFailure(Exception):
    """Trusted local marker used after a response cannot satisfy the schema."""


_EXACT_CODES: dict[type[BaseException], FailureCode] = {
    APITimeoutError: "TIMEOUT",
    APIConnectionError: "CONNECTION",
    AuthenticationError: "AUTHENTICATION",
    RateLimitError: "RATE_LIMIT",
    BadRequestError: "BAD_REQUEST",
    InternalServerError: "SERVER_ERROR",
    ParseOrSchemaFailure: "PARSE_OR_SCHEMA",
}
_VALID_STAGES: frozenset[str] = frozenset(
    {"BEFORE_PARSE_BOUNDARY", "IN_PARSE_BOUNDARY", "AFTER_PARSE_RESPONSE"}
)


def classify_parse_boundary_failure(
    *, failure: object, stage: FailureStage
) -> dict[str, object]:
    """Classify exact trusted types without inspecting failure attributes or text."""

    safe_stage: FailureStage = (
        stage
        if type(stage) is str and stage in _VALID_STAGES
        else "BEFORE_PARSE_BOUNDARY"
    )
    code: FailureCode = _EXACT_CODES.get(type(failure), "UNKNOWN_PROVIDER_ERROR")
    boundary_entered = safe_stage != "BEFORE_PARSE_BOUNDARY"
    return {
        "failure_code": code,
        "failure_stage": safe_stage,
        "call_may_have_been_sent": boundary_entered,
        "terminal_certainty": "TERMINAL_UNKNOWN" if boundary_entered else "FAIL_STOP",
        "classification_attempts": 1,
        "automatic_retries": 0,
    }


__all__ = ["FailureCode", "ParseOrSchemaFailure", "classify_parse_boundary_failure"]
