from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI
from pydantic import TypeAdapter, ValidationError

from abalo_iching.personalization_gate2.background_provider import (
    OpenAIGate2BackgroundProvider,
)
from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    VISIBLE_CALIBRATION_CASES,
)
from abalo_iching.personalization_gate2.models import (
    DryRunStatus,
    ExperimentArm,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
)
from abalo_iching.personalization_gate2.stage_c2_contract import (
    C2_SOURCE_TRACE_INSTRUCTIONS,
    STAGE_C2_EXTERNAL_MODEL_CALLS,
    STAGE_C2_PROMPT_VERSION,
    STAGE_C2_REAL_RETEST_AUTHORIZED,
    STAGE_C2_RETEST_MAX_OUTPUT_TOKENS,
    STAGE_C2_RETEST_REASONING_EFFORT,
    STAGE_C2_SCHEMA_VERSION,
    STAGE_C2_VALIDATOR_VERSION,
    Gate2ExperimentOutputV2,
    Gate2StageC2PromptBuilder,
    SourceTraceV2,
    build_stage_c2_request,
    build_stage_c2_retest_request,
    gate2_output_schema_v2_sha256,
)
from abalo_iching.personalization_gate2.stage_c2_execution import (
    Gate2StageC2OfflineBackgroundRunner,
    OfflineGate2StageC2BackgroundProvider,
    Gate2StageC2BackgroundRunner,
    OpenAIGate2StageC2BackgroundProvider,
)


def _trace_payload(
    *,
    trace_id: str,
    source_kind: str,
    link_mode: str,
    reality_refs: list[str],
    evidence_refs: list[str],
    interpretation_hypothesis: bool,
) -> dict[str, object]:
    return {
        "trace_id": trace_id,
        "source_kind": source_kind,
        "source_ref": trace_id,
        "supports_fields": ["user_facing_reading.core_judgment"],
        "link_mode": link_mode,
        "reality_refs": reality_refs,
        "evidence_refs": evidence_refs,
        "interpretation_hypothesis": interpretation_hypothesis,
    }


def _resolved_trace_branches() -> list[dict[str, object]]:
    schema = Gate2ExperimentOutputV2.model_json_schema()
    item_schema = schema["properties"]["source_trace"]["items"]
    return [
        schema["$defs"][branch["$ref"].rsplit("/", 1)[-1]]
        for branch in item_schema["anyOf"]
    ]


def _branch(
    branches: list[dict[str, object]],
    source_kind: str,
    link_mode: str,
) -> dict[str, object]:
    for branch in branches:
        properties = branch["properties"]
        if (
            properties["source_kind"].get("const") == source_kind
            and properties["link_mode"].get("const") == link_mode
        ):
            return branch
    raise AssertionError(f"missing schema branch: {source_kind}/{link_mode}")


def test_c2_is_offline_only_and_has_new_version_coordinates() -> None:
    request = build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    assert request.metadata.schema_version == STAGE_C2_SCHEMA_VERSION == "gate2_schema_v2"
    assert request.metadata.prompt_version == STAGE_C2_PROMPT_VERSION
    assert request.metadata.validator_version == STAGE_C2_VALIDATOR_VERSION
    assert STAGE_C2_EXTERNAL_MODEL_CALLS == 1
    assert STAGE_C2_REAL_RETEST_AUTHORIZED is True


def test_c2_schema_exposes_fact_empty_reference_constraints() -> None:
    branches = _resolved_trace_branches()
    for source_kind in ("REALITY_FACT", "CHART_FACT"):
        branch = _branch(branches, source_kind, "NOT_APPLICABLE")
        properties = branch["properties"]
        assert properties["reality_refs"]["maxItems"] == 0
        assert properties["evidence_refs"]["maxItems"] == 0
        assert properties["interpretation_hypothesis"]["const"] is False
        assert {"reality_refs", "evidence_refs"} <= set(branch["required"])


def test_c2_schema_exposes_both_interpretive_link_modes() -> None:
    branches = _resolved_trace_branches()
    reality_only = _branch(branches, "INTERPRETIVE_LINK", "REALITY_ONLY")
    reality_and_chart = _branch(
        branches,
        "INTERPRETIVE_LINK",
        "REALITY_AND_CHART",
    )
    assert reality_only["properties"]["reality_refs"]["minItems"] == 1
    assert reality_only["properties"]["evidence_refs"]["maxItems"] == 0
    assert reality_and_chart["properties"]["reality_refs"]["minItems"] == 1
    assert reality_and_chart["properties"]["evidence_refs"]["minItems"] == 1


def test_c2_reproduced_c1_fact_self_reference_fails_at_schema_boundary() -> None:
    payload = _trace_payload(
        trace_id="RW01",
        source_kind="REALITY_FACT",
        link_mode="NOT_APPLICABLE",
        reality_refs=["RW01"],
        evidence_refs=[],
        interpretation_hypothesis=False,
    )
    with pytest.raises(ValidationError, match="at most 0 items"):
        TypeAdapter(SourceTraceV2).validate_python(payload)


@pytest.mark.parametrize(
    "payload",
    [
        _trace_payload(
            trace_id="RW01",
            source_kind="REALITY_FACT",
            link_mode="NOT_APPLICABLE",
            reality_refs=[],
            evidence_refs=[],
            interpretation_hypothesis=False,
        ),
        _trace_payload(
            trace_id="EV01",
            source_kind="CHART_FACT",
            link_mode="NOT_APPLICABLE",
            reality_refs=[],
            evidence_refs=[],
            interpretation_hypothesis=False,
        ),
        _trace_payload(
            trace_id="IL01",
            source_kind="INTERPRETIVE_LINK",
            link_mode="REALITY_ONLY",
            reality_refs=["RW01"],
            evidence_refs=[],
            interpretation_hypothesis=True,
        ),
        _trace_payload(
            trace_id="IL01",
            source_kind="INTERPRETIVE_LINK",
            link_mode="REALITY_AND_CHART",
            reality_refs=["RW01"],
            evidence_refs=["EV01"],
            interpretation_hypothesis=True,
        ),
    ],
)
def test_c2_accepts_each_explicit_source_trace_branch(
    payload: dict[str, object],
) -> None:
    assert TypeAdapter(SourceTraceV2).validate_python(payload)


def test_c2_prompt_repeats_machine_contract_in_plain_language() -> None:
    request = build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    prompt = Gate2StageC2PromptBuilder().build(request)
    assert prompt.prompt_version == STAGE_C2_PROMPT_VERSION
    assert C2_SOURCE_TRACE_INSTRUCTIONS in prompt.system_instructions
    assert "不得再把自己的 RWxx 或 EVxx 重复写入" in prompt.system_instructions
    assert prompt.input_payload["output_schema"] == Gate2ExperimentOutputV2.model_json_schema()
    json.dumps(prompt.input_payload, ensure_ascii=False)


def test_c2_does_not_claim_a_group_or_real_retest_authority() -> None:
    with pytest.raises(ValueError, match="不重跑A组"):
        build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.A)


def test_c2_retest_request_preserves_c1_runtime_coordinates_and_validates() -> None:
    request = build_stage_c2_retest_request(
        VISIBLE_CALIBRATION_CASES[0],
        ExperimentArm.B,
    )

    assert request.metadata.reasoning_effort == STAGE_C2_RETEST_REASONING_EFFORT
    assert request.metadata.max_output_tokens == STAGE_C2_RETEST_MAX_OUTPUT_TOKENS
    assert request.__class__.model_validate(request.model_dump(mode="json")) == request


def _valid_b_output(request: Gate2ExperimentRequest) -> dict[str, object]:
    facts = request.reality.reality_facts()[:2]
    reality_refs = [item.ref for item in facts]
    source_trace = [
        {
            "trace_id": item.ref,
            "source_kind": "REALITY_FACT",
            "source_ref": item.ref,
            "supports_fields": [f"context_facts[{index}]"],
            "link_mode": "NOT_APPLICABLE",
            "reality_refs": [],
            "evidence_refs": [],
            "interpretation_hypothesis": False,
        }
        for index, item in enumerate(facts)
    ]
    source_trace.append(
        {
            "trace_id": "IL01",
            "source_kind": "INTERPRETIVE_LINK",
            "source_ref": "IL01",
            "supports_fields": [
                "judgment_signature.direction",
                "judgment_signature.method",
                "judgment_signature.agency",
                "judgment_signature.main_conflict",
                "judgment_signature.action_intensity",
                "user_facing_reading.core_judgment",
                "user_facing_reading.explanation",
                "user_facing_reading.reality_application",
                "user_facing_reading.action",
                "user_facing_reading.switch_condition",
            ],
            "link_mode": "REALITY_ONLY",
            "reality_refs": reality_refs,
            "evidence_refs": [],
            "interpretation_hypothesis": True,
        }
    )
    return {
        "context_facts": [
            {"fact_text": item.text, "reality_refs": [item.ref]}
            for item in facts
        ],
        "unknowns": [
            {"unknown_text": item.text, "must_not_infer": True}
            for item in request.reality.unknowns
        ],
        "chart_signals": [],
        "core_conflict": {
            "text": "当前关键是让现有准备获得一次明确回应。",
            "reality_refs": reality_refs,
            "evidence_refs": [],
            "interpretation_hypothesis": True,
        },
        "judgment_signature": {
            "direction": "推进",
            "method": "澄清",
            "agency": "在用户",
            "main_conflict": "回应",
            "action_intensity": "中",
        },
        "opposite_posture_and_reason": {
            "opposite_posture": "继续独自准备而不提出",
            "reason": "继续增加材料不能替代有决定权者的明确答复。",
            "reality_refs": reality_refs,
            "evidence_refs": [],
        },
        "one_action": {
            "action_text": "提交现有方案并请求一次正式答复。",
            "target_or_person": "有决定权的人",
            "observable_result": "对方给出下一步、补充条件或拒绝理由。",
            "reality_refs": reality_refs,
            "evidence_refs": [],
        },
        "switch_conditions": [
            {
                "condition_text": "若对方提出明确条件，就先补齐条件再推进。",
                "reality_refs": reality_refs,
                "evidence_refs": [],
            }
        ],
        "source_trace": source_trace,
        "user_facing_reading": {
            "core_judgment": "现有准备可以进入一次正式沟通。",
            "explanation": "现在需要验证的是有决定权者是否给出明确回应。",
            "reality_application": "把已经完成的准备转成可观察的外部答复。",
            "action": "提交方案并直接询问下一步。",
            "switch_condition": "若出现明确补充条件，就按条件调整后再推进。",
        },
    }


def _response(
    status: str,
    *,
    output: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="resp-stage-c2-offline",
        status=status,
        model="gpt-5.6-sol",
        output_text=json.dumps(output, ensure_ascii=False) if output else "",
        output=[],
        incomplete_details=None,
        usage=SimpleNamespace(
            input_tokens=1200 if output else 0,
            input_tokens_details=SimpleNamespace(
                cached_tokens=0,
                cache_write_tokens=0,
            ),
            output_tokens=1800 if output else 0,
            output_tokens_details=SimpleNamespace(reasoning_tokens=400),
            total_tokens=3000 if output else 0,
        ),
    )


class _FakeResponses:
    def __init__(self, initial: object, retrieved: list[object]) -> None:
        self.initial = initial
        self.retrieved = iter(retrieved)
        self.parse_calls = 0
        self.retrieve_calls = 0
        self.parse_kwargs: dict[str, object] = {}

    def parse(self, **kwargs: object) -> object:
        self.parse_calls += 1
        self.parse_kwargs = kwargs
        return self.initial

    def retrieve(self, response_id: str) -> object:
        assert response_id == "resp-stage-c2-offline"
        self.retrieve_calls += 1
        return next(self.retrieved)


class _FakeClient:
    def __init__(self, responses: object) -> None:
        self.responses = responses


def _offline_provider(
    responses: _FakeResponses,
    request: Gate2ExperimentRequest,
) -> OfflineGate2StageC2BackgroundProvider:
    return OfflineGate2StageC2BackgroundProvider(
        client_factory=lambda **kwargs: _FakeClient(responses),
        model=request.metadata.model,
        reasoning_effort=request.metadata.reasoning_effort,
        max_output_tokens=request.metadata.max_output_tokens,
        sleep_fn=lambda _: None,
    )


def test_c2_offline_background_runner_validates_v2_end_to_end(
    tmp_path: Path,
) -> None:
    request = build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    output = _valid_b_output(request)
    responses = _FakeResponses(
        _response("queued"),
        [_response("completed", output=output)],
    )
    provider = _offline_provider(responses, request)
    repository = tmp_path / "repository"
    repository.mkdir()
    runner = Gate2StageC2OfflineBackgroundRunner(repository_root=repository)

    result = runner.run(
        request,
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )

    assert result.status is DryRunStatus.VALIDATED
    assert isinstance(result.output, Gate2ExperimentOutputV2)
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 1
    assert responses.parse_kwargs["text_format"] is Gate2ExperimentOutputV2
    assert result.evidence_record.schema_version == STAGE_C2_SCHEMA_VERSION
    assert result.evidence_record.schema_sha256 == gate2_output_schema_v2_sha256()
    assert result.evidence_record.validator_version == STAGE_C2_VALIDATOR_VERSION
    assert result.evidence_record.cost_usd == 0
    assert runner.budget_guard.spent_usd == 0


def test_c2_offline_provider_rejects_default_network_client() -> None:
    with pytest.raises(ValueError, match="禁止使用默认OpenAI网络客户端"):
        OfflineGate2StageC2BackgroundProvider(client_factory=OpenAI)


def test_c2_offline_provider_rejects_wrapped_openai_network_client() -> None:
    def client_factory(**kwargs: object) -> OpenAI:
        return OpenAI(api_key="offline-placeholder", **kwargs)

    provider = OfflineGate2StageC2BackgroundProvider(
        client_factory=client_factory,
    )
    with pytest.raises(ValueError, match="只允许使用httpx.MockTransport"):
        provider._client()


def test_c2_runner_rejects_c1_provider_type(tmp_path: Path) -> None:
    request = build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    runner = Gate2StageC2OfflineBackgroundRunner(repository_root=tmp_path / "repository")
    provider = OpenAIGate2BackgroundProvider(
        model=request.metadata.model,
        reasoning_effort=request.metadata.reasoning_effort,
        max_output_tokens=request.metadata.max_output_tokens,
    )
    with pytest.raises(RuntimeError, match="只接受隔离的后台Provider"):
        runner.run(
            request,
            provider=provider,
            evidence_root=tmp_path / "external-evidence",
        )


def test_c2_live_runner_is_mockable_but_uses_v2_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_stage_c2_retest_request(
        VISIBLE_CALIBRATION_CASES[0],
        ExperimentArm.B,
    )
    output = _valid_b_output(request)
    responses = _FakeResponses(
        _response("queued"),
        [_response("completed", output=output)],
    )
    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder")
    provider = OpenAIGate2StageC2BackgroundProvider(
        client_factory=lambda **kwargs: _FakeClient(responses),
        model=request.metadata.model,
        reasoning_effort=request.metadata.reasoning_effort,
        max_output_tokens=request.metadata.max_output_tokens,
        sleep_fn=lambda _: None,
    )
    repository = tmp_path / "repository"
    repository.mkdir()
    runner = Gate2StageC2BackgroundRunner(
        repository_root=repository,
        budget_guard=Gate2CalibrationBudgetGuard(
            declared_account_balance_usd=Decimal("7.50"),
            authorized_spend_usd=Decimal("0.50"),
            required_reserve_usd=Decimal("7"),
        ),
    )

    result = runner.run(
        request,
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )

    assert result.status is DryRunStatus.VALIDATED
    assert isinstance(result.output, Gate2ExperimentOutputV2)
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 1
    assert responses.parse_kwargs["text_format"] is Gate2ExperimentOutputV2
    assert result.evidence_record.schema_version == STAGE_C2_SCHEMA_VERSION


def test_c1_provider_still_uses_v1_output_model() -> None:
    assert OpenAIGate2BackgroundProvider.output_model is Gate2ExperimentOutput
    assert OpenAIGate2BackgroundProvider.stage_label == "C.1"


def test_c2_real_sdk_mock_transport_sends_v2_schema(
    tmp_path: Path,
) -> None:
    request = build_stage_c2_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    output = _valid_b_output(request)
    seen_schema_branches: list[int] = []

    def response_body(status: str) -> dict[str, object]:
        completed = status == "completed"
        return {
            "id": "resp-stage-c2-offline",
            "object": "response",
            "created_at": int(time.time()),
            "status": status,
            "completed_at": int(time.time()) if completed else None,
            "background": True,
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": request.metadata.max_output_tokens,
            "model": request.metadata.model,
            "output": (
                [
                    {
                        "id": "msg-stage-c2-offline",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "annotations": [],
                                "logprobs": [],
                                "text": json.dumps(output, ensure_ascii=False),
                            }
                        ],
                    }
                ]
                if completed
                else []
            ),
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {
                "effort": request.metadata.reasoning_effort,
                "summary": None,
            },
            "store": False,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "usage": (
                {
                    "input_tokens": 1200,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 1800,
                    "output_tokens_details": {"reasoning_tokens": 400},
                    "total_tokens": 3000,
                }
                if completed
                else None
            ),
        }

    def handler(http_request: httpx.Request) -> httpx.Response:
        if http_request.method == "POST":
            payload = json.loads(http_request.content)
            schema = payload["text"]["format"]["schema"]
            seen_schema_branches.append(
                len(schema["properties"]["source_trace"]["items"]["anyOf"])
            )
            return httpx.Response(
                200,
                json=response_body("queued"),
                request=http_request,
            )
        return httpx.Response(
            200,
            json=response_body("completed"),
            request=http_request,
        )

    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs: object) -> OpenAI:
        return OpenAI(
            api_key="offline-placeholder",
            http_client=httpx.Client(transport=transport),
            max_retries=0,
        )

    provider = OfflineGate2StageC2BackgroundProvider(
        client_factory=client_factory,
        model=request.metadata.model,
        reasoning_effort=request.metadata.reasoning_effort,
        max_output_tokens=request.metadata.max_output_tokens,
        sleep_fn=lambda _: None,
    )
    repository = tmp_path / "repository"
    repository.mkdir()
    result = Gate2StageC2OfflineBackgroundRunner(
        repository_root=repository
    ).run(
        request,
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )

    assert result.status is DryRunStatus.VALIDATED
    assert seen_schema_branches == [4]
