from __future__ import annotations

import ast
import inspect
from pathlib import Path

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from abalo_iching.application.sites_parse_exception_classifier_v020 import (
    ParseOrSchemaFailure,
    classify_parse_boundary_failure,
)


REQUEST = httpx.Request("POST", "https://fixture.invalid")


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=REQUEST)


def trusted_fixtures() -> list[tuple[BaseException, str]]:
    return [
        (APITimeoutError(request=REQUEST), "TIMEOUT"),
        (APIConnectionError(request=REQUEST), "CONNECTION"),
        (AuthenticationError("诱饵-server", response=_response(401), body=None), "AUTHENTICATION"),
        (RateLimitError("诱饵-bad request", response=_response(429), body=None), "RATE_LIMIT"),
        (BadRequestError("server 服务端错误", response=_response(400), body=None), "BAD_REQUEST"),
        (InternalServerError("bad request 请求错误", response=_response(500), body=None), "SERVER_ERROR"),
        (ParseOrSchemaFailure(), "PARSE_OR_SCHEMA"),
        (RuntimeError("诱饵-sk-secret-question-date"), "UNKNOWN_PROVIDER_ERROR"),
    ]


@pytest.mark.parametrize("failure,expected", trusted_fixtures())
def test_exact_eight_code_table_and_safe_output(failure: BaseException, expected: str) -> None:
    result = classify_parse_boundary_failure(failure=failure, stage="IN_PARSE_BOUNDARY")
    assert result == {
        "failure_code": expected,
        "failure_stage": "IN_PARSE_BOUNDARY",
        "call_may_have_been_sent": True,
        "terminal_certainty": "TERMINAL_UNKNOWN",
        "classification_attempts": 1,
        "automatic_retries": 0,
    }
    serialized = repr(result)
    for forbidden in ("secret", "question", "date", "server", "bad request"):
        assert forbidden not in serialized


def test_general_status_other_status_and_subclasses_are_unknown() -> None:
    class FakeBadRequest(BadRequestError):
        pass

    failures = [
        APIStatusError("status", response=_response(403), body=None),
        APIStatusError("status", response=_response(404), body=None),
        FakeBadRequest("status", response=_response(400), body=None),
    ]
    for failure in failures:
        assert classify_parse_boundary_failure(
            failure=failure, stage="IN_PARSE_BOUNDARY"
        )["failure_code"] == "UNKNOWN_PROVIDER_ERROR"


def test_message_language_and_status_wording_never_change_exact_mapping() -> None:
    bad = BadRequestError("服务器 server 500", response=_response(400), body=None)
    server = InternalServerError("请求 bad request 400", response=_response(500), body=None)
    assert classify_parse_boundary_failure(
        failure=bad, stage="IN_PARSE_BOUNDARY"
    )["failure_code"] == "BAD_REQUEST"
    assert classify_parse_boundary_failure(
        failure=server, stage="IN_PARSE_BOUNDARY"
    )["failure_code"] == "SERVER_ERROR"


class Evil:
    def __init__(self) -> None:
        object.__setattr__(self, "effects", 0)

    def _effect(self) -> None:
        object.__setattr__(self, "effects", self.effects + 1)

    def __getattr__(self, name: str) -> object:
        self._effect()
        raise AttributeError(name)

    def __str__(self) -> str:
        self._effect()
        return "secret"

    def __repr__(self) -> str:
        self._effect()
        return "raw"

    @property
    def status_code(self) -> int:
        self._effect()
        return 500

    @property
    def body(self) -> str:
        self._effect()
        return "body"

    @property
    def headers(self) -> dict[str, str]:
        self._effect()
        return {"secret": "key"}


def test_malicious_duck_type_is_unknown_with_zero_side_effects() -> None:
    evil = Evil()
    result = classify_parse_boundary_failure(failure=evil, stage="IN_PARSE_BOUNDARY")
    assert result["failure_code"] == "UNKNOWN_PROVIDER_ERROR"
    assert evil.effects == 0


def test_stage_semantics_are_caller_controlled_and_conservative() -> None:
    before = classify_parse_boundary_failure(
        failure=RuntimeError(), stage="BEFORE_PARSE_BOUNDARY"
    )
    after = classify_parse_boundary_failure(
        failure=ParseOrSchemaFailure(), stage="AFTER_PARSE_RESPONSE"
    )
    invalid = classify_parse_boundary_failure(failure=RuntimeError(), stage="invalid")  # type: ignore[arg-type]
    assert before["call_may_have_been_sent"] is False
    assert before["terminal_certainty"] == "FAIL_STOP"
    assert after["call_may_have_been_sent"] is True
    assert invalid["failure_stage"] == "BEFORE_PARSE_BOUNDARY"


def test_static_module_has_no_client_key_network_bridge_high_or_forbidden_codes() -> None:
    import abalo_iching.application.sites_parse_exception_classifier_v020 as module

    source = Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not ({"OpenAI", "cast_meihua", "bridge_sdk_response_to_v017", "getenv"} & names)
    for forbidden in (
        "OPENAI_API_KEY", "traceback", "status_code", "response.body", "headers",
        '"API_STATUS"', '"INVALID_RESPONSE"',
    ):
        assert forbidden not in source
