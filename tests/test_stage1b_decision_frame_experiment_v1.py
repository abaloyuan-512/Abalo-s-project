from __future__ import annotations

from types import SimpleNamespace

import pytest

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    BottleneckHypothesis,
    Confirmation,
    EvidenceRef,
    GenerationMetrics,
    QuestionCandidate,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    CONTRACT_VERSION,
    SYSTEM_INSTRUCTIONS,
    AgencyAndAuthority,
    DecisionAxis,
    DecisionFrame,
    GroundedFrameValue,
    HighestValueUnknown,
    MotiveAndFearedCost,
    OpenAIStage1BProvider,
    Stage1BExperimentError,
    Stage1BExperimentRequest,
    Stage1BGenerationEnvelope,
    Stage1BModelOutput,
    StatedPremise,
    process_stage1b_experiment_request,
)


def frozen_turns() -> list[dict[str, str]]:
    return [
        {
            "question": "背景补充一",
            "answer": "项目已有初步方案，但我还没分清自己担心的是立即启动，还是公开启动。",
            "kind": "FROZEN_CONTEXT",
        }
    ]


def payload(turns=None):
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "stage1b-test",
        "question_text": "未来三个月，我是否适合立即公开启动这个项目？",
        "turns": frozen_turns() if turns is None else turns,
        "locale": "zh-CN",
    }


def unknown() -> GroundedFrameValue:
    return GroundedFrameValue(status="UNKNOWN", value=None, evidence_refs=[])


def grounded(value: str, quote: str) -> GroundedFrameValue:
    return GroundedFrameValue(
        status="GROUNDED",
        value=value,
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=0, quote=quote)],
    )


def frame(*, with_unknown: bool) -> DecisionFrame:
    gap = None
    if with_unknown:
        gap = HighestValueUnknown(
            dimension="DECISION_AXIS",
            missing_information="立即启动和公开启动中，哪一个才是真正的顾虑",
            why_it_changes_question_definition="答案会决定卜题是在判断启动时机，还是判断公开承诺风险。",
            question="你现在更担心的是立即启动准备仓促，还是公开启动带来的外部承诺风险？",
            evidence_refs=[
                EvidenceRef(
                    source="TURN_ANSWER",
                    turn_index=0,
                    quote="还没分清自己担心的是立即启动，还是公开启动",
                )
            ],
        )
    axis_evidence = [EvidenceRef(source="QUESTION_TEXT", quote="立即公开启动这个项目")]
    if not with_unknown:
        axis_evidence.append(
            EvidenceRef(
                source="TURN_ANSWER",
                turn_index=1,
                quote="更担心公开启动形成承诺",
            )
        )
    return DecisionFrame(
        decision_axes=[
            DecisionAxis(
                name="启动时机与公开方式",
                option_a="立即但不公开试运行",
                option_b="公开启动",
                status="AMBIGUOUS" if with_unknown else "GROUNDED",
                evidence_refs=axis_evidence,
            )
        ],
        stated_premises=[
            StatedPremise(
                statement="判断时间范围是未来三个月",
                treatment="RESPECT_AS_STATED",
                evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="未来三个月")],
            )
        ],
        agency_and_authority=AgencyAndAuthority(
            initiator=unknown(),
            authorizer=unknown(),
            decision_owner=unknown(),
            action_owner=unknown(),
        ),
        motive_and_feared_cost=MotiveAndFearedCost(
            desired_outcome=unknown(),
            feared_cost=grounded("担心启动或公开的风险", "担心的是立即启动，还是公开启动"),
        ),
        highest_value_unknown=gap,
    )


def hypothesis(turn_index: int, quote: str) -> BottleneckHypothesis:
    return BottleneckHypothesis(
        statement="你卡在立即试运行和公开承诺两个不同选择上，需要先判断公开风险是否可承担。",
        why_decision_is_stuck="启动时间与公开方式被合并成一个问题，导致无法判断真正要卜的选择。",
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
        uncertainty_note="这是等待你确认或纠正的理解。",
    )


class StubProvider:
    def __init__(self, output: Stage1BModelOutput):
        self.output = output

    def generate(self, _request):
        return Stage1BGenerationEnvelope(
            output=self.output,
            metrics=GenerationMetrics(model="stub", input_tokens=10, output_tokens=10, total_tokens=20, latency_ms=1),
        )


def ask_output() -> Stage1BModelOutput:
    f = frame(with_unknown=True)
    assert f.highest_value_unknown is not None
    return Stage1BModelOutput(
        status="ASK_CRITICAL",
        assistant_message="我需要先分清两个被合在一起的选择。",
        next_question=f.highest_value_unknown.question,
        frame=f,
        hypothesis=None,
        confirmation=Confirmation(state="NOT_REQUESTED"),
        candidates=[],
    )


def candidate(turn_index: int, quote: str) -> QuestionCandidate:
    return QuestionCandidate(
        question="未来三个月，我是否适合在不公开承诺的情况下立即小范围试运行这个项目？",
        focus_type="CORE_DECISION",
        what_it_tests="检验立即行动是否必须与公开承诺绑定。",
        why_this_question="它拆开启动时机和公开方式，避免把两个选择混成一个。",
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
    )


def test_ask_critical_allows_exactly_one_grounded_question() -> None:
    response = process_stage1b_experiment_request(payload(), provider=StubProvider(ask_output()))
    assert response["status"] == "ASK_CRITICAL"
    assert response["hypothesis"] is None


def test_second_critical_question_is_forbidden() -> None:
    turns = frozen_turns() + [
        {
            "question": ask_output().next_question,
            "answer": "我更担心公开承诺。",
            "kind": "CRITICAL_ANSWER",
        }
    ]
    with pytest.raises(Stage1BExperimentError, match="second critical"):
        process_stage1b_experiment_request(payload(turns), provider=StubProvider(ask_output()))


def test_non_grounded_frame_value_cannot_invent_content() -> None:
    output = ask_output().model_copy(deep=True)
    output.frame.agency_and_authority.authorizer.value = "领导"
    with pytest.raises(Stage1BExperimentError, match="cannot invent"):
        process_stage1b_experiment_request(payload(), provider=StubProvider(output))


def test_confirm_requires_resolved_frame_and_invites_correction() -> None:
    turns = frozen_turns() + [
        {
            "question": ask_output().next_question,
            "answer": "我更担心公开启动形成承诺。",
            "kind": "CRITICAL_ANSWER",
        }
    ]
    output = Stage1BModelOutput(
        status="CONFIRM",
        assistant_message="这是我的理解，请你确认。",
        next_question="我的理解是你卡在公开承诺风险，而不是启动时间。这个理解准确吗？如果不对，请纠正。",
        frame=frame(with_unknown=False),
        hypothesis=hypothesis(1, "更担心公开启动形成承诺"),
        confirmation=Confirmation(state="AWAITING"),
        candidates=[],
    )
    response = process_stage1b_experiment_request(payload(turns), provider=StubProvider(output))
    assert response["status"] == "CONFIRM"


def test_complete_requires_latest_confirmation_turn() -> None:
    turns = frozen_turns() + [
        {
            "question": ask_output().next_question,
            "answer": "我更担心公开启动形成承诺。",
            "kind": "CRITICAL_ANSWER",
        }
    ]
    output = Stage1BModelOutput(
        status="COMPLETE",
        assistant_message="已完成。",
        next_question=None,
        frame=frame(with_unknown=False),
        hypothesis=hypothesis(1, "更担心公开启动形成承诺"),
        confirmation=Confirmation(state="CONFIRMED", user_quote="对，就是这个意思。"),
        candidates=[candidate(1, "更担心公开启动形成承诺")],
    )
    with pytest.raises(Stage1BExperimentError, match="confirmation turn"):
        process_stage1b_experiment_request(payload(turns), provider=StubProvider(output))


def test_complete_after_confirmation_returns_at_most_two_candidates() -> None:
    turns = frozen_turns() + [
        {
            "question": ask_output().next_question,
            "answer": "我更担心公开启动形成承诺。",
            "kind": "CRITICAL_ANSWER",
        },
        {
            "question": "我的理解是你卡在公开承诺风险。准确吗？如果不对，请纠正。",
            "answer": "对，就是这个意思。",
            "kind": "CONFIRMATION",
        },
    ]
    output = Stage1BModelOutput(
        status="COMPLETE",
        assistant_message="确认后给出一个问题。",
        next_question=None,
        frame=frame(with_unknown=False),
        hypothesis=hypothesis(1, "更担心公开启动形成承诺"),
        confirmation=Confirmation(state="CONFIRMED", user_quote="对，就是这个意思。"),
        candidates=[candidate(1, "更担心公开启动形成承诺")],
    )
    response = process_stage1b_experiment_request(payload(turns), provider=StubProvider(output))
    assert response["status"] == "COMPLETE"
    assert len(response["candidates"]) == 1


def test_prompt_is_generic_and_locks_scope() -> None:
    assert "五项是内部判断门，不是五问问卷" in SYSTEM_INSTRUCTIONS
    assert "全流程最多新增一个 ASK_CRITICAL" in SYSTEM_INSTRUCTIONS
    assert "不占卜、不解卦、不排盘" in SYSTEM_INSTRUCTIONS
    for case_id in ("GXID-M01", "GXID-M02", "GXID-M03", "GXID-M04", "GXID-H07", "GXID-H08"):
        assert case_id not in SYSTEM_INSTRUCTIONS


def test_openai_provider_uses_structured_stateless_call(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = {}

    class Responses:
        def parse(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                output_parsed=ask_output(),
                usage=SimpleNamespace(input_tokens=10, output_tokens=10, total_tokens=20),
            )

    class Client:
        responses = Responses()

    provider = OpenAIStage1BProvider(client_factory=lambda **_kwargs: Client())
    result = provider.generate(Stage1BExperimentRequest.model_validate(payload()))
    assert result.output.status == "ASK_CRITICAL"
    assert calls["text_format"] is Stage1BModelOutput
    assert calls["store"] is False
    assert calls["tools"] == []
