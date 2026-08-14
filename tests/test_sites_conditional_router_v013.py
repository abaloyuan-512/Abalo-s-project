from __future__ import annotations

import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_conditional_router_v013 import (
    COUNT_SOURCE,
    begin_guarded_conditional_direct_reading,
    resume_guarded_conditional_direct_reading,
)


QUESTION = "这次合作，我应该继续投入，还是停止并退出？"
FIXED_CLOCK = lambda: datetime(2026, 8, 13, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
SAVED_PREPARE = high_service.prepare_direct_reading_v2_request
SAVED_CAST = high_service.cast_meihua


def request(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {"question_text": QUESTION, "numbers": [7, 8, 9]}
    payload.update(changes)
    return payload


def ambiguity() -> dict[str, str]:
    return {"kind": "SUBJECT", "description": "所问的合作可能指两个不同项目"}


def router_receipt(decision: object) -> dict[str, object]:
    return {
        "provider_kind": "FIXTURE",
        "real_provider_instantiated": False,
        "decision": decision,
    }


class FixtureRouter:
    def __init__(self, decision: object = None, *, failure: Exception | None = None) -> None:
        self.decision = {"action": "PASS"} if decision is None else decision
        self.failure = failure
        self.calls = 0

    def route(self, **_: object) -> object:
        self.calls += 1
        if self.failure:
            raise self.failure
        return router_receipt(self.decision)


class AuthoritativeFixtureHigh:
    def __init__(self, status: str = "SUCCESS", *, casts: int = 1, prepare: bool = True) -> None:
        self.status = status
        self.casts = casts
        self.prepare = prepare
        self.calls = 0

    def __call__(self, payload: dict[str, Any]) -> object:
        self.calls += 1
        if self.prepare:
            high_service.prepare_direct_reading_v2_request(
                payload,
                clock=FIXED_CLOCK,
                request_id=f"drv2-v013-{self.calls:016x}",
            )
        else:
            for _ in range(self.casts):
                SAVED_CAST(
                    high_service.MeihuaInput(
                        7,
                        8,
                        9,
                        FIXED_CLOCK(),
                        "Asia/Shanghai",
                        "drv2-v013-direct",
                    )
                )
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "cast_count": 1,
            "response": {
                "status": self.status,
                "direct_reading": ({"text": "fixture"} if self.status == "SUCCESS" else None),
                "retryable": False,
            },
        }


def assert_normal(result: dict[str, Any], high: AuthoritativeFixtureHigh) -> None:
    assert result["high_attempts"] == high.calls == 1
    assert result["router_cast_count"] == 0
    assert result["high_prepare_count"] == 1
    assert result["high_cast_count"] == 1
    assert result["total_cast_count"] == 1
    assert result["count_source"] == COUNT_SOURCE
    assert result["automatic_retries"] == 0


@pytest.mark.parametrize(
    "changes",
    [{}, {"user_confirmed": True, "critical_ambiguity": ambiguity()}, {"skip_router": True, "critical_ambiguity": ambiguity()}],
)
def test_direct_paths_have_zero_router_and_one_authoritative_high_cast(changes: dict[str, object]) -> None:
    high = AuthoritativeFixtureHigh()
    result = begin_guarded_conditional_direct_reading(request(**changes), high_invoker=high)
    assert result["router_attempts"] == 0
    assert_normal(result, high)


def test_legal_router_pass_has_zero_router_cast_and_one_high_cast() -> None:
    high = AuthoritativeFixtureHigh()
    router = FixtureRouter()
    result = begin_guarded_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()), router=router, high_invoker=high
    )
    assert router.calls == result["router_attempts"] == 1
    assert result["router_status"] == "PASSED"
    assert_normal(result, high)


def test_ask_once_waits_at_zero_then_resumes_to_one_cast() -> None:
    high = AuthoritativeFixtureHigh()
    router = FixtureRouter({"action": "ASK_ONCE"})
    payload = request(critical_ambiguity=ambiguity())
    waiting = begin_guarded_conditional_direct_reading(
        payload, router=router, high_invoker=high
    )
    assert waiting["status"] == "WAITING_FOR_ONE_ANSWER"
    assert waiting["router_cast_count"] == waiting["high_cast_count"] == waiting["total_cast_count"] == 0
    assert waiting["high_attempts"] == high.calls == 0
    completed = resume_guarded_conditional_direct_reading(
        payload, waiting, user_answer="我问的是甲项目。", high_invoker=high
    )
    assert completed["router_attempts"] == 1
    assert_normal(completed, high)


@pytest.mark.parametrize(
    "router",
    [FixtureRouter(failure=TimeoutError()), FixtureRouter(""), FixtureRouter({"action": "UNKNOWN"}), FixtureRouter({"action": "PASS", "question_text": "改题"})],
)
def test_ordinary_router_failures_fail_open_with_zero_router_cast(router: FixtureRouter) -> None:
    high = AuthoritativeFixtureHigh()
    result = begin_guarded_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()), router=router, high_invoker=high
    )
    assert result["router_status"] == "FAILED_OPEN"
    assert_normal(result, high)


class DirectPrepareRouter:
    def route(self, **_: object) -> object:
        high_service.prepare_direct_reading_v2_request(
            request(), clock=FIXED_CLOCK, request_id="drv2-v013-router1"
        )
        return router_receipt({"action": "PASS"})


class DirectCastRouter:
    def route(self, **_: object) -> object:
        SAVED_CAST(
            high_service.MeihuaInput(7, 8, 9, FIXED_CLOCK(), "Asia/Shanghai", "drv2-v013-router2")
        )
        return router_receipt({"action": "PASS"})


def _indirect_prepare() -> object:
    return SAVED_PREPARE(request(), clock=FIXED_CLOCK, request_id="drv2-v013-router3")


class AliasIndirectPrepareRouter:
    def route(self, **_: object) -> object:
        _indirect_prepare()
        return router_receipt({"action": "PASS"})


@pytest.mark.parametrize("router", [DirectPrepareRouter(), DirectCastRouter(), AliasIndirectPrepareRouter()])
def test_router_prepare_cast_and_saved_alias_are_terminal_boundary_violations(router: object) -> None:
    high = AuthoritativeFixtureHigh()
    result = begin_guarded_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()), router=router, high_invoker=high
    )
    assert result["status"] == "BOUNDARY_VIOLATION"
    assert result["router_status"] == "BOUNDARY_VIOLATION"
    assert result["router_failure_code"] == "ROUTER_CAST_BOUNDARY_VIOLATION"
    assert result["router_cast_count"] >= 1
    assert result["high_attempts"] == high.calls == 0
    assert result["high_status"] is None
    assert result["high_response"] is None
    assert result["total_cast_count"] == result["router_cast_count"]
    assert result["automatic_retries"] == 0


class CatchingPrepareRouter:
    def route(self, **_: object) -> object:
        try:
            _indirect_prepare()
        except BaseException:
            pass
        return router_receipt({"action": "PASS"})


def test_router_cannot_catch_boundary_violation_and_continue_high() -> None:
    high = AuthoritativeFixtureHigh()
    result = begin_guarded_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()), router=CatchingPrepareRouter(), high_invoker=high
    )
    assert result["router_status"] == "BOUNDARY_VIOLATION"
    assert result["high_attempts"] == high.calls == 0


def test_two_high_casts_are_terminal_and_not_released() -> None:
    high = AuthoritativeFixtureHigh(prepare=False, casts=2)
    result = begin_guarded_conditional_direct_reading(request(), high_invoker=high)
    assert result["status"] == "BOUNDARY_VIOLATION"
    assert result["high_status"] == "BOUNDARY_VIOLATION"
    assert result["high_response"] is None
    assert result["high_cast_count"] == result["total_cast_count"] == 2


def test_high_success_without_authoritative_prepare_is_rejected_even_if_receipt_claims_one() -> None:
    def forged(_: dict[str, Any]) -> object:
        return {
            "provider_kind": "FIXTURE",
            "real_provider_instantiated": False,
            "cast_count": 1,
            "response": {"status": "SUCCESS", "direct_reading": {"text": "forged"}},
        }

    result = begin_guarded_conditional_direct_reading(request(), high_invoker=forged)
    assert result["status"] == "BOUNDARY_VIOLATION"
    assert result["high_response"] is None
    assert result["high_cast_count"] == result["total_cast_count"] == 0


def test_high_failure_after_prepare_preserves_real_single_cast_without_retry() -> None:
    high = AuthoritativeFixtureHigh("BLOCKED_OUTPUT")
    result = begin_guarded_conditional_direct_reading(request(), high_invoker=high)
    assert result["high_status"] == "BLOCKED_OUTPUT"
    assert result["high_response"]["direct_reading"] is None
    assert_normal(result, high)


def test_profile_hook_is_restored_after_success_exception_and_boundary_violation() -> None:
    events: list[str] = []

    def existing(_frame: object, event: str, _arg: object) -> None:
        events.append(event)

    previous = sys.getprofile()
    sys.setprofile(existing)
    try:
        begin_guarded_conditional_direct_reading(request(), high_invoker=AuthoritativeFixtureHigh())
        assert sys.getprofile() is existing
        begin_guarded_conditional_direct_reading(
            request(critical_ambiguity=ambiguity()),
            router=DirectCastRouter(),
            high_invoker=AuthoritativeFixtureHigh(),
        )
        assert sys.getprofile() is existing
    finally:
        sys.setprofile(previous)
    assert events


def test_guard_state_does_not_leak_to_next_path() -> None:
    bad = begin_guarded_conditional_direct_reading(
        request(critical_ambiguity=ambiguity()),
        router=DirectCastRouter(),
        high_invoker=AuthoritativeFixtureHigh(),
    )
    assert bad["status"] == "BOUNDARY_VIOLATION"
    high = AuthoritativeFixtureHigh()
    good = begin_guarded_conditional_direct_reading(request(), high_invoker=high)
    assert good["high_status"] == "SUCCESS"
    assert_normal(good, high)
