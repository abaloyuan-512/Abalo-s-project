"""Eight-code parse-boundary classification with trusted status checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from openai import APIConnectionError, APITimeoutError, AuthenticationError, BadRequestError, InternalServerError, RateLimitError

FailureCode = Literal["TIMEOUT","CONNECTION","AUTHENTICATION","RATE_LIMIT","BAD_REQUEST","SERVER_ERROR","PARSE_OR_SCHEMA","UNKNOWN_PROVIDER_ERROR"]
FailureStage = Literal["BEFORE_PARSE_BOUNDARY","IN_PARSE_BOUNDARY","AFTER_PARSE_RESPONSE"]

@dataclass(frozen=True)
class ParseOrSchemaFailure(Exception):
    """Trusted local post-response parse marker."""

_CONSTANT_CODES: dict[type[BaseException], FailureCode] = {
    APITimeoutError:"TIMEOUT", APIConnectionError:"CONNECTION",
    AuthenticationError:"AUTHENTICATION", RateLimitError:"RATE_LIMIT",
    ParseOrSchemaFailure:"PARSE_OR_SCHEMA",
}
_STAGES=frozenset({"BEFORE_PARSE_BOUNDARY","IN_PARSE_BOUNDARY","AFTER_PARSE_RESPONSE"})

def classify_parse_boundary_failure(*, failure: object, stage: FailureStage) -> dict[str, object]:
    safe_stage: FailureStage = stage if type(stage) is str and stage in _STAGES else "BEFORE_PARSE_BOUNDARY"
    exact_type=type(failure)
    status_reads=0
    code: FailureCode
    if exact_type is BadRequestError:
        status_reads=1
        try:
            status=failure.response.status_code
        except BaseException:
            status=None
        code="BAD_REQUEST" if type(status) is int and status == 400 else "UNKNOWN_PROVIDER_ERROR"
    elif exact_type is InternalServerError:
        status_reads=1
        try:
            status=failure.response.status_code
        except BaseException:
            status=None
        code="SERVER_ERROR" if type(status) is int and 500 <= status <= 599 else "UNKNOWN_PROVIDER_ERROR"
    else:
        code=_CONSTANT_CODES.get(exact_type,"UNKNOWN_PROVIDER_ERROR")
    entered=safe_stage != "BEFORE_PARSE_BOUNDARY"
    return {"failure_code":code,"failure_stage":safe_stage,"call_may_have_been_sent":entered,
            "terminal_certainty":"TERMINAL_UNKNOWN" if entered else "FAIL_STOP",
            "classification_attempts":1,"status_read_count":status_reads,"automatic_retries":0}

__all__=["FailureCode","ParseOrSchemaFailure","classify_parse_boundary_failure"]
