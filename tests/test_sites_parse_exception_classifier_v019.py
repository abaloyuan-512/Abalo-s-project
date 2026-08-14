from __future__ import annotations

import ast
import inspect
from pathlib import Path

import httpx
import pytest
from openai import (
    APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError,
    RateLimitError,
)

from abalo_iching.application.sites_parse_exception_classifier_v019 import (
    ParseOrSchemaFailure, classify_parse_boundary_failure,
)


REQUEST = httpx.Request("POST", "https://fixture.invalid")
RESPONSE_400 = httpx.Response(400, request=REQUEST)
RESPONSE_401 = httpx.Response(401, request=REQUEST)
RESPONSE_429 = httpx.Response(429, request=REQUEST)
RESPONSE_500 = httpx.Response(500, request=REQUEST)


def fixtures():
    return [
        (APITimeoutError(request=REQUEST), "TIMEOUT"),
        (APIConnectionError(request=REQUEST), "CONNECTION"),
        (AuthenticationError("诱饵-sk-secret", response=RESPONSE_401, body=None), "AUTHENTICATION"),
        (RateLimitError("诱饵-raw-body", response=RESPONSE_429, body=None), "RATE_LIMIT"),
        (APIStatusError("诱饵-question-date", response=RESPONSE_400, body=None), "API_STATUS"),
        (ParseOrSchemaFailure(), "INVALID_RESPONSE"),
        (RuntimeError("诱饵-traceback"), "UNKNOWN_PROVIDER_ERROR"),
    ]


@pytest.mark.parametrize("failure,expected", fixtures())
def test_exact_type_table_and_safe_output(failure, expected):
    result = classify_parse_boundary_failure(failure=failure, stage="IN_PARSE_BOUNDARY")
    assert result == {
        "failure_code": expected, "failure_stage": "IN_PARSE_BOUNDARY",
        "call_may_have_been_sent": True, "terminal_certainty": "TERMINAL_UNKNOWN",
        "classification_attempts": 1, "automatic_retries": 0,
    }
    serialized = repr(result)
    for forbidden in ("secret", "raw-body", "question", "date", "header", "traceback"):
        assert forbidden not in serialized


def test_stage_semantics_are_conservative():
    before = classify_parse_boundary_failure(failure=RuntimeError(), stage="BEFORE_PARSE_BOUNDARY")
    after = classify_parse_boundary_failure(failure=ParseOrSchemaFailure(), stage="AFTER_PARSE_RESPONSE")
    assert before["call_may_have_been_sent"] is False and before["terminal_certainty"] == "FAIL_STOP"
    assert after["call_may_have_been_sent"] is True and after["terminal_certainty"] == "TERMINAL_UNKNOWN"


class Evil:
    def __init__(self): object.__setattr__(self, "effects", 0)
    def __getattr__(self, name): object.__setattr__(self, "effects", self.effects + 1); raise AttributeError(name)
    def __str__(self): object.__setattr__(self, "effects", self.effects + 1); return "secret"
    def __repr__(self): object.__setattr__(self, "effects", self.effects + 1); return "raw"
    @property
    def status_code(self): object.__setattr__(self, "effects", self.effects + 1); return 401


def test_malicious_and_duck_types_are_unknown_without_side_effect():
    evil = Evil()
    result = classify_parse_boundary_failure(failure=evil, stage="IN_PARSE_BOUNDARY")
    assert evil.effects == 0 and result["failure_code"] == "UNKNOWN_PROVIDER_ERROR"


def test_subclasses_and_message_language_do_not_gain_specificity():
    class FakeTimeout(APITimeoutError): pass
    fake = FakeTimeout(request=REQUEST)
    assert classify_parse_boundary_failure(failure=fake, stage="IN_PARSE_BOUNDARY")["failure_code"] == "UNKNOWN_PROVIDER_ERROR"
    a = classify_parse_boundary_failure(failure=RuntimeError("English"), stage="IN_PARSE_BOUNDARY")
    b = classify_parse_boundary_failure(failure=RuntimeError("中文 sk-secret"), stage="IN_PARSE_BOUNDARY")
    assert a == b


def test_static_module_has_no_client_env_network_bridge_or_high():
    import abalo_iching.application.sites_parse_exception_classifier_v019 as module
    source = Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not ({"OpenAI", "cast_meihua", "bridge_sdk_response_to_v017", "getenv"} & names)
    for forbidden in ("OPENAI_API_KEY", "traceback", "status_code", "response.body", "headers"):
        assert forbidden not in source
