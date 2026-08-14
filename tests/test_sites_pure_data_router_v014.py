from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_pure_data_router_v014 import (
    begin_pure_data_direct_reading,
    resume_pure_data_direct_reading,
)
from tests.test_sites_direct_reading_v2 import _complete_text


QUESTION = "这次合作，我应该继续投入，还是停止并退出？"


def request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {"question_text": QUESTION, "numbers": [7, 8, 9]}
    value.update(changes)
    return value


def ambiguity() -> dict[str, str]:
    return {"kind": "SUBJECT", "description": "所问的合作可能指两个不同项目"}


def provider_data(*, text: str | None = None, failure_code: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "output_text": text if text is not None else _complete_text(base="地天泰", mutual="雷泽归妹", changed="地泽临", line_name="初九", line_text="拔茅茹，以其彙。征吉。"),
        "api_status": "completed",
        "incomplete_details": None,
        "response_id": "fixture-v014",
        "model": "gpt-5.6-sol",
        "input_tokens": 200,
        "output_tokens": 2000,
        "latency_ms": 10,
    }
    if failure_code is not None:
        value["failure_code"] = failure_code
    return value


def outcome(status: str, **extra: object) -> dict[str, object]:
    return {"status": status, **extra}


@pytest.fixture
def counted_cast(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    real = high_service.cast_meihua
    calls: list[int] = []

    def count(value: object) -> object:
        calls.append(1)
        return real(value)

    monkeypatch.setattr(high_service, "cast_meihua", count)
    return calls


def assert_high_once(result: dict[str, Any], calls: list[int]) -> None:
    assert result["prepare_calls"] == result["deterministic_cast_count"] == 1
    assert result["provider_calls"] == result["high_attempts"] == 1
    assert len(calls) == 1
    assert result["router_callback_executions"] == result["router_cast_count"] == 0
    assert result["automatic_retries"] == 0
    assert result["original_question_text"] == QUESTION
    assert result["original_question_sha_before"] == result["original_question_sha_after"]
    assert result["original_question_preserved"] is True


@pytest.mark.parametrize(
    ("changes", "ignored"),
    [
        ({}, None),
        ({"user_confirmed": True, "critical_ambiguity": ambiguity()}, {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}),
        ({"skip_router": True, "critical_ambiguity": ambiguity()}, {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"}),
    ],
)
def test_clear_confirmed_and_skip_go_direct_high_and_ignore_outcome(
    changes: dict[str, object], ignored: object, counted_cast: list[int]
) -> None:
    result = begin_pure_data_direct_reading(
        request(**changes), router_outcome=ignored, fixture_provider_result=provider_data()
    )
    assert result["route"] == "DIRECT_HIGH"
    assert result["router_outcomes_consumed"] == 0
    assert_high_once(result, counted_cast)


def test_pass_and_failed_outcomes_go_high(counted_cast: list[int]) -> None:
    passed = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=outcome("PASS"),
        fixture_provider_result=provider_data(),
    )
    assert passed["router_outcome_status"] == "PASS"
    assert passed["router_outcomes_consumed"] == 1
    assert_high_once(passed, counted_cast)
    counted_cast.clear()
    failed = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=outcome("FAILED", failure_code="TIMEOUT"),
        fixture_provider_result=provider_data(),
    )
    assert failed["router_outcome_status"] == "FAILED"
    assert failed["router_outcome_validation_code"] == "TIMEOUT"
    assert_high_once(failed, counted_cast)


def test_ask_waits_at_zero_then_answer_resumes_to_one_high(counted_cast: list[int]) -> None:
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_pure_data_direct_reading(
        payload,
        router_outcome=outcome("ASK_ONCE", ambiguity_kind="SUBJECT"),
        fixture_provider_result=provider_data(),
    )
    assert waiting["status"] == "WAITING_FOR_ONE_ANSWER"
    assert waiting["prepare_calls"] == waiting["deterministic_cast_count"] == waiting["provider_calls"] == 0
    assert counted_cast == []
    result = resume_pure_data_direct_reading(
        payload,
        waiting,
        user_answer="我问的是甲项目。",
        fixture_provider_result=provider_data(),
    )
    assert result["high_response"]["audit"]["question_sha256"] == result["original_question_sha_before"]
    assert_high_once(result, counted_cast)


def test_ask_skip_resumes_without_user_context(counted_cast: list[int]) -> None:
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_pure_data_direct_reading(
        payload, router_outcome=outcome("ASK_ONCE", ambiguity_kind="SUBJECT")
    )
    result = resume_pure_data_direct_reading(
        payload, waiting, skip_answer=True, fixture_provider_result=provider_data()
    )
    assert_high_once(result, counted_cast)


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        "",
        {},
        {"status": "UNKNOWN"},
        {"status": "PASS", "question_text": "改写问题"},
        {"status": "PASS", "facts": ["新增事实"]},
        {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT", "question": "自由问题"},
        {"status": "FAILED"},
    ],
)
def test_missing_empty_schema_and_unauthorized_outcomes_fail_open(
    invalid: object, counted_cast: list[int]
) -> None:
    result = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=invalid,
        fixture_provider_result=provider_data(),
    )
    assert result["router_outcomes_consumed"] == 0
    assert result["router_outcome_validation_code"] in {"OUTCOME_MISSING", "INVALID_ROUTER_OUTCOME"}
    assert_high_once(result, counted_cast)


class Evil:
    def __init__(self) -> None:
        object.__setattr__(self, "effects", 0)

    def __call__(self) -> object:
        object.__setattr__(self, "effects", self.effects + 1)
        return {"status": "PASS"}

    def __iter__(self):
        object.__setattr__(self, "effects", self.effects + 1)
        return iter(())

    def __getattr__(self, _name: str) -> object:
        object.__setattr__(self, "effects", self.effects + 1)
        raise AttributeError

    def model_dump(self) -> object:
        object.__setattr__(self, "effects", self.effects + 1)
        return {"status": "PASS"}


class DictSubclass(dict):
    def items(self):
        raise AssertionError("must not call subclass items")


class ListSubclass(list):
    def __iter__(self):
        raise AssertionError("must not iterate list subclass")


@pytest.mark.parametrize("factory", [Evil, lambda: DictSubclass(status="PASS"), lambda: ListSubclass(["PASS"]), lambda: (item for item in ["PASS"]), lambda: (lambda: {"status": "PASS"})])
def test_executable_and_non_plain_objects_are_rejected_without_side_effects(
    factory: Any, counted_cast: list[int]
) -> None:
    value = factory()
    result = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=value,
        fixture_provider_result=provider_data(),
    )
    if isinstance(value, Evil):
        assert value.effects == 0
    assert result["router_outcome_validation_code"] == "INVALID_ROUTER_OUTCOME"
    assert_high_once(result, counted_cast)


def test_nested_callable_is_rejected_without_execution(counted_cast: list[int]) -> None:
    evil = Evil()
    result = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome={"status": "PASS", "nested": evil},
        fixture_provider_result=provider_data(),
    )
    assert evil.effects == 0
    assert result["router_outcome_validation_code"] == "INVALID_ROUTER_OUTCOME"
    assert_high_once(result, counted_cast)


@pytest.mark.parametrize("container_kind", ["list", "dict"])
def test_cyclic_builtin_outcome_fails_open_without_recursion_error(
    container_kind: str, counted_cast: list[int]
) -> None:
    if container_kind == "list":
        cycle: object = []
        cycle.append(cycle)  # type: ignore[attr-defined]
    else:
        cycle = {"status": "PASS"}
        cycle["cycle"] = cycle  # type: ignore[index]
    result = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=cycle,
        fixture_provider_result=provider_data(),
    )
    assert result["router_outcome_validation_code"] == "INVALID_ROUTER_OUTCOME"
    assert_high_once(result, counted_cast)


def test_excessively_deep_builtin_outcome_fails_open(counted_cast: list[int]) -> None:
    deep: object = "leaf"
    for _ in range(25):
        deep = [deep]
    result = begin_pure_data_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router_outcome=deep,
        fixture_provider_result=provider_data(),
    )
    assert result["router_outcome_validation_code"] == "INVALID_ROUTER_OUTCOME"
    assert_high_once(result, counted_cast)


def test_invalid_resume_and_repeated_resume_do_not_call_high(counted_cast: list[int]) -> None:
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_pure_data_direct_reading(
        payload, router_outcome=outcome("ASK_ONCE", ambiguity_kind="SUBJECT")
    )
    invalid = resume_pure_data_direct_reading(
        {**payload, "numbers": [9, 8, 7]}, waiting, fixture_provider_result=provider_data()
    )
    assert invalid["status"] == "INVALID_RESUME"
    assert counted_cast == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_payload", {"question_text": QUESTION, "numbers": [9, 8, 7], "critical_ambiguity": ambiguity()}),
        ("clarification_prompt", "被篡改的澄清问题？"),
        ("request_sha256", "0" * 64),
        ("router_outcomes_consumed", 0),
        ("unexpected", "extra"),
    ],
)
def test_waiting_envelope_tamper_never_calls_high(
    field: str, value: object, counted_cast: list[int]
) -> None:
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_pure_data_direct_reading(
        payload, router_outcome=outcome("ASK_ONCE", ambiguity_kind="SUBJECT")
    )
    tampered = {**waiting, field: value}
    result = resume_pure_data_direct_reading(
        payload, tampered, user_answer="甲项目", fixture_provider_result=provider_data()
    )
    assert result["status"] == "INVALID_RESUME"
    assert result["high_attempts"] == 0
    assert counted_cast == []
    completed = resume_pure_data_direct_reading(
        payload, waiting, skip_answer=True, fixture_provider_result=provider_data()
    )
    assert_high_once(completed, counted_cast)
    counted_cast.clear()
    repeated = resume_pure_data_direct_reading(
        payload, completed, skip_answer=True, fixture_provider_result=provider_data()
    )
    assert repeated["status"] == "INVALID_RESUME"
    assert counted_cast == []


@pytest.mark.parametrize("text", ["", "## 判断\n空壳"])
def test_high_failure_is_one_cast_one_provider_zero_retry_no_release(
    text: str, counted_cast: list[int]
) -> None:
    result = begin_pure_data_direct_reading(
        request(), fixture_provider_result=provider_data(text=text)
    )
    assert result["high_status"] in {"INCOMPLETE", "BLOCKED_OUTPUT"}
    assert result["high_response"]["direct_reading"] is None
    assert_high_once(result, counted_cast)


def test_high_unavailable_is_one_cast_one_provider_zero_retry_no_release(
    counted_cast: list[int],
) -> None:
    result = begin_pure_data_direct_reading(
        request(),
        fixture_provider_result=provider_data(failure_code="PROVIDER_UNAVAILABLE"),
    )
    assert result["high_status"] == "UNAVAILABLE"
    assert result["high_response"]["direct_reading"] is None
    assert_high_once(result, counted_cast)


def test_invalid_request_has_zero_cast_and_provider(counted_cast: list[int]) -> None:
    result = begin_pure_data_direct_reading(
        {"question_text": "太短", "numbers": [7, 8, 9]},
        fixture_provider_result=provider_data(),
    )
    assert result["status"] == "INVALID_REQUEST"
    assert result["prepare_calls"] == result["deterministic_cast_count"] == result["provider_calls"] == 0
    assert counted_cast == []


def test_unexpected_prepare_exception_is_zero_cast_zero_provider_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_prepare(_: object) -> object:
        raise RuntimeError("fixture prepare failure")

    monkeypatch.setattr(
        "abalo_iching.application.sites_pure_data_router_v014.prepare_direct_reading_v2_request",
        fail_prepare,
    )
    result = begin_pure_data_direct_reading(
        request(), fixture_provider_result=provider_data()
    )
    assert result["high_status"] == "ENGINE_ERROR"
    assert result["prepare_calls"] == result["high_attempts"] == 1
    assert result["deterministic_cast_count"] == result["provider_calls"] == 0
    assert result["high_response"] is None
    assert result["automatic_retries"] == 0


def test_module_api_and_ast_have_no_router_or_high_callback_or_engine_import() -> None:
    source_path = Path("src/abalo_iching/application/sites_pure_data_router_v014.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"Callable", "Protocol", "high_invoker", "cast_meihua", "abalo_iching.meihua"}
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            seen.add(node.id)
        elif isinstance(node, ast.Attribute):
            seen.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in node.names:
                seen.add(name.name)
            if isinstance(node, ast.ImportFrom) and node.module:
                seen.add(node.module)
    assert forbidden.isdisjoint(seen)
    assert "router=" not in source
    assert "provider=" in source  # only the internally constructed fixture provider
