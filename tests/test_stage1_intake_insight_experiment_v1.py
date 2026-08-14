from __future__ import annotations

from types import SimpleNamespace

import pytest

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    CONTRACT_VERSION,
    SYSTEM_INSTRUCTIONS,
    BottleneckHypothesis,
    Confirmation,
    EvidenceRef,
    GenerationEnvelope,
    GenerationMetrics,
    OpenAIStage1Provider,
    QuestionCandidate,
    Stage1ExperimentError,
    Stage1ExperimentRequest,
    Stage1ModelOutput,
    process_stage1_experiment_request,
)


def base_turns() -> list[dict[str, str]]:
    return [
        {
            "question": "你现在最顾虑什么？",
            "answer": "项目有正面反馈，但合作人的投入和第一轮交付资源还没确认。",
        },
        {
            "question": "我先理解为：机会已经出现，但你担心公开承诺超过现有承接能力。这个理解对吗？如果不对，请纠正。",
            "answer": "对，真正卡住的是正面反馈还不足以证明现在适合公开启动。",
        },
    ]


def request_payload(*, turns: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "stage1-case-001",
        "question_text": "未来三个月，我是否适合公开启动这个项目？",
        "turns": base_turns() if turns is None else turns,
        "locale": "zh-CN",
    }


def grounded_hypothesis(*, corrected: bool = False, turn_index: int = 1) -> BottleneckHypothesis:
    quote = (
        "真正卡住的是正面反馈还不足以证明现在适合公开启动"
        if not corrected
        else "更准确地说，我真正卡住的是要不要在资源没有落实前承担公开承诺"
    )
    return BottleneckHypothesis(
        statement="你真正卡住的是机会信号已经出现，但它是否足以支撑现在承担公开承诺。",
        why_decision_is_stuck="正面反馈与尚未落实的承接能力指向了不同方向。",
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
        uncertainty_note="这是对你当前纠结的理解，不是替你作出的决定。",
    )


def candidates(*, evidence_quote: str, turn_index: int = 1) -> list[QuestionCandidate]:
    evidence = [EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=evidence_quote)]
    return [
        QuestionCandidate(
            question="未来三个月，我是否适合在承接能力尚未验证时公开启动这个项目？",
            focus_type="CORE_DECISION",
            what_it_tests="现在公开启动是否与可承担的承诺相匹配。",
            why_this_question="它保留原始选择，同时把真正造成犹豫的承接风险放入判断。",
            evidence_refs=evidence,
        ),
        QuestionCandidate(
            question="未来三个月，机会信号与资源未落实之间的拉扯，哪一项更应影响我是否公开启动？",
            focus_type="BLOCKING_TENSION",
            what_it_tests="机会信号和承接风险中哪一个是当前主导矛盾。",
            why_this_question="它检验导致无法决定的两股相反力量，而不是重复条件清单。",
            evidence_refs=evidence,
        ),
    ]


def complete_output() -> Stage1ModelOutput:
    user_quote = "对，真正卡住的是正面反馈还不足以证明现在适合公开启动。"
    evidence_quote = "真正卡住的是正面反馈还不足以证明现在适合公开启动"
    return Stage1ModelOutput(
        status="COMPLETE",
        assistant_message="你的纠结已经说清楚了。下面两种问法分别检验核心选择和关键拉扯。",
        next_question=None,
        hypothesis=grounded_hypothesis(),
        confirmation=Confirmation(state="CONFIRMED", user_quote=user_quote),
        unconfirmed_assumptions=[],
        candidates=candidates(evidence_quote=evidence_quote),
    )


class StubProvider:
    def __init__(self, output: Stage1ModelOutput) -> None:
        self.output = output

    def generate(self, _request: Stage1ExperimentRequest) -> GenerationEnvelope:
        return GenerationEnvelope(
            output=self.output,
            metrics=GenerationMetrics(model="stub", input_tokens=100, output_tokens=50, total_tokens=150, latency_ms=5),
        )


def test_complete_requires_prior_confirmation_turn_and_returns_at_most_two_candidates() -> None:
    response = process_stage1_experiment_request(request_payload(), provider=StubProvider(complete_output()))

    assert response["status"] == "COMPLETE"
    assert response["confirmation"]["state"] == "CONFIRMED"
    assert len(response["candidates"]) == 2
    assert {item["focus_type"] for item in response["candidates"]} == {
        "CORE_DECISION",
        "BLOCKING_TENSION",
    }


def test_confirm_state_requires_correction_invitation_and_forbids_candidates() -> None:
    output = Stage1ModelOutput(
        status="CONFIRM",
        assistant_message="我先提出一个可能不准确的理解。",
        next_question="我先理解为你卡在机会与承接能力的拉扯。这个理解对吗？如果不对，请纠正。",
        hypothesis=BottleneckHypothesis(
            statement="你卡在机会信号与承接能力不足之间。",
            why_decision_is_stuck="两类信息指向了相反行动。",
            evidence_refs=[
                EvidenceRef(
                    source="TURN_ANSWER",
                    turn_index=0,
                    quote="合作人的投入和第一轮交付资源还没确认",
                )
            ],
            uncertainty_note="需要你确认这个理解是否准确。",
        ),
        confirmation=Confirmation(state="AWAITING"),
        unconfirmed_assumptions=["正面反馈是否足以支撑公开启动"],
        candidates=[],
    )
    response = process_stage1_experiment_request(
        request_payload(turns=base_turns()[:1]),
        provider=StubProvider(output),
    )
    assert response["status"] == "CONFIRM"
    assert response["candidates"] == []


def test_model_cannot_complete_without_a_prior_confirmation_question() -> None:
    turns = [
        {
            "question": "你现在最顾虑什么？",
            "answer": "对，真正卡住的是正面反馈还不足以证明现在适合公开启动。",
        }
    ]
    with pytest.raises(Stage1ExperimentError, match="prior confirmation question"):
        process_stage1_experiment_request(
            request_payload(turns=turns),
            provider=StubProvider(complete_output()),
        )


def test_evidence_must_match_the_declared_turn_not_the_global_transcript() -> None:
    output = complete_output().model_copy(deep=True)
    assert output.hypothesis is not None
    output.hypothesis.evidence_refs[0] = EvidenceRef(
        source="TURN_ANSWER",
        turn_index=0,
        quote="真正卡住的是正面反馈还不足以证明现在适合公开启动",
    )
    with pytest.raises(Stage1ExperimentError, match="declared source"):
        process_stage1_experiment_request(request_payload(), provider=StubProvider(output))


def test_two_candidates_must_have_different_focus_types() -> None:
    output = complete_output().model_copy(deep=True)
    output.candidates[1].focus_type = "CORE_DECISION"
    with pytest.raises(Stage1ExperimentError, match="different decision focuses"):
        process_stage1_experiment_request(request_payload(), provider=StubProvider(output))


def test_natural_either_or_question_is_accepted() -> None:
    output = complete_output().model_copy(deep=True)
    output.candidates[1].question = "我现在更应该先等责任和资源明确，还是先推动一个小范围里程碑？"

    response = process_stage1_experiment_request(request_payload(), provider=StubProvider(output))

    assert response["status"] == "COMPLETE"


@pytest.mark.parametrize(
    ("correction_answer", "evidence_quote"),
    [
        (
            "这个理解不对。更准确地说，我真正卡住的是要不要在资源没有落实前承担公开承诺。",
            "更准确地说，我真正卡住的是要不要在资源没有落实前承担公开承诺",
        ),
        (
            "不是这个意思。我真正纠结的是合作人不确定时，正面反馈还值不值得相信。",
            "我真正纠结的是合作人不确定时，正面反馈还值不值得相信",
        ),
    ],
)
def test_two_explicit_correction_paths_rebuild_and_cite_latest_user_answer(
    correction_answer: str,
    evidence_quote: str,
) -> None:
    turns = [
        base_turns()[0],
        {
            "question": "我先理解为你只是担心进度太慢。这个理解对吗？如果不对，请纠正。",
            "answer": correction_answer,
        },
    ]
    hypothesis = BottleneckHypothesis(
        statement="纠正后，瓶颈不再是进度，而是机会信号是否足以覆盖承接风险。",
        why_decision_is_stuck="用户明确否认旧理解，并指出了新的核心拉扯。",
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=1, quote=evidence_quote)],
        uncertainty_note="该瓶颈已经按用户纠正重建。",
    )
    output = Stage1ModelOutput(
        status="COMPLETE",
        assistant_message="我已按你的纠正重建问题，不再沿用进度假设。",
        next_question=None,
        hypothesis=hypothesis,
        confirmation=Confirmation(
            state="CORRECTED",
            user_quote=correction_answer,
            corrected_statement=hypothesis.statement,
        ),
        unconfirmed_assumptions=[],
        candidates=candidates(evidence_quote=evidence_quote),
    )
    response = process_stage1_experiment_request(
        request_payload(turns=turns),
        provider=StubProvider(output),
    )
    assert response["confirmation"]["state"] == "CORRECTED"
    assert response["hypothesis"]["evidence_refs"][0]["turn_index"] == 1
    assert "进度太慢" not in response["hypothesis"]["statement"]


def test_prompt_enforces_confirmation_and_stage_boundaries() -> None:
    assert "无论轮数多少都不得自动完成" in SYSTEM_INSTRUCTIONS
    assert "用户否认后不得维护旧假设" in SYSTEM_INSTRUCTIONS
    assert "不占卜、不解卦、不索取起卦数字" in SYSTEM_INSTRUCTIONS
    assert "不要为了数量强凑两个" in SYSTEM_INSTRUCTIONS
    assert "unconfirmed_assumptions 必须是 []" in SYSTEM_INSTRUCTIONS
    assert "turn_index 一律从 0 开始" in SYSTEM_INSTRUCTIONS


def test_openai_provider_uses_stateless_structured_output(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls: dict[str, object] = {}

    class Responses:
        def parse(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                output_parsed=complete_output(),
                usage=SimpleNamespace(input_tokens=100, output_tokens=50, total_tokens=150),
            )

    class Client:
        responses = Responses()

    provider = OpenAIStage1Provider(client_factory=lambda **_kwargs: Client())
    result = provider.generate(Stage1ExperimentRequest.model_validate(request_payload()))

    assert result.output.status == "COMPLETE"
    assert calls["text_format"] is Stage1ModelOutput
    assert calls["reasoning"] == {"effort": "medium"}
    assert calls["store"] is False
    assert calls["tools"] == []
    assert "不得自动完成" in str(calls["input"])
