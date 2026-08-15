from __future__ import annotations

from dataclasses import dataclass

import pytest

from abalo_iching.application.sites_conditional_intake_product_v1 import (
    CLARIFICATION_PROMPTS,
    CONTRACT_VERSION,
    SYSTEM_PROMPT,
    ConditionalIntakeDecision,
    process_conditional_intake_request,
)


QUESTION = "我和合伙人各自负责一个项目；现在应该暂停这个项目吗？"


def test_prompt_locks_critical_pronoun_ambiguity_boundary() -> None:
    assert "这个项目" in SYSTEM_PROMPT
    assert "必须 ASK_ONCE" in SYSTEM_PROMPT
    assert "JUDGMENT_OBJECT" in SYSTEM_PROMPT


@dataclass
class FixtureProvider:
    decision: ConditionalIntakeDecision | None = None
    fail: bool = False
    calls: int = 0

    def classify(self, request):
        self.calls += 1
        assert request.original_question == QUESTION
        if self.fail:
            raise RuntimeError("fixture detail must not escape")
        assert self.decision is not None
        return self.decision


def request() -> dict[str, str]:
    return {
        "contract_version": CONTRACT_VERSION,
        "intake_id": "intake-1111111111111111",
        "original_question": QUESTION,
    }


def test_clear_question_passes_without_question_or_cast_side_effects() -> None:
    provider = FixtureProvider(ConditionalIntakeDecision(status="PASS"))
    result = process_conditional_intake_request(request(), provider=provider)
    assert result["status"] == "PASS"
    assert result["clarification_prompt"] is None
    assert result["router_attempts"] == provider.calls == 1
    assert result["router_cast_count"] == result["router_high_calls"] == 0
    assert result["original_question_sha_before"] == result["original_question_sha_after"]


@pytest.mark.parametrize("kind", tuple(CLARIFICATION_PROMPTS))
def test_each_critical_ambiguity_can_trigger_only_one_program_question(kind: str) -> None:
    provider = FixtureProvider(ConditionalIntakeDecision(status="ASK_ONCE", ambiguity_kind=kind))
    result = process_conditional_intake_request(request(), provider=provider)
    assert result["status"] == "ASK_ONCE"
    assert result["ambiguity_kind"] == kind
    assert result["clarification_prompt"] == CLARIFICATION_PROMPTS[kind]
    assert provider.calls == 1
    assert set(result).isdisjoint({"numbers", "chart", "question_rewrite", "free_question"})


def test_router_failure_fails_open_without_retry_or_exception_text() -> None:
    provider = FixtureProvider(fail=True)
    result = process_conditional_intake_request(request(), provider=provider)
    assert result["status"] == "PASS"
    assert result["failure_code"] == "ROUTER_INVALID_OR_UNKNOWN_FAIL_OPEN"
    assert result["automatic_retries"] == 0
    assert provider.calls == 1
    assert "fixture detail" not in str(result)


@pytest.mark.parametrize(
    "change",
    [
        {"original_question": f" {QUESTION}"},
        {"original_question": "太短"},
        {"intake_id": "wrong"},
        {"extra": "not allowed"},
    ],
)
def test_invalid_request_never_calls_provider(change: dict[str, str]) -> None:
    payload = {**request(), **change}
    provider = FixtureProvider(ConditionalIntakeDecision(status="PASS"))
    result = process_conditional_intake_request(payload, provider=provider)
    assert result["status"] == "INVALID_REQUEST"
    assert result["router_attempts"] == 0
    assert provider.calls == 0
