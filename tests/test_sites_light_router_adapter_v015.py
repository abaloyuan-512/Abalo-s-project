from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_light_router_adapter_v015 import (
    MAX_OUTPUT_TOKENS,
    MODEL,
    REASONING_EFFORT,
    SYSTEM_PROMPT,
    TIMEOUT_SECONDS,
    OpenAILightRouterAdapter,
    build_openai_request,
    run_fixture_light_router_adapter,
    run_without_provider,
)
from abalo_iching.application.sites_pure_data_router_v014 import (
    begin_pure_data_direct_reading,
    resume_pure_data_direct_reading,
)
from tests.test_sites_direct_reading_v2 import _complete_text


QUESTION = "这次合作，我应该继续投入，还是停止并退出？"
KINDS = ("SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT")


def adapter_request(kind: str = "SUBJECT", **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "original_question": QUESTION,
        "critical_ambiguity": {
            "kind": kind,
            "description": "这个表述可能指向两个不同对象",
        },
    }
    value.update(changes)
    return value


def v014_request(kind: str = "SUBJECT") -> dict[str, object]:
    return {
        "question_text": QUESTION,
        "numbers": [7, 8, 9],
        "critical_ambiguity": {
            "kind": kind,
            "description": "这个表述可能指向两个不同对象",
        },
    }


def high_fixture() -> dict[str, object]:
    return {
        "output_text": _complete_text(
            base="地天泰",
            mutual="雷泽归妹",
            changed="地泽临",
            line_name="初九",
            line_text="拔茅茹，以其汇。征吉。",
        ),
        "api_status": "completed",
        "incomplete_details": None,
        "response_id": "fixture-v015-high",
        "model": "gpt-5.6-sol",
        "input_tokens": 200,
        "output_tokens": 2000,
        "latency_ms": 10,
    }


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def assert_adapter_audit(
    outcome: dict[str, str],
    audit: dict[str, Any],
    *,
    attempts: int,
    fixture_calls: int,
) -> None:
    assert type(outcome) is dict
    assert json.loads(json.dumps(outcome, ensure_ascii=False, sort_keys=True)) == outcome
    assert audit["question_sha_before"] == audit["question_sha_after"] == sha(QUESTION)
    assert audit["question_sha_sent"] == (sha(QUESTION) if attempts else None)
    assert audit["original_question_preserved"] is True
    assert audit["provider_attempts"] == attempts
    assert audit["fixture_transport_calls"] == fixture_calls
    assert audit["router_live_calls"] == audit["live_calls"] == 0
    assert audit["real_provider_instantiated"] is False
    assert audit["router_prepare_calls"] == audit["router_cast_count"] == 0
    assert audit["router_process_calls"] == audit["router_high_calls"] == 0
    assert audit["automatic_retries"] == 0
    assert audit["canonical_round_trip"] is True
    assert audit["outcome_sha256"] == sha(
        json.dumps(outcome, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    assert QUESTION not in json.dumps(audit, ensure_ascii=False)


def test_openai_shape_is_bounded_and_contains_only_question_and_typed_ambiguity() -> None:
    built = build_openai_request(adapter_request())
    assert built["model"] == MODEL == "gpt-5.6-luna"
    assert REASONING_EFFORT == "low"
    assert built["reasoning"] == {"effort": REASONING_EFFORT}
    assert built["store"] is False
    assert built["tools"] == []
    assert built["max_output_tokens"] == MAX_OUTPUT_TOKENS == 128
    assert TIMEOUT_SECONDS == 15.0
    user_payload = json.loads(built["input"][1]["content"])  # type: ignore[index]
    assert user_payload == adapter_request()
    assert set(user_payload) == {"original_question", "critical_ambiguity"}
    serialized = json.dumps(built["input"], ensure_ascii=False)
    for forbidden in ("numbers", "chart", "optional_context", "framed_question", "cast_time"):
        assert forbidden not in serialized
    assert "不得改写问题" in SYSTEM_PROMPT


def test_adapter_module_has_no_chart_or_high_capability() -> None:
    import abalo_iching.application.sites_light_router_adapter_v015 as module

    source = Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any("meihua" in name or "sites_direct_reading" in name for name in imported)
    forbidden_names = {
        "cast_meihua",
        "prepare_direct_reading_v2_request",
        "process_prepared_direct_reading_v2_request",
        "begin_pure_data_direct_reading",
    }
    assert not ({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} & forbidden_names)
    for function in (run_fixture_light_router_adapter, run_without_provider, build_openai_request):
        parameters = inspect.signature(function).parameters
        assert not ({"numbers", "chart", "provider", "callback", "high", "high_invoker"} & set(parameters))


@pytest.mark.parametrize("kind", KINDS)
def test_pass_and_ask_three_kinds_are_exact_plain_outcomes(kind: str) -> None:
    passed, pass_audit = run_fixture_light_router_adapter(
        adapter_request(kind), fixture_response={"status": "PASS"}, fixture_latency_ms=4
    )
    assert passed == {"status": "PASS"}
    assert pass_audit["raw_receipt_sha256"] is not None
    assert_adapter_audit(passed, pass_audit, attempts=1, fixture_calls=1)
    asked, ask_audit = run_fixture_light_router_adapter(
        adapter_request(kind),
        fixture_response={"status": "ASK_ONCE", "ambiguity_kind": kind},
    )
    assert asked == {"status": "ASK_ONCE", "ambiguity_kind": kind}
    assert_adapter_audit(asked, ask_audit, attempts=1, fixture_calls=1)


@pytest.mark.parametrize("failure_code", ["UNAVAILABLE", "TIMEOUT", "INVALID_OUTPUT"])
def test_provider_cannot_self_declare_adapter_failure(failure_code: str) -> None:
    outcome, audit = run_fixture_light_router_adapter(
        adapter_request(),
        fixture_response={"status": "FAILED", "failure_code": failure_code},
    )
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert audit["provider_status"] == "FAILED"
    assert_adapter_audit(outcome, audit, attempts=1, fixture_calls=1)


@pytest.mark.parametrize(
    ("behavior", "failure_code"),
    [("TIMEOUT", "TIMEOUT"), ("EXCEPTION", "UNAVAILABLE")],
)
def test_transport_failures_are_stable_single_attempt_without_detail_leak(
    behavior: str, failure_code: str
) -> None:
    outcome, audit = run_fixture_light_router_adapter(
        adapter_request(), fixture_response={"status": "PASS"}, fixture_behavior=behavior
    )
    assert outcome == {"status": "FAILED", "failure_code": failure_code}
    assert "detail must not escape" not in json.dumps({"outcome": outcome, "audit": audit})
    assert_adapter_audit(outcome, audit, attempts=1, fixture_calls=1)


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        "",
        "not json",
        [],
        {},
        {"status": "UNKNOWN"},
        {"status": "PASS", "question_text": "改写问题"},
        {"status": "PASS", "facts": ["新增事实"]},
        {"status": "PASS", "date": "明天"},
        {"status": "PASS", "guarantee": True},
        {"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT", "question": "自由问题"},
        {"status": "ASK_ONCE", "ambiguity_kind": "DECISION_AXIS"},
        {"status": "FAILED"},
    ],
)
def test_invalid_provider_outputs_become_invalid_output(invalid: object) -> None:
    outcome, audit = run_fixture_light_router_adapter(adapter_request(), fixture_response=invalid)
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert_adapter_audit(outcome, audit, attempts=1, fixture_calls=1)


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
        raise AssertionError("must not call custom items")


class ListSubclass(list):
    def __iter__(self):
        raise AssertionError("must not iterate custom list")


@pytest.mark.parametrize(
    "factory",
    [
        Evil,
        lambda: DictSubclass(status="PASS"),
        lambda: ListSubclass(["PASS"]),
        lambda: (item for item in ["PASS"]),
        lambda: (lambda: {"status": "PASS"}),
    ],
)
def test_malicious_objects_are_rejected_without_execution(factory: Any) -> None:
    value = factory()
    outcome, audit = run_fixture_light_router_adapter(adapter_request(), fixture_response=value)
    if isinstance(value, Evil):
        assert value.effects == 0
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert_adapter_audit(outcome, audit, attempts=1, fixture_calls=1)


def test_nested_evil_cycle_and_depth_are_rejected_without_execution() -> None:
    evil = Evil()
    outcome, _ = run_fixture_light_router_adapter(
        adapter_request(), fixture_response={"status": "PASS", "nested": evil}
    )
    assert evil.effects == 0
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    cycle: dict[str, object] = {"status": "PASS"}
    cycle["cycle"] = cycle
    assert run_fixture_light_router_adapter(adapter_request(), fixture_response=cycle)[0] == {
        "status": "FAILED",
        "failure_code": "INVALID_OUTPUT",
    }
    deep: object = "leaf"
    for _ in range(25):
        deep = [deep]
    assert run_fixture_light_router_adapter(adapter_request(), fixture_response=deep)[0] == {
        "status": "FAILED",
        "failure_code": "INVALID_OUTPUT",
    }


def test_invalid_request_is_zero_attempt_and_provider_absent_is_fail_safe() -> None:
    outcome, audit = run_fixture_light_router_adapter(
        {**adapter_request(), "numbers": [1, 2, 3]}, fixture_response={"status": "PASS"}
    )
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert audit["terminal_status"] == "INVALID_REQUEST"
    assert audit["provider_attempts"] == audit["fixture_transport_calls"] == 0
    assert audit["question_sha_before"] is None
    absent, absent_audit = run_without_provider(adapter_request())
    assert absent == {"status": "FAILED", "failure_code": "UNAVAILABLE"}
    assert absent_audit["provider_kind"] == "ABSENT"
    assert_adapter_audit(absent, absent_audit, attempts=0, fixture_calls=0)


@pytest.mark.parametrize(
    "changed_question",
    [
        f"  {QUESTION}  ",
        QUESTION.replace("，", "，  "),
        "Cafe\u0301 collaboration: should I continue or exit?",
    ],
)
def test_question_that_would_be_normalized_is_rejected_without_provider_attempt(
    changed_question: str,
) -> None:
    payload = adapter_request()
    payload["original_question"] = changed_question
    outcome, audit = run_fixture_light_router_adapter(
        payload, fixture_response={"status": "PASS"}
    )
    assert outcome == {"status": "FAILED", "failure_code": "INVALID_OUTPUT"}
    assert audit["terminal_status"] == "INVALID_REQUEST"
    assert audit["provider_attempts"] == audit["fixture_transport_calls"] == 0
    assert audit["question_sha_before"] is None


def test_adapter_does_not_read_api_key_or_instantiate_real_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    import abalo_iching.application.sites_light_router_adapter_v015 as module

    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-read-offline")

    class ForbiddenOpenAI:
        def __init__(self, **_: object) -> None:
            raise AssertionError("real OpenAI must not be instantiated")

    monkeypatch.setattr(module, "OpenAI", ForbiddenOpenAI)
    outcome, audit = run_fixture_light_router_adapter(
        adapter_request(), fixture_response={"status": "PASS"}
    )
    assert outcome == {"status": "PASS"}
    assert audit["real_provider_instantiated"] is False


def test_explicit_real_adapter_is_single_use_without_calling_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = OpenAILightRouterAdapter()
    outcome, audit = adapter.route_once(adapter_request())
    assert outcome == {"status": "FAILED", "failure_code": "UNAVAILABLE"}
    assert audit["provider_attempts"] == audit["live_calls"] == 0
    with pytest.raises(RuntimeError, match="single-use"):
        adapter.route_once(adapter_request())


@pytest.fixture
def counted_cast(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    real = high_service.cast_meihua
    calls: list[int] = []

    def count(value: object) -> object:
        calls.append(1)
        return real(value)

    monkeypatch.setattr(high_service, "cast_meihua", count)
    return calls


def test_adapter_to_v014_pass_is_data_only_then_one_high(counted_cast: list[int]) -> None:
    outcome, audit = run_fixture_light_router_adapter(
        adapter_request(), fixture_response={"status": "PASS"}
    )
    assert audit["router_cast_count"] == 0 and counted_cast == []
    diode = json.loads(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    result = begin_pure_data_direct_reading(
        v014_request(), router_outcome=diode, fixture_provider_result=high_fixture()
    )
    assert result["router_outcome_status"] == "PASS"
    assert result["router_outcomes_consumed"] == 1
    assert result["high_attempts"] == result["deterministic_cast_count"] == 1
    assert len(counted_cast) == 1
    assert result["original_question_sha_before"] == result["original_question_sha_after"]


def test_adapter_to_v014_failed_fails_open_to_one_high(counted_cast: list[int]) -> None:
    outcome, _ = run_fixture_light_router_adapter(adapter_request(), fixture_behavior="TIMEOUT")
    result = begin_pure_data_direct_reading(
        v014_request(), router_outcome=outcome, fixture_provider_result=high_fixture()
    )
    assert result["router_outcome_status"] == "FAILED"
    assert result["router_outcome_validation_code"] == "TIMEOUT"
    assert result["high_attempts"] == 1 and len(counted_cast) == 1


@pytest.mark.parametrize(("answer", "skip"), [("我问的是甲项目", False), (None, True)])
def test_adapter_to_v014_ask_waits_then_answer_or_skip_goes_one_high(
    answer: str | None, skip: bool, counted_cast: list[int]
) -> None:
    outcome, _ = run_fixture_light_router_adapter(
        adapter_request(),
        fixture_response={"status": "ASK_ONCE", "ambiguity_kind": "SUBJECT"},
    )
    payload = v014_request()
    waiting = begin_pure_data_direct_reading(payload, router_outcome=outcome)
    assert waiting["status"] == "WAITING_FOR_ONE_ANSWER"
    assert waiting["high_attempts"] == 0 and counted_cast == []
    result = resume_pure_data_direct_reading(
        payload,
        waiting,
        user_answer=answer,
        skip_answer=skip,
        fixture_provider_result=high_fixture(),
    )
    assert result["high_attempts"] == 1 and len(counted_cast) == 1
    assert result["original_question_preserved"] is True


def test_v014_and_authority_files_are_not_changed() -> None:
    root = Path(__file__).resolve().parents[1]
    locked = {
        "src/abalo_iching/application/sites_pure_data_router_v014.py": "CB2A3827AC433403F1D0F38DE5E0B0456D1D4FC99B49DBF5F285B6814BCA51BB",
        "src/abalo_iching/application/sites_direct_reading_v2.py": "1CD851EE815F876A693F84B0632C1FFC6F20C12768EEA7E1313B289DCB23B928",
        "evals/meihua/direct_reading_v2_pure_data_router_v014/candidate_manifest.json": "CAAF3FC09E7AFE33022F9A4E9A57E6D1F4F9D0AB79F5C01D05B409B7232B2C67",
    }
    for relative, expected in locked.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest().upper() == expected
