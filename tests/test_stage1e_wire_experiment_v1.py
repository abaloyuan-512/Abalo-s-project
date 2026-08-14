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
from evals.meihua.intelligence_optimization_stage1e_v001.experiment.critic_first_wire_experiment_v1 import (
    CONTRACT_VERSION,
    CRITIC_INSTRUCTIONS,
    CRITIC_PROMPT_SHA256,
    CRITIC_TEXT_FORMAT,
    CRITIC_WIRE_SCHEMA_SHA256,
    PROPOSER_INSTRUCTIONS,
    PROPOSER_PROMPT_SHA256,
    PROPOSER_TEXT_FORMAT,
    PROPOSER_WIRE_SCHEMA_SHA256,
    AgencyAndAuthorityWire,
    CriticAttempt,
    CriticWireOutput,
    DecisionFrameWire,
    FrameProposalWire,
    FrameValueWire,
    ModelCallRecord,
    MotiveAndFearedCostWire,
    OpenAICritic,
    ProposerAttempt,
    Stage1EError,
    Stage1ERequest,
    _walk_schema,
    arbitrate_stage1e_request,
)
from evals.meihua.intelligence_optimization_stage1e_v001.experiment import (
    run_stage1e_canary as canary_runner,
)


def payload(*, critical: bool = False):
    turns = [
        {
            "question": "背景补充",
            "answer": "我还没分清是在决定是否开放，还是只决定开放范围。",
            "kind": "FROZEN_CONTEXT",
        }
    ]
    if critical:
        turns.append(
            {
                "question": "你还在决定是否开放，还是已经决定开放只选范围？",
                "answer": "我已经决定开放，现在只在小范围与全面开放之间选择。",
                "kind": "CRITICAL_ANSWER",
            }
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": "SECRET-CASE-ID",
        "question_text": "未来一个月，我是否适合立即全面开放新功能？",
        "turns": turns,
        "locale": "zh-CN",
    }


def ask_wire():
    return CriticWireOutput(
        verdict="ASK_ONE",
        dimension="DECISION_AXIS",
        definition_a="判断未来一个月是否开放新功能",
        definition_b="已经决定开放，只判断小范围还是全面开放",
        why_answers_create_different_questions="前者判断是否行动，后者判断已确定行动后的开放范围。",
        question="你还在决定是否开放，还是已经决定开放、只在选择开放范围？",
        resolved_problem_definition=None,
        ready_reason=None,
        non_blocking_unknowns=[],
        evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="立即全面开放")],
    )


def ready_wire(*, critical: bool = False):
    turn_index = 1 if critical else 0
    quote = (
        "已经决定开放，现在只在小范围与全面开放之间选择"
        if critical
        else "还没分清是在决定是否开放，还是只决定开放范围"
    )
    return CriticWireOutput(
        verdict="READY",
        dimension=None,
        definition_a=None,
        definition_b=None,
        why_answers_create_different_questions=None,
        question=None,
        resolved_problem_definition="已经决定开放，只判断开放范围。",
        ready_reason="行动承诺与开放范围已经明确区分。",
        non_blocking_unknowns=[],
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
    )


def unknown_wire(status="UNKNOWN"):
    return FrameValueWire(status=status, value=None, evidence_refs=[])


def grounded_wire(value: str, quote: str, *, turn_index: int):
    return FrameValueWire(
        status="GROUNDED",
        value=value,
        evidence_refs=[EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)],
    )


def proposal_wire(*, critical: bool = False):
    turn_index = 1 if critical else 0
    quote = (
        "已经决定开放，现在只在小范围与全面开放之间选择"
        if critical
        else "还没分清是在决定是否开放，还是只决定开放范围"
    )
    refs = [EvidenceRef(source="TURN_ANSWER", turn_index=turn_index, quote=quote)]
    return FrameProposalWire(
        frame=DecisionFrameWire(
            decision_axes=[
                DecisionAxis(
                    name="开放范围",
                    option_a="小范围开放",
                    option_b="全面开放",
                    status="GROUNDED",
                    evidence_refs=refs,
                )
            ],
            stated_premises=[
                StatedPremise(
                    statement="判断窗口为未来一个月",
                    treatment="RESPECT_AS_STATED",
                    evidence_refs=[EvidenceRef(source="QUESTION_TEXT", quote="未来一个月")],
                )
            ],
            agency_and_authority=AgencyAndAuthorityWire(
                initiator=unknown_wire(),
                authorizer=unknown_wire("NOT_RELEVANT"),
                decision_owner=unknown_wire(),
                action_owner=unknown_wire(),
            ),
            motive_and_feared_cost=MotiveAndFearedCostWire(
                desired_outcome=grounded_wire("选择开放范围", quote, turn_index=turn_index),
                feared_cost=unknown_wire(),
            ),
            highest_value_unknown=None,
        ),
        candidate_hypothesis=BottleneckHypothesis(
            statement="真正卡住决定的是小范围验证与全面覆盖之间的取舍。",
            why_decision_is_stuck="两个开放范围带来不同的验证速度与影响范围。",
            evidence_refs=refs,
            uncertainty_note="等待用户确认该候选理解。",
        ),
        proposal_note="只形成一个候选瓶颈。",
    )


def call_record(sequence: int, role: str, raw_model, outcome="SUCCESS"):
    prompt_sha = CRITIC_PROMPT_SHA256 if role == "CRITIC" else PROPOSER_PROMPT_SHA256
    schema_sha = (
        CRITIC_WIRE_SCHEMA_SHA256 if role == "CRITIC" else PROPOSER_WIRE_SCHEMA_SHA256
    )
    raw = raw_model.model_dump(mode="json") if raw_model else None
    return ModelCallRecord(
        sequence=sequence,
        role=role,
        attempted=True,
        model="stub",
        prompt_sha256=prompt_sha,
        schema_sha256=schema_sha,
        input_sha256="a" * 64,
        started_at="2026-08-07T00:00:00+00:00",
        finished_at="2026-08-07T00:00:00+00:00",
        latency_ms=1,
        response_id="resp",
        request_id="req",
        http_status=200,
        api_error_code=None,
        api_error_param=None,
        raw_output_text=json.dumps(raw, ensure_ascii=False) if raw else None,
        raw_parsed_output=raw,
        usage=GenerationMetrics(
            model="stub", input_tokens=5, output_tokens=5, total_tokens=10, latency_ms=1
        ),
        outcome=outcome,
        error_detail=None,
    )


class StubCritic:
    def __init__(self, output, calls):
        self.output = output
        self.calls = calls

    def generate(self, _request, *, call_sequence):
        self.calls.append(("CRITIC", call_sequence))
        return CriticAttempt(
            output=self.output,
            record=call_record(call_sequence, "CRITIC", self.output),
        )


class StubProposer:
    def __init__(self, output, calls):
        self.output = output
        self.calls = calls

    def generate(self, _request, *, call_sequence):
        self.calls.append(("PROPOSER", call_sequence))
        return ProposerAttempt(
            output=self.output,
            record=call_record(call_sequence, "PROPOSER", self.output),
        )


def test_wire_schemas_are_flat_service_compatible_subset():
    for text_format in (CRITIC_TEXT_FORMAT, PROPOSER_TEXT_FORMAT):
        assert text_format["type"] == "json_schema"
        assert text_format["strict"] is True
        assert text_format["name"]
        schema = text_format["schema"]
        assert schema["type"] == "object"
        assert "anyOf" not in schema
        raw = json.dumps(schema)
        assert "oneOf" not in raw
        assert "discriminator" not in raw
        _walk_schema(schema)


def test_static_schema_gate_rejects_forbidden_keyword():
    with pytest.raises(Stage1EError, match="forbidden schema keys"):
        _walk_schema({"type": "object", "oneOf": [], "properties": {}, "required": [], "additionalProperties": False})


def test_static_schema_gate_requires_all_properties_and_forbids_extra():
    with pytest.raises(Stage1EError, match="all object properties"):
        _walk_schema(
            {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            }
        )


def test_wire_format_gate_rejects_root_anyof(monkeypatch):
    from evals.meihua.intelligence_optimization_stage1e_v001.experiment import critic_first_wire_experiment_v1 as contract

    monkeypatch.setattr(
        contract,
        "type_to_text_format_param",
        lambda _model: {
            "type": "json_schema",
            "name": "bad_root",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
                "anyOf": [],
            },
        },
    )
    with pytest.raises(Stage1EError, match="root cannot use anyOf"):
        contract._wire_text_format(CriticWireOutput)
    with pytest.raises(Stage1EError, match="forbid extra"):
        _walk_schema(
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            }
        )


def test_critic_all_fields_are_required_even_when_nullable():
    data = ask_wire().model_dump(mode="json")
    data.pop("ready_reason")
    with pytest.raises(ValidationError):
        CriticWireOutput.model_validate(data)


def test_critic_branch_exclusivity():
    ask = ask_wire().model_dump(mode="json")
    ask["ready_reason"] = "这个READY理由不应该出现"
    with pytest.raises(ValidationError, match="cannot carry READY"):
        CriticWireOutput.model_validate(ask)
    ready = ready_wire().model_dump(mode="json")
    ready["question"] = "不该追问？"
    with pytest.raises(ValidationError, match="cannot carry ASK"):
        CriticWireOutput.model_validate(ready)
    ask = ask_wire().model_dump(mode="json")
    ask["non_blocking_unknowns"] = ["不该出现"]
    with pytest.raises(ValidationError, match="non-blocking"):
        CriticWireOutput.model_validate(ask)


def test_frame_value_wire_exclusivity():
    grounded_wire("值", "还没分清是在决定是否开放", turn_index=0)
    unknown_wire()
    with pytest.raises(ValidationError, match="GROUNDED requires"):
        FrameValueWire(status="GROUNDED", value="值", evidence_refs=[])
    with pytest.raises(ValidationError, match="require null value"):
        FrameValueWire(status="UNKNOWN", value="错误", evidence_refs=[])


def test_ask_path_never_calls_proposer():
    calls = []
    response = arbitrate_stage1e_request(
        payload(),
        critic=StubCritic(ask_wire(), calls),
        proposer=StubProposer(proposal_wire(), calls),
    )
    assert response["status"] == "ASK_CRITICAL"
    assert calls == [("CRITIC", 1)]


def test_ready_path_calls_critic_then_proposer():
    calls = []
    response = arbitrate_stage1e_request(
        payload(),
        critic=StubCritic(ready_wire(), calls),
        proposer=StubProposer(proposal_wire(), calls),
    )
    assert response["status"] == "CONFIRM"
    assert calls == [("CRITIC", 1), ("PROPOSER", 2)]


def test_critical_ready_requires_latest_answer_evidence():
    calls = []
    bad = arbitrate_stage1e_request(
        payload(critical=True),
        critic=StubCritic(ready_wire(critical=False), calls),
        proposer=StubProposer(proposal_wire(critical=True), calls),
    )
    assert bad["status"] == "REVIEW_ERROR"
    assert calls == [("CRITIC", 1)]


def test_provider_sends_frozen_wire_format_and_no_case_id(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            output = ask_wire()
            return SimpleNamespace(
                id="resp-1",
                _request_id="req-1",
                output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=1, output_tokens=2, total_tokens=3),
            )

    provider = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    )
    attempt = provider.generate(Stage1ERequest.model_validate(payload()), call_sequence=1)
    body = captured["input"][1]["content"]
    assert attempt.record.outcome == "SUCCESS"
    assert captured["text"]["format"] == CRITIC_TEXT_FORMAT
    assert "SECRET-CASE-ID" not in body
    assert "proposal" not in body.lower()
    assert json.loads(body)["answers"][0]["context_question"] == "背景补充"


def test_proposer_provider_sends_frozen_wire_format(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            output = proposal_wire()
            return SimpleNamespace(
                id="resp-proposer",
                _request_id="req-proposer",
                output_text=json.dumps(output.model_dump(mode="json"), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5),
            )

    from evals.meihua.intelligence_optimization_stage1e_v001.experiment.critic_first_wire_experiment_v1 import OpenAIProposer

    attempt = OpenAIProposer(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    ).generate(Stage1ERequest.model_validate(payload()), call_sequence=1)
    assert attempt.record.outcome == "SUCCESS"
    assert captured["text"]["format"] == PROPOSER_TEXT_FORMAT
    assert attempt.record.schema_sha256 == PROPOSER_WIRE_SCHEMA_SHA256


def test_http_400_invalid_schema_is_classified_and_observable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class InvalidSchemaError(RuntimeError):
        status_code = 400
        request_id = "req-schema"
        body = {
            "message": "bad schema",
            "code": "invalid_json_schema",
            "param": "text.format.schema",
        }

    class Responses:
        def create(self, **_kwargs):
            raise InvalidSchemaError("bad schema")

    attempt = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    ).generate(Stage1ERequest.model_validate(payload()), call_sequence=1)
    record = attempt.record
    assert record.outcome == "SCHEMA_COMPATIBILITY_ERROR"
    assert record.http_status == 400
    assert record.api_error_code == "invalid_json_schema"
    assert record.api_error_param == "text.format.schema"
    assert record.request_id == "req-schema"
    assert record.usage is None
    assert record.raw_parsed_output == InvalidSchemaError.body


def test_http_success_invalid_json_preserves_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class Responses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                id="resp-json",
                _request_id="req-json",
                output_text="not-json",
                usage=SimpleNamespace(input_tokens=2, output_tokens=2, total_tokens=4),
            )

    attempt = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    ).generate(Stage1ERequest.model_validate(payload()), call_sequence=1)
    assert attempt.record.outcome == "WIRE_JSON_PARSE_ERROR"
    assert attempt.record.raw_output_text == "not-json"
    assert attempt.record.usage.total_tokens == 4


def test_http_success_wire_validation_failure_preserves_raw(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    invalid = ask_wire().model_dump(mode="json")
    invalid["ready_reason"] = "混合分支"

    class Responses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                id="resp-wire",
                _request_id="req-wire",
                output_text=json.dumps(invalid, ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=3, output_tokens=3, total_tokens=6),
            )

    attempt = OpenAICritic(
        client_factory=lambda **_kwargs: SimpleNamespace(responses=Responses())
    ).generate(Stage1ERequest.model_validate(payload()), call_sequence=1)
    assert attempt.record.outcome == "WIRE_VALIDATION_ERROR"
    assert attempt.record.raw_parsed_output == invalid
    assert attempt.record.usage.total_tokens == 6


def _write_canary_fixture(tmp_path):
    stage = tmp_path / canary_runner.STAGE1E_REL
    (stage / "canary").mkdir(parents=True)
    (stage / "manifest.json").write_text(json.dumps({"canary_model": "stub"}), encoding="utf-8")
    cases = [
        {
            "case_id": "CANARY-CRITIC-ASK",
            "role": "CRITIC",
            "expected_verdict": "ASK_ONE",
            "question_text": payload()["question_text"],
            "answer_pool": [payload()["turns"][0]["answer"]] * 4,
        },
        {
            "case_id": "CANARY-CRITIC-READY",
            "role": "CRITIC",
            "expected_verdict": "READY",
            "question_text": payload()["question_text"],
            "answer_pool": [payload()["turns"][0]["answer"]] * 4,
        },
        {
            "case_id": "CANARY-PROPOSER",
            "role": "PROPOSER",
            "expected_verdict": None,
            "question_text": payload()["question_text"],
            "answer_pool": [payload()["turns"][0]["answer"]] * 4,
        },
    ]
    (stage / "canary/canary_inputs.json").write_text(
        json.dumps(
            {"synthetic": True, "not_for_capability_scoring": True, "cases": cases}
        ),
        encoding="utf-8",
    )
    return stage


def test_canary_schema_error_short_circuits_after_first_call(tmp_path, monkeypatch):
    stage = _write_canary_fixture(tmp_path)
    monkeypatch.setattr(canary_runner, "_validate_frozen", lambda *_args: None)
    calls = []

    class Critic:
        def __init__(self, **_kwargs):
            pass

        def generate(self, _request, *, call_sequence):
            calls.append(("CRITIC", call_sequence))
            record = call_record(call_sequence, "CRITIC", None, "SCHEMA_COMPATIBILITY_ERROR")
            record.http_status = 400
            record.api_error_code = "invalid_json_schema"
            record.api_error_param = "text.format.schema"
            record.usage = None
            return CriticAttempt(output=None, record=record)

    monkeypatch.setattr(canary_runner, "OpenAICritic", Critic)
    path = canary_runner.run(tmp_path, "stub")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["run_status"] == "CANARY_SCHEMA_FAILED"
    assert result["attempted_call_count"] == 1
    assert calls == [("CRITIC", 1)]


def test_canary_input_contract_requires_exact_three_paths():
    valid = [
        {
            "case_id": "CANARY-CRITIC-ASK",
            "role": "CRITIC",
            "expected_verdict": "ASK_ONE",
            "question_text": "问题",
            "answer_pool": ["a"] * 4,
        },
        {
            "case_id": "CANARY-CRITIC-READY",
            "role": "CRITIC",
            "expected_verdict": "READY",
            "question_text": "问题",
            "answer_pool": ["a"] * 4,
        },
        {
            "case_id": "CANARY-PROPOSER",
            "role": "PROPOSER",
            "expected_verdict": None,
            "question_text": "问题",
            "answer_pool": ["a"] * 4,
        },
    ]
    document = {"synthetic": True, "not_for_capability_scoring": True, "cases": valid}
    canary_runner._validate_canary_inputs(document)
    invalid = [dict(item) for item in valid]
    invalid[0] = {**invalid[0], "expected_verdict": "READY"}
    with pytest.raises(RuntimeError, match="frozen three paths"):
        canary_runner._validate_canary_inputs({**document, "cases": invalid})


def test_invalid_canary_inputs_do_not_consume_marker(tmp_path, monkeypatch):
    stage = _write_canary_fixture(tmp_path)
    document = json.loads((stage / "canary/canary_inputs.json").read_text(encoding="utf-8"))
    document["synthetic"] = False
    (stage / "canary/canary_inputs.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(canary_runner, "_validate_frozen", lambda *_args: None)
    with pytest.raises(RuntimeError, match="explicitly synthetic"):
        canary_runner.run(tmp_path, "stub")
    assert not (stage / "canary/stage1e_canary_started.json").exists()


def test_canary_critic_semantic_failure_updates_record_and_counts(tmp_path, monkeypatch):
    stage = _write_canary_fixture(tmp_path)
    monkeypatch.setattr(canary_runner, "_validate_frozen", lambda *_args: None)

    class Critic:
        def __init__(self, **_kwargs):
            pass

        def generate(self, _request, *, call_sequence):
            output = ask_wire()
            return CriticAttempt(output=output, record=call_record(call_sequence, "CRITIC", output))

    monkeypatch.setattr(canary_runner, "OpenAICritic", Critic)
    monkeypatch.setattr(
        canary_runner,
        "_validate_review",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("semantic failure")),
    )
    path = canary_runner.run(tmp_path, "stub")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["steps"][0]["record"]["outcome"] == "SEMANTIC_VALIDATION_ERROR"
    assert result["steps"][0]["failure"] == "SEMANTIC_VALIDATION_ERROR"
    assert result["wire_successful_call_count"] == 1
    assert result["validated_path_success_count"] == 0
    assert result["successful_call_count"] == 0


def test_canary_proposer_semantic_failure_updates_record(tmp_path, monkeypatch):
    stage = _write_canary_fixture(tmp_path)
    monkeypatch.setattr(canary_runner, "_validate_frozen", lambda *_args: None)

    class Critic:
        def __init__(self, **_kwargs):
            pass

        def generate(self, request, *, call_sequence):
            output = ask_wire() if "ASK" in request.session_id else ready_wire()
            return CriticAttempt(output=output, record=call_record(call_sequence, "CRITIC", output))

    class Proposer:
        def __init__(self, **_kwargs):
            pass

        def generate(self, _request, *, call_sequence):
            output = proposal_wire()
            return ProposerAttempt(output=output, record=call_record(call_sequence, "PROPOSER", output))

    monkeypatch.setattr(canary_runner, "OpenAICritic", Critic)
    monkeypatch.setattr(canary_runner, "OpenAIProposer", Proposer)
    monkeypatch.setattr(
        canary_runner,
        "_validate_proposal",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("semantic failure")),
    )
    path = canary_runner.run(tmp_path, "stub")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["steps"][2]["record"]["outcome"] == "SEMANTIC_VALIDATION_ERROR"
    assert result["steps"][2]["failure"] == "SEMANTIC_VALIDATION_ERROR"
    assert result["wire_successful_call_count"] == 3
    assert result["validated_path_success_count"] == 2


def test_canary_three_success_paths_use_exactly_three_calls(tmp_path, monkeypatch):
    stage = _write_canary_fixture(tmp_path)
    monkeypatch.setattr(canary_runner, "_validate_frozen", lambda *_args: None)
    calls = []

    class Critic:
        def __init__(self, **_kwargs):
            pass

        def generate(self, request, *, call_sequence):
            calls.append(("CRITIC", call_sequence))
            output = ask_wire() if "ASK" in request.session_id else ready_wire()
            return CriticAttempt(output=output, record=call_record(call_sequence, "CRITIC", output))

    class Proposer:
        def __init__(self, **_kwargs):
            pass

        def generate(self, _request, *, call_sequence):
            calls.append(("PROPOSER", call_sequence))
            output = proposal_wire()
            return ProposerAttempt(
                output=output, record=call_record(call_sequence, "PROPOSER", output)
            )

    monkeypatch.setattr(canary_runner, "OpenAICritic", Critic)
    monkeypatch.setattr(canary_runner, "OpenAIProposer", Proposer)
    path = canary_runner.run(tmp_path, "stub")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["run_status"] == "CANARY_PASSED"
    assert result["attempted_call_count"] == 3
    assert calls == [("CRITIC", 1), ("CRITIC", 2), ("PROPOSER", 3)]


def test_prompts_are_generic_and_do_not_contain_case_ids():
    for value in ("GXID-M01", "GXID-H11", "GXID-H16", "CANARY-CRITIC-ASK"):
        assert value not in CRITIC_INSTRUCTIONS
        assert value not in PROPOSER_INSTRUCTIONS
