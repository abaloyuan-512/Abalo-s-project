from __future__ import annotations

from typing import Any

import pytest

from abalo_iching.application.sites_conditional_router_v1 import (
    begin_conditional_direct_reading,
    resume_conditional_direct_reading,
)


QUESTION = "这次合作，我应该继续投入，还是停止并退出？"


class StubRouter:
    def __init__(self, result: object = None, *, failure: Exception | None = None) -> None:
        self.result = {"action": "PASS"} if result is None else result
        self.failure = failure
        self.calls: list[dict[str, str]] = []

    def route(
        self,
        *,
        original_question: str,
        critical_ambiguity_kind: str,
        critical_ambiguity_description: str,
    ) -> object:
        self.calls.append(
            {
                "original_question": original_question,
                "critical_ambiguity_kind": critical_ambiguity_kind,
                "critical_ambiguity_description": critical_ambiguity_description,
            }
        )
        if self.failure is not None:
            raise self.failure
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "decision": self.result,
        }


class StubHigh:
    def __init__(self, *, status: str = "SUCCESS", failure: Exception | None = None) -> None:
        self.status = status
        self.failure = failure
        self.calls: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if self.failure is not None:
            raise self.failure
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "cast_count": 1,
            "response": {
                "status": self.status,
                "direct_reading": {"text": "fixture only"} if self.status == "SUCCESS" else None,
                "retryable": False,
            },
        }


def request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "question_text": QUESTION,
        "numbers": [7, 8, 9],
    }
    value.update(changes)
    return value


def ambiguity(kind: str = "SUBJECT") -> dict[str, str]:
    return {"kind": kind, "description": "所问的合作可能指两个不同项目"}


def assert_one_high(result: dict[str, Any], high: StubHigh) -> None:
    assert result["high_attempts"] == result["cast_count"] == 1
    assert result["automatic_retries"] == 0
    assert len(high.calls) == 1
    assert high.calls[0]["question_text"] == QUESTION
    assert result["original_question_text"] == QUESTION
    assert result["original_question_sha_before"] == result["original_question_sha_after"]
    assert result["original_question_preserved"] is True
    assert result["high_provider_kind"] == "FIXTURE"
    assert result["high_real_provider_instantiated"] is False


def test_clear_question_goes_directly_to_high_without_router() -> None:
    router = StubRouter()
    high = StubHigh()

    result = begin_conditional_direct_reading(request(), router=router, high_invoker=high)

    assert result["route"] == "DIRECT_HIGH"
    assert result["clarity_result"] == "CLEAR"
    assert result["router_attempts"] == 0
    assert router.calls == []
    assert_one_high(result, high)


def test_user_confirmation_goes_directly_to_high() -> None:
    router = StubRouter()
    high = StubHigh()

    result = begin_conditional_direct_reading(
        request(user_confirmed=True, critical_ambiguity=ambiguity()),
        router=router,
        high_invoker=high,
    )

    assert result["clarity_result"] == "CONFIRMED"
    assert result["router_attempts"] == 0
    assert router.calls == []
    assert_one_high(result, high)


def test_explicit_skip_overrides_critical_ambiguity() -> None:
    router = StubRouter()
    high = StubHigh()

    result = begin_conditional_direct_reading(
        request(skip_router=True, critical_ambiguity=ambiguity()),
        router=router,
        high_invoker=high,
    )

    assert result["clarity_result"] == "SKIPPED"
    assert result["router_attempts"] == 0
    assert router.calls == []
    assert_one_high(result, high)


def test_preexisting_critical_ambiguity_can_pass_once_then_high() -> None:
    router = StubRouter({"action": "PASS"})
    high = StubHigh()

    result = begin_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router=router,
        high_invoker=high,
    )

    assert result["route"] == "LIGHT_ROUTER_THEN_HIGH"
    assert result["router_attempts"] == len(router.calls) == 1
    assert set(router.calls[0]) == {
        "original_question",
        "critical_ambiguity_kind",
        "critical_ambiguity_description",
    }
    assert "numbers" not in router.calls[0]
    assert result["router_status"] == "PASSED"
    assert_one_high(result, high)


def test_ask_once_waits_without_cast_then_user_answer_goes_to_high() -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())

    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)

    assert waiting["status"] == "WAITING_FOR_ONE_ANSWER"
    assert waiting["router_attempts"] == 1
    assert waiting["high_attempts"] == 0
    assert waiting["cast_count"] is None
    assert high.calls == []

    completed = resume_conditional_direct_reading(
        payload,
        waiting,
        user_answer="我问的是甲项目。",
        high_invoker=high,
    )

    assert completed["router_attempts"] == 1
    assert completed["router_status"] == "ASKED_ONCE"
    assert completed["resume_mode"] == "USER_ANSWER"
    assert high.calls[0]["optional_context"] == {
        "discernment_note": "[用户一次澄清原话] 我问的是甲项目。"
    }
    assert_one_high(completed, high)


def test_user_answer_merges_with_existing_context_without_replacing_framed_question() -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(
        critical_ambiguity=ambiguity(),
        optional_context={
            "discernment_note": "这是用户原有背景。",
            "framed_question": "这是用户原有定问。",
        },
    )
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)
    completed = resume_conditional_direct_reading(
        payload, waiting, user_answer="我问的是甲项目。", high_invoker=high
    )
    assert completed["user_answer_context_applied"] is True
    assert high.calls[0]["optional_context"] == {
        "discernment_note": "这是用户原有背景。\n[用户一次澄清原话] 我问的是甲项目。",
        "framed_question": "这是用户原有定问。",
    }


def test_answer_is_dropped_if_merge_would_overflow_existing_context() -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(
        critical_ambiguity=ambiguity(),
        optional_context={"discernment_note": "甲" * 390},
    )
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)
    completed = resume_conditional_direct_reading(
        payload, waiting, user_answer="我问的是甲项目。", high_invoker=high
    )
    assert completed["user_answer_context_applied"] is False
    assert high.calls[0]["optional_context"] == {"discernment_note": "甲" * 390}


@pytest.mark.parametrize(
    ("kind", "prompt"),
    [
        ("SUBJECT", "你这次所问的主体具体是哪一个？"),
        ("DECISION_AXIS", "你希望比较的两个互斥选择分别是什么？"),
        ("JUDGMENT_OBJECT", "你这次希望判断的具体对象是哪一个？"),
    ],
)
def test_each_critical_ambiguity_kind_uses_one_fixed_program_prompt(
    kind: str, prompt: str
) -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    result = begin_conditional_direct_reading(
        request(critical_ambiguity=ambiguity(kind)), router=router, high_invoker=high
    )
    assert result["clarification_prompt"] == prompt
    assert high.calls == []
    assert set(router.calls[0]) == {
        "original_question",
        "critical_ambiguity_kind",
        "critical_ambiguity_description",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: {**payload, "numbers": [9, 8, 7]},
        lambda payload: {**payload, "optional_context": {"discernment_note": "被换掉"}},
        lambda payload: {**payload, "critical_ambiguity": ambiguity("DECISION_AXIS")},
    ],
)
def test_resume_rejects_changed_numbers_or_context(mutation: Any) -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)
    result = resume_conditional_direct_reading(
        mutation(payload), waiting, user_answer="甲项目", high_invoker=high
    )
    assert result["status"] == "INVALID_RESUME"
    assert high.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("route", "DIRECT_HIGH"),
        ("clarity_result", "CLEAR"),
        ("high_attempts", 1),
        ("cast_count", 1),
        ("router_attempts", 0),
        ("clarification_prompt", "任意篡改？"),
        ("unexpected", "extra"),
    ],
)
def test_resume_rejects_any_waiting_envelope_tamper(field: str, value: object) -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)
    tampered = {**waiting, field: value}
    result = resume_conditional_direct_reading(
        payload, tampered, user_answer="甲项目", high_invoker=high
    )
    assert result["status"] == "INVALID_RESUME"
    assert high.calls == []


def test_invalid_offline_high_receipt_does_not_claim_cast_or_provider() -> None:
    calls: list[dict[str, Any]] = []

    def invalid_high(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {"status": "SUCCESS", "cast_count": 1}

    result = begin_conditional_direct_reading(request(), high_invoker=invalid_high)
    assert len(calls) == result["high_attempts"] == 1
    assert result["cast_count"] is None
    assert result["high_provider_kind"] is None
    assert result["high_real_provider_instantiated"] is None
    assert result["high_status"] == "UNAVAILABLE"


def test_invalid_router_receipt_fails_open_without_provider_claim() -> None:
    class InvalidReceiptRouter:
        def route(self, **_: object) -> object:
            return {"decision": {"action": "PASS"}}

    high = StubHigh()
    result = begin_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router=InvalidReceiptRouter(),
        high_invoker=high,
    )
    assert result["router_failure_code"] == "ROUTER_RECEIPT_INVALID"
    assert result["router_provider_kind"] is None
    assert result["router_real_provider_instantiated"] is None
    assert_one_high(result, high)


@pytest.mark.parametrize("field", ["user_confirmed", "skip_router"])
def test_boolean_flags_are_strict(field: str) -> None:
    high = StubHigh()
    result = begin_conditional_direct_reading(
        request(**{field: 1}), high_invoker=high
    )
    assert result["status"] == "INVALID_REQUEST"
    assert high.calls == []


def test_request_extra_fields_are_rejected() -> None:
    high = StubHigh()
    result = begin_conditional_direct_reading(
        request(suggested_question="覆盖原问题"), high_invoker=high
    )
    assert result["status"] == "INVALID_REQUEST"
    assert high.calls == []


@pytest.mark.parametrize("resume", [{"skip_answer": True}, {"user_answer": "\u200b"}])
def test_ask_once_skip_or_invalid_answer_still_goes_to_high_without_context(
    resume: dict[str, object],
) -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)

    completed = resume_conditional_direct_reading(
        payload, waiting, high_invoker=high, **resume
    )

    assert completed["router_attempts"] == 1
    assert completed["resume_mode"] == "SKIP_OR_INVALID_ANSWER"
    assert "optional_context" not in high.calls[0]
    assert_one_high(completed, high)


@pytest.mark.parametrize(
    ("router", "failure_code"),
    [
        (None, "ROUTER_UNAVAILABLE"),
        (StubRouter(failure=TimeoutError("timeout")), "ROUTER_UNAVAILABLE"),
        (StubRouter(""), "ROUTER_EMPTY"),
        (StubRouter({"action": "UNKNOWN"}), "ROUTER_SCHEMA_INVALID"),
        (StubRouter({"action": "ASK_ONCE", "clarification_prompt": "越权问题？"}), "ROUTER_SCHEMA_INVALID"),
        (
            StubRouter({"action": "PASS", "question_text": "替换后的问题"}),
            "ROUTER_FORBIDDEN_FIELD",
        ),
        (
            StubRouter({"action": "PASS", "facts": ["你们已经签约"]}),
            "ROUTER_FORBIDDEN_FIELD",
        ),
    ],
)
def test_router_failures_and_unauthorized_output_fail_open_to_original_high(
    router: StubRouter | None, failure_code: str
) -> None:
    high = StubHigh()

    result = begin_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router=router,
        high_invoker=high,
    )

    assert result["router_status"] == "FAILED_OPEN"
    assert result["router_failure_code"] == failure_code
    assert result["router_attempts"] == (0 if router is None else 1)
    assert_one_high(result, high)


def test_ordinary_missing_execution_detail_does_not_trigger_router() -> None:
    router = StubRouter()
    high = StubHigh()
    result = begin_conditional_direct_reading(
        request(optional_context={"discernment_note": "我还不知道具体预算。"}),
        router=router,
        high_invoker=high,
    )
    assert result["clarity_result"] == "CLEAR"
    assert router.calls == []
    assert_one_high(result, high)


def test_high_failure_is_not_retried_or_released() -> None:
    router = StubRouter({"action": "PASS"})
    high = StubHigh(status="BLOCKED_OUTPUT")

    result = begin_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router=router,
        high_invoker=high,
    )

    assert_one_high(result, high)
    assert result["high_status"] == "BLOCKED_OUTPUT"
    assert result["high_response"]["direct_reading"] is None
    assert result["automatic_retries"] == 0


def test_unexpected_high_exception_is_safe_and_not_retried() -> None:
    high = StubHigh(failure=RuntimeError("secret raw exception"))
    result = begin_conditional_direct_reading(request(), high_invoker=high)
    assert result["high_status"] == "UNAVAILABLE"
    assert result["high_response"]["direct_reading"] is None
    assert result["high_response"]["error_code"] == "HIGH_UNAVAILABLE"
    assert result["automatic_retries"] == 0
    assert result["cast_count"] is None
    assert result["high_provider_kind"] is None
    assert result["high_real_provider_instantiated"] is None
    assert len(high.calls) == 1


def test_waiting_result_cannot_be_resumed_with_a_changed_question() -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)

    result = resume_conditional_direct_reading(
        {**payload, "question_text": "替换后的问题足够长而且看似有效？"},
        waiting,
        user_answer="甲项目",
        high_invoker=high,
    )

    assert result["status"] == "INVALID_RESUME"
    assert high.calls == []


def test_router_is_never_called_twice_after_waiting() -> None:
    router = StubRouter({"action": "ASK_ONCE"})
    high = StubHigh()
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_conditional_direct_reading(payload, router=router, high_invoker=high)
    completed = resume_conditional_direct_reading(
        payload,
        waiting,
        user_answer="甲项目",
        high_invoker=high,
    )

    assert len(router.calls) == completed["router_attempts"] == 1
    assert_one_high(completed, high)


def test_invalid_request_never_calls_router_or_high() -> None:
    router = StubRouter()
    high = StubHigh()
    result = begin_conditional_direct_reading(
        {"question_text": "太短", "numbers": [7, 8, 9]},
        router=router,
        high_invoker=high,
    )
    assert result["status"] == "INVALID_REQUEST"
    assert result["router_attempts"] == result["high_attempts"] == 0
    assert result["cast_count"] is None
    assert router.calls == high.calls == []
