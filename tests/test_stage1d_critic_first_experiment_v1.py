from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from evals.meihua.intelligence_optimization_stage1_v001.experiment.intake_insight_experiment_v1 import (
    BottleneckHypothesis,
    EvidenceRef,
    GenerationMetrics,
)
from evals.meihua.intelligence_optimization_stage1b_v001.experiment.decision_frame_experiment_v1 import (
    DecisionAxis,
    StatedPremise,
)
from evals.meihua.intelligence_optimization_stage1d_v001.experiment.critic_first_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_INSTRUCTIONS,
    CRITIC_PROMPT_SHA256,
    PROPOSER_INSTRUCTIONS,
    PROPOSER_PROMPT_SHA256,
    AgencyAndAuthority,
    AskOneReview,
    CriticAttempt,
    CriticOutput,
    DecisionFrame,
    FrameProposal,
    GroundedValue,
    ModelCallRecord,
    MotiveAndFearedCost,
    NotRelevantValue,
    OpenAICritic,
    OpenAIProposer,
    ProposerAttempt,
    ReadyReview,
    Stage1DRequest,
    UnknownValue,
    arbitrate_stage1d_request,
)
from evals.meihua.intelligence_optimization_stage1d_v001.experiment import (
    run_stage1d_experiment as stage1d_runner,
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
                "question": "你需要判断立即开始，还是公开承诺？",
                "answer": "我担心的是公开后形成承诺，不是立即开始。",
                "kind": "CRITICAL_ANSWER",
            }
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "GXID-TEST-SECRET",
        "question_text": "未来三个月，我是否适合立即公开启动这个项目？",
        "turns": turns,
        "locale": "zh-CN",
    }


def grounded(value: str, quote: str, *, turn_index: int | None = None):
    return GroundedValue(
        status="GROUNDED",
        value=value,
        evidence_refs=[
            EvidenceRef(
                source="QUESTION_TEXT" if turn_index is None else "TURN_ANSWER",
                turn_index=turn_index,
                quote=quote,
            )
        ],
    )


def proposal(*, cite_critical: bool = False):
    turn_index = 1 if cite_critical else 0
    quote = (
        "担心的是公开后形成承诺，不是立即开始"
        if cite_critical
        else "立即开始，还是公开后的承诺"
    )
    refs = [EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)]
    return FrameProposal(
        frame=DecisionFrame(
            decision_axes=[
                DecisionAxis(
                    name="公开启动的承诺风险",
                    option_a="立即但不公开开始",
                    option_b="公开启动",
                    status="GROUNDED",
                    evidence_refs=refs,
                )
            ],
            stated_premises=[
                StatedPremise(
                    statement="判断窗口为未来三个月",
                    treatment="RESPECT_AS_STATED",
                    evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="未来三个月")],
                )
            ],
            agency_and_authority=AgencyAndAuthority(
                initiator=UnknownValue(status="UNKNOWN"),
                authorizer=NotRelevantValue(status="NOT_RELEVANT"),
                decision_owner=UnknownValue(status="UNKNOWN"),
                action_owner=UnknownValue(status="UNKNOWN"),
            ),
            motive_and_feared_cost=MotiveAndFearedCost(
                desired_outcome=grounded("判断公开承诺风险", quote, turn_index=turn_index),
                feared_cost=UnknownValue(status="UNKNOWN"),
            ),
        ),
        candidate_hypothesis=BottleneckHypothesis(
            statement="真正卡住决定的是公开启动会形成尚无把握承担的对外承诺。",
            why_decision_is_stuck="立即开始与公开承诺曾被合并为一个问题。",
            evidence_refs=refs,
            uncertainty_note="请用户确认这一候选理解。",
        ),
        proposal_note="Critic已放行，只形成一个候选瓶颈。",
    )


def ask_review():
    return AskOneReview(
        verdict="ASK_ONE",
        dimension="DECISION_AXIS",
        definition_a="判断是否立即开始项目",
        definition_b="判断是否承担公开启动后的承诺",
        why_answers_create_different_questions="两种答案分别形成启动时机和公开承诺风险两个不同卜题。",
        question="你需要判断的是是否立即开始，还是是否承担公开启动后的承诺？",
        evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="立即公开启动")],
    )


def ready_review(*, cite_critical: bool = False):
    turn_index = 1 if cite_critical else 0
    quote = (
        "担心的是公开后形成承诺，不是立即开始"
        if cite_critical
        else "立即开始，还是公开后的承诺"
    )
    return ReadyReview(
        verdict="READY",
        resolved_problem_definition="判断是否承担公开启动形成的对外承诺。",
        ready_reason="用户已经把启动时机和公开承诺区分开。",
        non_blocking_unknowns=[],
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
    )


def record(sequence: int, role: str, output):
    return ModelCallRecord(
        sequence=sequence,
        role=role,
        model=f"stub-{role.lower()}",
        prompt_sha256=(CRITIC_PROMPT_SHA256 if role == "CRITIC" else PROPOSER_PROMPT_SHA256),
        latency_ms=1,
        raw_output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
        raw_parsed_output=output.model_dump(mode="json"),
        usage=GenerationMetrics(
            model=f"stub-{role.lower()}",
            input_tokens=6,
            output_tokens=4,
            total_tokens=10,
            latency_ms=1,
        ),
        outcome="SUCCESS",
    )


class StubCritic:
    def __init__(self, decision, calls):
        self.decision = decision
        self.calls = calls

    def generate(self, _request, *, call_sequence):
        self.calls.append(("CRITIC", call_sequence))
        output = CriticOutput(decision=self.decision)
        return CriticAttempt(output=output, record=record(call_sequence, "CRITIC", output))


class StubProposer:
    def __init__(self, output, calls):
        self.output = output
        self.calls = calls

    def generate(self, _request, *, call_sequence):
        self.calls.append(("PROPOSER", call_sequence))
        return ProposerAttempt(
            output=self.output,
            record=record(call_sequence, "PROPOSER", self.output),
        )


def test_frame_value_union_rejects_unknown_or_not_relevant_content():
    with pytest.raises(ValidationError):
        AgencyAndAuthority.model_validate(
            {
                "initiator": {"status": "UNKNOWN", "value": "invented"},
                "authorizer": {"status": "UNKNOWN"},
                "decision_owner": {"status": "UNKNOWN"},
                "action_owner": {"status": "UNKNOWN"},
            }
        )
    with pytest.raises(ValidationError):
        AgencyAndAuthority.model_validate(
            {
                "initiator": {"status": "NOT_RELEVANT", "evidence_refs": []},
                "authorizer": {"status": "UNKNOWN"},
                "decision_owner": {"status": "UNKNOWN"},
                "action_owner": {"status": "UNKNOWN"},
            }
        )


def test_frame_value_union_requires_grounded_content_and_evidence():
    with pytest.raises(ValidationError):
        GroundedValue.model_validate({"status": "GROUNDED", "value": "x", "evidence_refs": []})
    assert UnknownValue.model_json_schema()["additionalProperties"] is False


def test_review_union_forbids_cross_verdict_fields():
    with pytest.raises(ValidationError):
        CriticOutput.model_validate(
            {
                "decision": {
                    "verdict": "READY",
                    "resolved_problem_definition": "已经明确判断公开承诺风险",
                    "ready_reason": "两个定义已经收束为一个",
                    "non_blocking_unknowns": [],
                    "question": "还要问吗？",
                    "evidence_refs": [{"source": "QUESTION_TEXT", "quote": "立即公开启动"}],
                }
            }
        )


def test_initial_ask_calls_only_critic_and_hides_hypothesis():
    calls = []
    response = arbitrate_stage1d_request(
        payload(),
        critic=StubCritic(ask_review(), calls),
        proposer=StubProposer(proposal(), calls),
    )
    assert response["status"] == "ASK_CRITICAL"
    assert response["hypothesis"] is None
    assert calls == [("CRITIC", 1)]
    assert len(response["call_records"]) == 1


def test_initial_ready_calls_critic_then_proposer():
    calls = []
    response = arbitrate_stage1d_request(
        payload(),
        critic=StubCritic(ready_review(), calls),
        proposer=StubProposer(proposal(), calls),
    )
    assert response["status"] == "CONFIRM"
    assert calls == [("CRITIC", 1), ("PROPOSER", 2)]
    assert len(response["call_records"]) == 2


def test_second_ask_stops_without_exposing_question_or_calling_proposer():
    calls = []
    response = arbitrate_stage1d_request(
        payload(with_critical=True),
        call_sequence_start=7,
        critic=StubCritic(ask_review(), calls),
        proposer=StubProposer(proposal(cite_critical=True), calls),
    )
    assert response["status"] == "INSUFFICIENT_TO_CONFIRM"
    assert response["next_question"] is None
    assert calls == [("CRITIC", 7)]


def test_after_critical_ready_requires_critic_and_proposer_to_cite_answer():
    calls = []
    bad = arbitrate_stage1d_request(
        payload(with_critical=True),
        critic=StubCritic(ready_review(cite_critical=False), calls),
        proposer=StubProposer(proposal(cite_critical=True), calls),
    )
    assert bad["status"] == "REVIEW_ERROR"
    assert bad["call_records"][0]["outcome"] == "SEMANTIC_VALIDATION_ERROR"
    assert calls == [("CRITIC", 1)]

    calls = []
    good = arbitrate_stage1d_request(
        payload(with_critical=True),
        critic=StubCritic(ready_review(cite_critical=True), calls),
        proposer=StubProposer(proposal(cite_critical=True), calls),
    )
    assert good["status"] == "CONFIRM"
    assert calls == [("CRITIC", 1), ("PROPOSER", 2)]


def test_semantic_failure_preserves_raw_output_usage_and_latency():
    calls = []
    invalid = ask_review().model_copy(update={"question": "这个问题没有问号"})
    response = arbitrate_stage1d_request(
        payload(),
        critic=StubCritic(invalid, calls),
        proposer=StubProposer(proposal(), calls),
    )
    call = response["call_records"][0]
    assert response["status"] == "REVIEW_ERROR"
    assert call["raw_parsed_output"] is not None
    assert call["usage"]["total_tokens"] == 10
    assert call["latency_ms"] == 1
    assert call["outcome"] == "SEMANTIC_VALIDATION_ERROR"


def test_provider_failure_is_a_first_class_call_record(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class BrokenResponses:
        def create(self, **_kwargs):
            raise RuntimeError("network unavailable")

    provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=BrokenResponses())
    )
    attempt = provider.generate(Stage1DRequest.model_validate(payload()), call_sequence=9)
    assert attempt.output is None
    assert attempt.record.sequence == 9
    assert attempt.record.outcome == "TRANSPORT_ERROR"
    assert "network unavailable" in attempt.record.error_detail


def test_critic_input_contains_no_case_id_or_proposer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            output = CriticOutput(decision=ask_review())
            return SimpleNamespace(
                id="resp-1",
                output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    )
    provider.generate(Stage1DRequest.model_validate(payload()), call_sequence=1)
    body = captured["input"][1]["content"]
    assert "GXID-TEST-SECRET" not in body
    assert "proposal" not in body.lower()
    parsed_body = json.loads(body)
    assert parsed_body["answers"][0]["context_question"] == "背景补充"
    assert captured["input"][0]["content"] == CRITIC_INSTRUCTIONS
    assert captured["store"] is False
    assert captured["text"]["format"]["strict"] is True


def test_critical_round_input_contains_the_prior_single_question(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            output = CriticOutput(decision=ready_review(cite_critical=True))
            return SimpleNamespace(
                id="resp-critical",
                output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    )
    provider.generate(Stage1DRequest.model_validate(payload(with_critical=True)), call_sequence=2)
    body = json.loads(captured["input"][1]["content"])
    critical = body["answers"][1]
    assert critical["turn_kind"] == "CRITICAL_ANSWER"
    assert critical["context_question"] == "你需要判断立即开始，还是公开承诺？"
    assert "GXID-TEST-SECRET" not in captured["input"][1]["content"]


def test_http_success_schema_failure_preserves_raw_usage_and_validation_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    invalid = {
        "decision": {
            "verdict": "READY",
            "resolved_problem_definition": "判断公开启动后的承诺风险",
            "ready_reason": "问题定义已经收束",
            "non_blocking_unknowns": [],
            "question": "这个字段不应存在？",
            "evidence_refs": [
                {"source": "QUESTION_TEXT", "turn_index": None, "quote": "立即公开启动"}
            ],
        }
    }

    class Responses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                id="resp-invalid",
                output_text=json.dumps(invalid, ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=11, output_tokens=7, total_tokens=18),
            )

    provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    )
    attempt = provider.generate(Stage1DRequest.model_validate(payload()), call_sequence=4)
    assert attempt.output is None
    assert attempt.record.outcome == "PARSE_OR_SCHEMA_ERROR"
    assert attempt.record.response_id == "resp-invalid"
    assert attempt.record.raw_output_text == json.dumps(invalid, ensure_ascii=False)
    assert attempt.record.raw_parsed_output == invalid
    assert attempt.record.usage.total_tokens == 18
    assert "ValidationError" in attempt.record.error_detail


def test_proposer_provider_uses_separate_prompt(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            output = proposal()
            return SimpleNamespace(
                id="resp-2",
                output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    provider = OpenAIProposer(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    )
    provider.generate(Stage1DRequest.model_validate(payload()), call_sequence=2)
    assert captured["input"][0]["content"] == PROPOSER_INSTRUCTIONS
    assert CRITIC_INSTRUCTIONS != PROPOSER_INSTRUCTIONS


def test_prompts_are_generic_and_do_not_leak_case_ids():
    for case_id in (
        "GXID-M01",
        "GXID-M02",
        "GXID-M03",
        "GXID-M04",
        "GXID-H09",
        "GXID-H10",
    ):
        assert case_id not in CRITIC_INSTRUCTIONS
        assert case_id not in PROPOSER_INSTRUCTIONS
    assert "看不到" in CRITIC_INSTRUCTIONS
    assert "不得转而寻找新的" in CRITIC_INSTRUCTIONS
    assert "不得把事实摘要冒充瓶颈" in PROPOSER_INSTRUCTIONS


def test_runner_normalizes_ready_and_veto_expectations():
    assert (
        stage1d_runner._expected_verdict({"acceptable_critic_decision": ["READY"]})
        == "READY"
    )
    assert (
        stage1d_runner._expected_verdict({"acceptable_critic_decision": ["VETO_ASK"]})
        == "ASK_ONE"
    )
    with pytest.raises(RuntimeError, match="invalid acceptable_critic_decision"):
        stage1d_runner._expected_verdict({"acceptable_critic_decision": ["REDAY"]})


def test_runner_aggregate_counts_failures_and_missing_usage():
    success = record(1, "CRITIC", CriticOutput(decision=ready_review())).model_dump(mode="json")
    failure = ModelCallRecord(
        sequence=2,
        role="PROPOSER",
        model="stub",
        prompt_sha256=PROPOSER_PROMPT_SHA256,
        latency_ms=3,
        outcome="TRANSPORT_ERROR",
        error_detail="network",
    ).model_dump(mode="json")
    aggregate = stage1d_runner._aggregate([success, failure])
    assert aggregate["attempted_call_count"] == 2
    assert aggregate["successful_call_count"] == 1
    assert aggregate["failed_call_count"] == 1
    assert aggregate["usage_missing_count"] == 1
    assert aggregate["sequence_is_contiguous"] is True


def test_runner_marker_blocks_second_run_before_any_model_call(tmp_path, monkeypatch):
    stage = tmp_path / stage1d_runner.STAGE1D_REL
    (stage / "runs").mkdir(parents=True)
    (stage / "manifest.json").write_text("{}", encoding="utf-8")
    (stage / "runs/stage1d_run_started.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(stage1d_runner, "_validate_frozen_assets", lambda *_args: None)
    monkeypatch.setattr(stage1d_runner, "_validate_dataset_assets", lambda *_args: None)
    with pytest.raises(RuntimeError, match="already been run"):
        stage1d_runner.run(tmp_path, "stub")


def test_exclusive_marker_creation_is_atomic(tmp_path):
    marker = tmp_path / "runs" / "started.json"
    stage1d_runner._write_exclusive(marker, {"run": 1})
    with pytest.raises(RuntimeError, match="already been run"):
        stage1d_runner._write_exclusive(marker, {"run": 2})
    assert json.loads(marker.read_text(encoding="utf-8")) == {"run": 1}


def test_dataset_preflight_enforces_six_balanced_and_matching_ids(tmp_path):
    stage0 = tmp_path / "stage0"
    stage1b = tmp_path / "stage1b"
    stage1d = tmp_path / "stage1d"
    (stage0 / "baselines").mkdir(parents=True)
    (stage1b / "cases").mkdir(parents=True)
    (stage1d / "cases").mkdir(parents=True)
    core_ids = list(stage1d_runner.CORE_DIMENSIONS)
    (stage0 / "guided_intake_synthetic_inputs.json").write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": case_id, "question_text": "核心问题", "answer_pool": ["a"] * 4}
                    for case_id in core_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    (stage1b / "cases/development_critical_answers.json").write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": case_id, "critical_answer": "关键回答"}
                    for case_id in core_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    heldout_ids = [f"NEW-{index}" for index in range(6)]
    (stage1d / "cases/cases.json").write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": case_id, "question_text": "保护问题", "answer_pool": ["a"] * 4}
                    for case_id in heldout_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    expectations = [
        {
            "case_id": case_id,
            "acceptable_critic_decision": ["VETO" if index < 3 else "READY"],
            "expected_dimension": "DECISION_AXIS" if index < 3 else None,
        }
        for index, case_id in enumerate(heldout_ids)
    ]
    expectations_path = stage1d / "cases/expectations.json"
    expectations_path.write_text(json.dumps({"expectations": expectations}), encoding="utf-8")
    (stage1d / "cases/answers.json").write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": case_id,
                        "critical_answer": "回答" if index < 3 else None,
                    }
                    for index, case_id in enumerate(heldout_ids)
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "heldout_cases": "cases/cases.json",
        "heldout_expectations": "cases/expectations.json",
        "heldout_critical_answers": "cases/answers.json",
    }
    stage1d_runner._validate_dataset_assets(stage0, stage1b, stage1d, manifest)

    expectations[5]["acceptable_critic_decision"] = ["UNKNOWN_LABEL"]
    expectations_path.write_text(json.dumps({"expectations": expectations}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid acceptable_critic_decision"):
        stage1d_runner._validate_dataset_assets(stage0, stage1b, stage1d, manifest)
