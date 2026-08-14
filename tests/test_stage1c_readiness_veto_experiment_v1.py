from __future__ import annotations

from types import SimpleNamespace

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    BottleneckHypothesis,
    EvidenceRef,
    GenerationMetrics,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    AgencyAndAuthority,
    DecisionAxis,
    DecisionFrame,
    GroundedFrameValue,
    MotiveAndFearedCost,
    StatedPremise,
)
from evals.meihua.intelligence_optimization_stage1c_v001.experiment.readiness_veto_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_INSTRUCTIONS,
    PROPOSER_INSTRUCTIONS,
    FrameProposal,
    OpenAICritic,
    OpenAIProposer,
    ProposalEnvelope,
    ReadinessReview,
    ReviewEnvelope,
    Stage1CRequest,
    arbitrate_stage1c_request,
)


def payload(*, with_critical: bool = False):
    turns = [
        {
            "question": "背景补充",
            "answer": "我还没有分清真正担心的是立即开始，还是公开后的承诺。",
            "kind": "FROZEN_CONTEXT",
        }
    ]
    if with_critical:
        turns.append(
            {
                "question": "你更需要判断立即开始，还是公开后的承诺风险？",
                "answer": "我担心的是公开后形成承诺，不是立即开始。",
                "kind": "CRITICAL_ANSWER",
            }
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "stage1c-test",
        "question_text": "未来三个月，我是否适合立即公开启动这个项目？",
        "turns": turns,
        "locale": "zh-CN",
    }


def unknown():
    return GroundedFrameValue(status="UNKNOWN", value=None, evidence_refs=[])


def frame(*, cite_critical: bool = False):
    refs = [EvidenceRef(source="QUESTION_TEXT", quote="立即公开启动这个项目")]
    if cite_critical:
        refs.append(
            EvidenceRef(
                source="TURN_ANSWER",
                turn_index=1,
                quote="担心的是公开后形成承诺，不是立即开始",
            )
        )
    return DecisionFrame(
        decision_axes=[
            DecisionAxis(
                name="启动时机与公开方式",
                option_a="立即但不公开开始",
                option_b="公开启动",
                status="AMBIGUOUS" if not cite_critical else "GROUNDED",
                evidence_refs=refs,
            )
        ],
        stated_premises=[
            StatedPremise(
                statement="时间范围为未来三个月",
                treatment="RESPECT_AS_STATED",
                evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="未来三个月")],
            )
        ],
        agency_and_authority=AgencyAndAuthority(
            initiator=unknown(), authorizer=unknown(), decision_owner=unknown(), action_owner=unknown()
        ),
        motive_and_feared_cost=MotiveAndFearedCost(
            desired_outcome=unknown(), feared_cost=unknown()
        ),
        highest_value_unknown=None,
    )


def proposal(*, cite_critical: bool = False):
    turn_index = 1 if cite_critical else 0
    quote = "担心的是公开后形成承诺，不是立即开始" if cite_critical else "立即开始，还是公开后的承诺"
    return FrameProposal(
        frame=frame(cite_critical=cite_critical),
        candidate_hypothesis=BottleneckHypothesis(
            statement="你真正需要判断的是公开启动后的承诺风险是否值得承担。",
            why_decision_is_stuck="启动时机与公开方式曾被合并，导致问题定义不清。",
            evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
            uncertainty_note="这是等待独立审查的候选理解。",
        ),
        proposal_note="只提交框架和候选瓶颈，不决定状态。",
    )


def veto_review():
    return ReadinessReview(
        verdict="VETO_ASK",
        critical_gap="立即开始和公开启动可能是两个不同决策轴",
        alternative_problem_definition="用户可能愿意立即开始，但只是不愿立即公开承诺。",
        definition_change_reason="答案会把卜题从启动时机改成公开承诺风险。",
        question="你更需要判断的是立即开始的时机，还是公开启动后的承诺风险？",
        ready_reason=None,
        evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="立即公开启动")],
    )


def allow_review(*, cite_critical: bool = False):
    turn_index = 1 if cite_critical else 0
    quote = "担心的是公开后形成承诺，不是立即开始" if cite_critical else "立即开始，还是公开后的承诺"
    return ReadinessReview(
        verdict="ALLOW_CONFIRM",
        critical_gap=None,
        alternative_problem_definition=None,
        definition_change_reason=None,
        question=None,
        ready_reason="没有发现仍会产生不同卜题的问题定义。",
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
    )


class StubProposer:
    def __init__(self, output):
        self.output = output

    def generate(self, _request):
        if isinstance(self.output, Exception):
            raise self.output
        return ProposalEnvelope(
            output=self.output,
            metrics=GenerationMetrics(model="proposer", total_tokens=10, latency_ms=1),
        )


class StubCritic:
    def __init__(self, output):
        self.output = output

    def generate(self, _request, _proposal):
        if isinstance(self.output, Exception):
            raise self.output
        return ReviewEnvelope(
            output=self.output,
            metrics=GenerationMetrics(model="critic", total_tokens=10, latency_ms=1),
        )


def test_veto_forces_ask_even_when_proposer_supplies_hypothesis():
    response = arbitrate_stage1c_request(
        payload(), proposer=StubProposer(proposal()), critic=StubCritic(veto_review())
    )
    assert response["status"] == "ASK_CRITICAL"
    assert response["hypothesis"] is None
    assert response["next_question"] == veto_review().question


def test_allow_is_the_only_path_to_confirm():
    response = arbitrate_stage1c_request(
        payload(), proposer=StubProposer(proposal()), critic=StubCritic(allow_review())
    )
    assert response["status"] == "CONFIRM"
    assert response["hypothesis"] is not None
    assert "如果不准确，请纠正" in response["next_question"]


def test_critic_error_fails_closed():
    response = arbitrate_stage1c_request(
        payload(), proposer=StubProposer(proposal()), critic=StubCritic(RuntimeError("boom"))
    )
    assert response["status"] == "REVIEW_ERROR"
    assert response["hypothesis"] is None


def test_second_veto_stops_without_second_question():
    response = arbitrate_stage1c_request(
        payload(with_critical=True),
        proposer=StubProposer(proposal(cite_critical=True)),
        critic=StubCritic(veto_review()),
    )
    assert response["status"] == "INSUFFICIENT_TO_CONFIRM"
    assert response["next_question"] is None


def test_after_critical_allow_requires_all_three_layers_to_cite_answer():
    response = arbitrate_stage1c_request(
        payload(with_critical=True),
        proposer=StubProposer(proposal(cite_critical=True)),
        critic=StubCritic(allow_review(cite_critical=False)),
    )
    assert response["status"] == "REVIEW_ERROR"
    assert "critical answer not cited" in response["review_error"]


def test_after_critical_allow_can_confirm_when_all_layers_cite_answer():
    response = arbitrate_stage1c_request(
        payload(with_critical=True),
        proposer=StubProposer(proposal(cite_critical=True)),
        critic=StubCritic(allow_review(cite_critical=True)),
    )
    assert response["status"] == "CONFIRM"


def test_inducing_veto_question_fails_closed():
    review = veto_review().model_copy(deep=True)
    review.question = "你是不是因为害怕公开承诺，所以才不愿启动？"
    response = arbitrate_stage1c_request(
        payload(), proposer=StubProposer(proposal()), critic=StubCritic(review)
    )
    assert response["status"] == "REVIEW_ERROR"


def test_role_prompts_are_separate_generic_and_boundary_locked():
    assert PROPOSER_INSTRUCTIONS != CRITIC_INSTRUCTIONS
    assert "不得向用户提问" in PROPOSER_INSTRUCTIONS
    assert "另一种合理的问题定义" in CRITIC_INSTRUCTIONS
    assert "不占卜" in PROPOSER_INSTRUCTIONS
    for case_id in ("GXID-M01", "GXID-M02", "GXID-M03", "GXID-M04", "GXID-H09", "GXID-H10"):
        assert case_id not in PROPOSER_INSTRUCTIONS
        assert case_id not in CRITIC_INSTRUCTIONS


def test_openai_roles_use_distinct_system_prompts(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    proposer_calls = {}
    critic_calls = {}

    class ProposerResponses:
        def parse(self, **kwargs):
            proposer_calls.update(kwargs)
            return SimpleNamespace(
                output_parsed=proposal(),
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    class CriticResponses:
        def parse(self, **kwargs):
            critic_calls.update(kwargs)
            return SimpleNamespace(
                output_parsed=veto_review(),
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    proposer_provider = OpenAIProposer(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=ProposerResponses())
    )
    critic_provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=CriticResponses())
    )
    request = Stage1CRequest.model_validate(payload())
    proposer_provider.generate(request)
    critic_provider.generate(request, proposal())

    assert proposer_calls["input"][0]["content"] == PROPOSER_INSTRUCTIONS
    assert critic_calls["input"][0]["content"] == CRITIC_INSTRUCTIONS
    assert proposer_calls["store"] is False and critic_calls["store"] is False

