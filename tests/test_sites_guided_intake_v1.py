from __future__ import annotations

from types import SimpleNamespace

import pytest

from abalo_iching.application.sites_guided_intake_v1 import (
    CONTRACT_VERSION,
    GuidedIntakeModelOutput,
    OpenAIGuidedIntakeProvider,
    SYSTEM_INSTRUCTIONS,
    process_sites_guided_intake_v1_request,
)
from abalo_iching.application.sites_question_context_v1 import DecisionStage, KeyUncertainty
from abalo_iching.application.sites_structured_question_v1 import (
    DecisionGoal,
    DecisionRiskProfile,
    QuestionDomain,
    TimeHorizon,
)


def request_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "intake-session-001",
        "question_text": "这次合作，我还应该继续投入吗？",
        "turns": [
            {"question": "事情已经走到哪一步？", "answer": "方案已经提交，对方两周没有回复。"},
            {"question": "哪些是已确认的事实？", "answer": "我们已经沟通过两次。"},
            {"question": "哪一部分仍然未知？", "answer": "不知道负责人是否看过方案。"},
        ],
        "locale": "zh-CN",
    }


def test_prompt_stops_when_context_is_sufficient_instead_of_chasing_a_fixed_count() -> None:
    assert "不得为了达到固定题数继续追问" in SYSTEM_INSTRUCTIONS
    assert "通常在 4 至 6 次回答内完成，最多 8 次" in SYSTEM_INSTRUCTIONS
    assert "不要机械追问" in SYSTEM_INSTRUCTIONS
    assert "必须是一句完整、自然、可直接默念的中文问句" in SYSTEM_INSTRUCTIONS
    assert "不得返回行动清单" in SYSTEM_INSTRUCTIONS


def complete_output() -> GuidedIntakeModelOutput:
    return GuidedIntakeModelOutput(
        is_complete=True,
        assistant_message="信息已经足够，我们来确认真正要问的核心。",
        next_question=None,
        suggested_question="这次合作中，我下一步最该核实什么，再决定是否继续投入？",
        question_change_reason="把未知条件与可采取的行动说得更清楚。",
        question_domain=QuestionDomain.PROJECT_COOPERATION,
        decision_goal=DecisionGoal.OBSERVE_VERIFY_SIGNALS,
        time_horizon=TimeHorizon.CURRENT,
        decision_stage=DecisionStage.WAITING_FEEDBACK,
        key_uncertainty=KeyUncertainty.OTHER_RESPONSE,
        decision_risk_profile=DecisionRiskProfile.STANDARD,
        confirmed_facts=["我们已经沟通过两次。", "模型擅自补写的事实"],
        unknowns=["不知道负责人是否看过方案。"],
        actions_already_taken=["方案已经提交"],
        observable_responses=["对方两周没有回复"],
    )


class StubProvider:
    def generate(self, _request):
        return complete_output()


def test_process_returns_only_user_grounded_context() -> None:
    response = process_sites_guided_intake_v1_request(request_payload(), provider=StubProvider())

    assert response["status"] == "COMPLETE"
    assert response["next_question"] is None
    assert response["confirmed_facts"] == ["我们已经沟通过两次。"]
    assert response["unknowns"] == ["不知道负责人是否看过方案。"]
    assert response["actions_already_taken"] == ["方案已经提交"]
    assert response["observable_responses"] == ["对方两周没有回复"]
    assert response["structured_intake"]["question_domain"] == "PROJECT_COOPERATION"
    assert "不参与" in response["boundary_note"]


def test_ungrounded_complete_output_is_forced_back_to_one_question() -> None:
    output = complete_output().model_copy(
        update={"confirmed_facts": ["不存在的事实"], "unknowns": ["不存在的未知"]}
    )

    class UngroundedProvider:
        def generate(self, _request):
            return output

    response = process_sites_guided_intake_v1_request(request_payload(), provider=UngroundedProvider())

    assert response["status"] == "ASK"
    assert response["next_question"] == "还有哪一部分是你尚未确认、不能先当作事实的？"
    assert response["confirmed_facts"] == []


def test_six_grounded_answers_complete_even_if_provider_keeps_asking() -> None:
    payload = request_payload()
    payload["turns"] = [
        *payload["turns"],
        {"question": "你已经做过什么？", "answer": "我已经发过两次邮件。"},
        {"question": "对方有什么回应？", "answer": "对方仍然没有回复。"},
        {"question": "你最想确认什么？", "answer": "我想确认是否值得继续等待。"},
    ]
    output = complete_output().model_copy(
        update={
            "is_complete": False,
            "next_question": "还有什么细节？",
            "confirmed_facts": ["我们已经沟通过两次。"],
            "unknowns": ["不知道负责人是否看过方案。"],
        }
    )

    class AskingProvider:
        def generate(self, _request):
            return output

    response = process_sites_guided_intake_v1_request(payload, provider=AskingProvider())

    assert response["status"] == "COMPLETE"
    assert response["next_question"] is None


def test_non_question_suggestion_falls_back_to_original_question() -> None:
    output = complete_output().model_copy(
        update={
            "suggested_question": "向单位核实该岗位的预计期限、阶段目标，以及短期任务结束后的岗位或转岗安排。",
            "question_change_reason": "这是一份行动清单，不是问句。",
        }
    )

    class InvalidSuggestionProvider:
        def generate(self, _request):
            return output

    response = process_sites_guided_intake_v1_request(
        request_payload(),
        provider=InvalidSuggestionProvider(),
    )

    assert response["suggested_question"] == request_payload()["question_text"]
    assert response["question_change_reason"] == ""


@pytest.mark.parametrize(
    "question",
    [
        "这次合作中，我下一步最该核实什么，再决定是否继续投入？",
        "我是否值得继续等待对方的回复？",
        "这份工作还要不要继续争取？",
    ],
)
def test_interrogative_suggestions_are_preserved(question: str) -> None:
    output = complete_output().model_copy(update={"suggested_question": question})

    class QuestionProvider:
        def generate(self, _request):
            return output

    response = process_sites_guided_intake_v1_request(
        request_payload(),
        provider=QuestionProvider(),
    )

    assert response["suggested_question"] == question


def test_provider_uses_stateless_structured_responses(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls: dict[str, object] = {}

    class Responses:
        def parse(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(output_parsed=complete_output())

    class Client:
        responses = Responses()

    provider = OpenAIGuidedIntakeProvider(client_factory=lambda **_kwargs: Client())
    result = provider.generate(
        __import__(
            "abalo_iching.application.sites_guided_intake_v1",
            fromlist=["GuidedIntakeRequest"],
        ).GuidedIntakeRequest.model_validate(request_payload())
    )

    assert result.is_complete is True
    assert calls["text_format"] is GuidedIntakeModelOutput
    assert calls["store"] is False
    assert calls["tools"] == []
    assert calls["reasoning"] == {"effort": "low"}
    assert "numbers" not in str(calls["input"])


@pytest.mark.parametrize(
    "patch",
    [
        {"session_id": "bad id"},
        {"question_text": "太短"},
        {"turns": [{"question": "问", "answer": "答"}] * 9},
    ],
)
def test_invalid_requests_are_rejected(patch: dict[str, object]) -> None:
    payload = {**request_payload(), **patch}
    with pytest.raises(ValueError, match="invalid guided intake request"):
        process_sites_guided_intake_v1_request(payload, provider=StubProvider())
