"""V013 cast-boundary wrapper for the frozen V012 conditional Router.

This module does not change V012.  It observes the authoritative prepare and
cast function bodies across the synchronous Router/high boundaries.  Router
touching either boundary is terminal; high is allowed exactly one prepare and
one cast before a successful release.
"""

from __future__ import annotations

import sys
from types import FrameType
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_conditional_router_v1 import (
    CONTRACT_VERSION as V012_CONTRACT_VERSION,
    WaitingEnvelope,
    begin_conditional_direct_reading,
    resume_conditional_direct_reading,
)


CONTRACT_VERSION = "DRV2_CONDITIONAL_ROUTER_CAST_BOUNDARY_V013"
COUNT_SOURCE = "IN_PROCESS_AUTHORITY_BOUNDARY"


class RouterCastBoundaryViolation(RuntimeError):
    pass


class HighCastBoundaryViolation(RuntimeError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuardedWaitingEnvelope(StrictModel):
    contract_version: Literal[CONTRACT_VERSION]
    status: Literal["WAITING_FOR_ONE_ANSWER"]
    v012_waiting: WaitingEnvelope
    router_prepare_count: Literal[0]
    router_cast_count: Literal[0]
    high_prepare_count: Literal[0]
    high_cast_count: Literal[0]
    total_cast_count: Literal[0]
    count_source: Literal[COUNT_SOURCE]
    high_attempts: Literal[0]
    high_status: None
    high_response: None
    automatic_retries: Literal[0]
    deployment: Literal[False]
    production: Literal[False]
    default_replacement: Literal[False]


class _Counts:
    def __init__(self) -> None:
        self.phase: Literal["IDLE", "ROUTER", "HIGH"] = "IDLE"
        self.router_prepare = 0
        self.router_cast = 0
        self.high_prepare = 0
        self.high_cast = 0
        self.router_violation = False
        self.high_violation = False


class _AuthorityBoundary:
    def __init__(self, counts: _Counts) -> None:
        self.counts = counts
        self.previous: Any = None

    def __enter__(self) -> _AuthorityBoundary:
        self.previous = sys.getprofile()
        sys.setprofile(self._profile)
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        sys.setprofile(self.previous)

    def _profile(self, frame: FrameType, event: str, arg: object) -> None:
        if self.previous is not None:
            self.previous(frame, event, arg)
        if event != "call":
            return
        code = frame.f_code
        is_prepare = code is high_service.prepare_direct_reading_v2_request.__code__
        is_cast = code is high_service.cast_meihua.__code__
        if not is_prepare and not is_cast:
            return
        if self.counts.phase == "ROUTER":
            if is_prepare:
                self.counts.router_prepare += 1
            if is_cast:
                self.counts.router_cast += 1
            self.counts.router_violation = True
            raise RouterCastBoundaryViolation("ROUTER_CAST_BOUNDARY_VIOLATION")
        if self.counts.phase == "HIGH":
            if is_prepare:
                self.counts.high_prepare += 1
                if self.counts.high_prepare > 1:
                    self.counts.high_violation = True
                    raise HighCastBoundaryViolation("HIGH_PREPARE_BOUNDARY_VIOLATION")
            if is_cast:
                self.counts.high_cast += 1
                if self.counts.high_cast > 1:
                    self.counts.high_violation = True
                    raise HighCastBoundaryViolation("HIGH_CAST_BOUNDARY_VIOLATION")


def _router_proxy(router: object, counts: _Counts) -> object:
    class GuardedRouter:
        def route(self, **kwargs: object) -> object:
            counts.phase = "ROUTER"
            try:
                return router.route(**kwargs)  # type: ignore[attr-defined]
            finally:
                counts.phase = "IDLE"

    return GuardedRouter()


def _high_proxy(high_invoker: Callable[[dict[str, Any]], object], counts: _Counts) -> Callable[[dict[str, Any]], object]:
    def invoke(payload: dict[str, Any]) -> object:
        if counts.router_violation:
            raise RouterCastBoundaryViolation("ROUTER_CAST_BOUNDARY_VIOLATION")
        counts.phase = "HIGH"
        try:
            return high_invoker(payload)
        finally:
            counts.phase = "IDLE"

    return invoke


def _accounting(counts: _Counts) -> dict[str, Any]:
    return {
        "router_prepare_count": counts.router_prepare,
        "router_cast_count": counts.router_prepare + counts.router_cast,
        "router_authoritative_cast_events": counts.router_cast,
        "high_prepare_count": counts.high_prepare,
        "high_cast_count": counts.high_cast,
        "total_cast_count": counts.router_prepare + counts.router_cast + counts.high_cast,
        "count_source": COUNT_SOURCE,
    }


def _boundary_failure(result: dict[str, Any], counts: _Counts, *, router: bool) -> dict[str, Any]:
    code = "ROUTER_CAST_BOUNDARY_VIOLATION" if router else "HIGH_CAST_BOUNDARY_VIOLATION"
    status = "BOUNDARY_VIOLATION"
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "route": result.get("route"),
        "original_question_text": result.get("original_question_text"),
        "original_question_sha_before": result.get("original_question_sha_before"),
        "original_question_sha_after": result.get("original_question_sha_after"),
        "original_question_preserved": result.get("original_question_preserved"),
        "router_attempts": result.get("router_attempts", 0),
        "router_status": "BOUNDARY_VIOLATION" if router else result.get("router_status"),
        "router_failure_code": code if router else result.get("router_failure_code"),
        "high_attempts": 0 if router else 1,
        "high_status": None if router else "BOUNDARY_VIOLATION",
        "high_response": None,
        "automatic_retries": 0,
        **_accounting(counts),
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def _finalize(result: dict[str, Any], counts: _Counts) -> dict[str, Any]:
    if counts.router_violation:
        return _boundary_failure(result, counts, router=True)
    if counts.high_violation:
        return _boundary_failure(result, counts, router=False)
    status = result.get("status")
    if status == "WAITING_FOR_ONE_ANSWER":
        waiting = WaitingEnvelope.model_validate(result)
        return GuardedWaitingEnvelope(
            contract_version=CONTRACT_VERSION,
            status="WAITING_FOR_ONE_ANSWER",
            v012_waiting=waiting,
            router_prepare_count=0,
            router_cast_count=0,
            high_prepare_count=0,
            high_cast_count=0,
            total_cast_count=0,
            count_source=COUNT_SOURCE,
            high_attempts=0,
            high_status=None,
            high_response=None,
            automatic_retries=0,
            deployment=False,
            production=False,
            default_replacement=False,
        ).model_dump(mode="json")
    high_status = result.get("high_status")
    if result.get("high_attempts") == 1 and high_status == "SUCCESS":
        if counts.high_prepare != 1 or counts.high_cast != 1:
            counts.high_violation = True
            return _boundary_failure(result, counts, router=False)
    return {
        **result,
        "contract_version": CONTRACT_VERSION,
        **_accounting(counts),
    }


def begin_guarded_conditional_direct_reading(
    request_payload: object,
    *,
    high_invoker: Callable[[dict[str, Any]], object],
    router: object | None = None,
) -> dict[str, Any]:
    counts = _Counts()
    guarded_router = _router_proxy(router, counts) if router is not None else None
    try:
        with _AuthorityBoundary(counts):
            result = begin_conditional_direct_reading(
                request_payload,
                router=guarded_router,  # type: ignore[arg-type]
                high_invoker=_high_proxy(high_invoker, counts),
            )
    except RouterCastBoundaryViolation:
        result = {
            "route": "LIGHT_ROUTER_THEN_HIGH",
            "router_attempts": 1,
            "original_question_preserved": True,
        }
    except HighCastBoundaryViolation:
        result = {"route": "DIRECT_HIGH", "router_attempts": 0}
    return _finalize(result, counts)


def resume_guarded_conditional_direct_reading(
    request_payload: object,
    waiting_payload: object,
    *,
    high_invoker: Callable[[dict[str, Any]], object],
    user_answer: object | None = None,
    skip_answer: bool = False,
) -> dict[str, Any]:
    try:
        waiting = GuardedWaitingEnvelope.model_validate(waiting_payload)
    except (ValidationError, ValueError, TypeError):
        return {"contract_version": CONTRACT_VERSION, "status": "INVALID_RESUME"}
    counts = _Counts()
    try:
        with _AuthorityBoundary(counts):
            result = resume_conditional_direct_reading(
                request_payload,
                waiting.v012_waiting.model_dump(mode="json"),
                user_answer=user_answer,
                skip_answer=skip_answer,
                high_invoker=_high_proxy(high_invoker, counts),
            )
    except HighCastBoundaryViolation:
        result = {"route": "LIGHT_ROUTER_THEN_HIGH", "router_attempts": 1}
    return _finalize(result, counts)


__all__ = [
    "CONTRACT_VERSION",
    "COUNT_SOURCE",
    "begin_guarded_conditional_direct_reading",
    "resume_guarded_conditional_direct_reading",
]
