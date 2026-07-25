from __future__ import annotations

from types import SimpleNamespace

import pytest

from abalo_iching.application.sites_guided_intake_v1 import (
    CONTRACT_VERSION,
    GuidedIntakeModelOutput,
    OpenAIGuidedIntakeProvider,
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
