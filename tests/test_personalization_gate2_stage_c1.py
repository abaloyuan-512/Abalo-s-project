from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI

from abalo_iching.personalization_gate2.background_checkpoint import (
    Gate2BackgroundCheckpointWriter,
)
from abalo_iching.personalization_gate2.background_provider import (
    OpenAIGate2BackgroundProvider,
    STAGE_C1_MAX_OUTPUT_TOKENS,
    STAGE_C1_REASONING_EFFORT,
)
from abalo_iching.personalization_gate2.background_runner import (
    Gate2BackgroundCalibrationRunner,
)
from abalo_iching.personalization_gate2.budget import Gate2CalibrationBudgetGuard
from abalo_iching.personalization_gate2.calibration_cases import (
    VISIBLE_CALIBRATION_CASES,
)
from abalo_iching.personalization_gate2.calibration_prompt_builder import (
    Gate2CalibrationPromptBuilder,
)
from abalo_iching.personalization_gate2.live_provider import Gate2LiveProviderError
from abalo_iching.personalization_gate2.models import (
    DryRunStatus,
    ExperimentArm,
    Gate2BackgroundCheckpoint,
)
from abalo_iching.personalization_gate2.stage_c1 import (
    PAID_RETEST_AUTHORIZATION_CONSUMED,
    PAID_RETEST_AUTHORIZED,
    PROPOSED_AUTHORIZED_SPEND_USD,
    PROPOSED_MAX_GENERATION_CALLS,
    build_stage_c1_request,
)


def _output_dict() -> dict[str, object]:
    return {
        "context_facts": [
            {"fact_text": "改进方案已经准备了两周。", "reality_refs": ["RW01"]},
            {"fact_text": "直属负责人认可方案方向。", "reality_refs": ["RW02"]},
        ],
        "unknowns": [
            {
                "unknown_text": "最终负责人是否支持该方案尚不明确。",
                "must_not_infer": True,
            },
            {
                "unknown_text": "资源重新分配后还能保留多少执行空间尚不明确。",
                "must_not_infer": True,
            },
        ],
        "chart_signals": [],
        "core_conflict": {
            "text": "关键是让最终负责人形成可观察的正式回应。",
            "reality_refs": ["RW01", "RW02"],
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
            "opposite_posture": "继续独自准备",
            "reason": "继续准备不能验证最终负责人是否支持。",
            "reality_refs": ["RW01", "RW02"],
            "evidence_refs": [],
        },
        "one_action": {
            "action_text": "提交现有方案并请求一次正式回应。",
            "target_or_person": "最终负责人",
            "observable_result": "对方给出下一步、补充条件或拒绝理由。",
            "reality_refs": ["RW01", "RW02"],
            "evidence_refs": [],
        },
        "switch_conditions": [
            {
                "condition_text": "若对方提出明确补充条件，就先补齐条件。",
                "reality_refs": ["RW02"],
                "evidence_refs": [],
            }
        ],
        "source_trace": [
            {
                "trace_id": "RW01",
                "source_kind": "REALITY_FACT",
                "source_ref": "RW01",
                "supports_fields": ["context_facts[0]"],
                "link_mode": "NOT_APPLICABLE",
                "reality_refs": [],
                "evidence_refs": [],
                "interpretation_hypothesis": False,
            },
            {
                "trace_id": "RW02",
                "source_kind": "REALITY_FACT",
                "source_ref": "RW02",
                "supports_fields": ["context_facts[1]"],
                "link_mode": "NOT_APPLICABLE",
                "reality_refs": [],
                "evidence_refs": [],
                "interpretation_hypothesis": False,
            },
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
                "reality_refs": ["RW01", "RW02"],
                "evidence_refs": [],
                "interpretation_hypothesis": True,
            },
        ],
        "user_facing_reading": {
            "core_judgment": "现在可以提出方案并要求正式回应。",
            "explanation": "准备已经形成，下一项未知来自最终负责人。",
            "reality_application": "直属负责人已认可方向，但最终负责人尚未看到。",
            "action": "向最终负责人提交现有方案并询问下一步。",
            "switch_condition": "若出现明确补充条件，就先补齐条件再推进。",
        },
    }


def _response(
    status: str,
    *,
    output: dict[str, object] | None = None,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    incomplete_reason: str | None = None,
):
    return SimpleNamespace(
        id="resp-stage-c1-test",
        status=status,
        model="gpt-5.6-sol",
        output_text=(json.dumps(output, ensure_ascii=False) if output else ""),
        output=[],
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason) if incomplete_reason else None
        ),
        usage=SimpleNamespace(
            input_tokens=4185 if output_tokens else 0,
            input_tokens_details=SimpleNamespace(
                cached_tokens=0,
                cache_write_tokens=0,
            ),
            output_tokens=output_tokens,
            output_tokens_details=SimpleNamespace(
                reasoning_tokens=reasoning_tokens
            ),
            total_tokens=(4185 + output_tokens if output_tokens else 0),
        ),
    )


class _FakeBackgroundResponses:
    def __init__(self, initial, retrieved: list[object]) -> None:
        self.initial = initial
        self.retrieved = iter(retrieved)
        self.parse_calls = 0
        self.retrieve_calls = 0
        self.parse_kwargs = None

    def parse(self, **kwargs):
        self.parse_calls += 1
        self.parse_kwargs = kwargs
        return self.initial

    def retrieve(self, response_id: str):
        assert response_id == "resp-stage-c1-test"
        self.retrieve_calls += 1
        result = next(self.retrieved)
        if isinstance(result, Exception):
            raise result
        return result


class _TransientRetrieveError(Exception):
    status_code = 500


class _FakeClient:
    def __init__(self, responses: _FakeBackgroundResponses) -> None:
        self.responses = responses


def _provider(
    responses: _FakeBackgroundResponses,
    *,
    checkpoints: list[Gate2BackgroundCheckpoint] | None = None,
    max_poll_attempts: int = 10,
) -> OpenAIGate2BackgroundProvider:
    return OpenAIGate2BackgroundProvider(
        client_factory=lambda **kwargs: _FakeClient(responses),
        sleep_fn=lambda _: None,
        max_poll_attempts=max_poll_attempts,
        on_checkpoint=(checkpoints.append if checkpoints is not None else None),
    )


def _prompt():
    request = build_stage_c1_request(
        VISIBLE_CALIBRATION_CASES[0],
        ExperimentArm.B,
    )
    return Gate2CalibrationPromptBuilder().build(request)


def test_stage_c1_candidate_is_offline_and_fits_proposed_45_cent_ceiling() -> None:
    request = build_stage_c1_request(
        VISIBLE_CALIBRATION_CASES[0],
        ExperimentArm.B,
    )
    provider = OpenAIGate2BackgroundProvider()
    estimate = provider.pricing.conservative_preflight_estimate(
        Gate2CalibrationPromptBuilder().build(request),
        max_output_tokens=provider.max_output_tokens,
    )
    assert PAID_RETEST_AUTHORIZED is True
    assert PAID_RETEST_AUTHORIZATION_CONSUMED is True
    assert PROPOSED_MAX_GENERATION_CALLS == 1
    assert PROPOSED_AUTHORIZED_SPEND_USD == Decimal("0.45")
    assert request.metadata.reasoning_effort == STAGE_C1_REASONING_EFFORT == "medium"
    assert request.metadata.max_output_tokens == STAGE_C1_MAX_OUTPUT_TOKENS == 10_000
    assert estimate <= PROPOSED_AUTHORIZED_SPEND_USD


def test_background_provider_creates_once_and_polls_same_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    checkpoints: list[Gate2BackgroundCheckpoint] = []
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _response("in_progress"),
            _response(
                "completed",
                output=_output_dict(),
                output_tokens=2500,
                reasoning_tokens=1200,
            ),
        ],
    )
    provider = _provider(responses, checkpoints=checkpoints)
    result = provider.generate(_prompt())
    assert provider.call_count == 1
    assert provider.poll_count == 2
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 2
    assert responses.parse_kwargs["background"] is True
    assert responses.parse_kwargs["store"] is False
    assert responses.parse_kwargs["reasoning"] == {"effort": "medium"}
    assert responses.parse_kwargs["max_output_tokens"] == 10_000
    assert result.response_id == "resp-stage-c1-test"
    assert result.api_status == "completed"
    assert result.background_mode is True
    assert result.poll_count == 2
    assert [item.api_status for item in checkpoints] == [
        "queued",
        "in_progress",
        "completed",
    ]


def test_background_provider_recovers_same_response_after_transient_poll_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _TransientRetrieveError("synthetic upstream 500"),
            _response("in_progress"),
            _response(
                "completed",
                output=_output_dict(),
                output_tokens=2500,
                reasoning_tokens=1200,
            ),
        ],
    )
    provider = _provider(responses)

    result = provider.generate(_prompt())

    assert result.api_status == "completed"
    assert provider.call_count == 1
    assert provider.poll_count == 3
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 3


def test_background_provider_does_not_hide_nontransient_poll_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [ValueError("synthetic client defect")],
    )
    provider = _provider(responses)

    with pytest.raises(Gate2LiveProviderError) as captured:
        provider.generate(_prompt())

    assert captured.value.code == "background_poll_error"
    assert provider.call_count == 1
    assert provider.poll_count == 1
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 1


def test_resume_only_retrieves_existing_response_and_never_creates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _response(
                "completed",
                output=_output_dict(),
                output_tokens=2000,
                reasoning_tokens=900,
            )
        ],
    )
    provider = _provider(responses)
    result = provider.resume(_prompt(), response_id="resp-stage-c1-test")
    assert result.response_id == "resp-stage-c1-test"
    assert provider.call_count == 0
    assert responses.parse_calls == 0
    assert responses.retrieve_calls == 1


def test_incomplete_background_response_preserves_usage_cost_and_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _response(
                "incomplete",
                output_tokens=10_000,
                reasoning_tokens=9_500,
                incomplete_reason="max_output_tokens",
            )
        ],
    )
    provider = _provider(responses)
    with pytest.raises(Gate2LiveProviderError) as captured:
        provider.generate(_prompt())
    error = captured.value
    assert error.code == "response_incomplete"
    assert error.response_id == "resp-stage-c1-test"
    assert error.api_status == "incomplete"
    assert error.incomplete_reason == "max_output_tokens"
    assert error.usage.output_tokens == 10_000
    assert error.usage.reasoning_tokens == 9_500
    assert error.cost_usd == 0.320925
    assert provider.call_count == 1
    assert responses.parse_calls == 1


def test_poll_limit_stops_without_second_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [_response("in_progress")],
    )
    provider = _provider(responses, max_poll_attempts=1)
    with pytest.raises(Gate2LiveProviderError) as captured:
        provider.generate(_prompt())
    assert captured.value.code == "background_poll_limit_reached"
    assert captured.value.response_id == "resp-stage-c1-test"
    assert provider.call_count == 1
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 1


def test_checkpoint_writer_uses_new_hashed_files_and_can_resume(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    writer = Gate2BackgroundCheckpointWriter(
        repository_root=repository,
        output_root=tmp_path / "external-evidence",
        case_id="G2CAL-001",
        arm=ExperimentArm.B,
    )
    writer.write(
        Gate2BackgroundCheckpoint(
            response_id="resp-stage-c1-test",
            api_status="queued",
            terminal=False,
            generation_calls=1,
            poll_count=0,
        )
    )
    writer.write(
        Gate2BackgroundCheckpoint(
            response_id="resp-stage-c1-test",
            api_status="in_progress",
            terminal=False,
            generation_calls=1,
            poll_count=1,
        )
    )
    latest = writer.latest()
    assert latest is not None
    assert latest.response_id == "resp-stage-c1-test"
    assert latest.poll_count == 1
    assert len(list(writer.directory.glob("checkpoint_*.json"))) == 2
    assert len(list(writer.directory.glob("checkpoint_*.sha256"))) == 2


def test_checkpoint_writer_rejects_repository_internal_path(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(ValueError, match="仓库之外"):
        Gate2BackgroundCheckpointWriter(
            repository_root=repository,
            output_root=repository / "forbidden-evidence",
            case_id="G2CAL-001",
            arm=ExperimentArm.B,
        )
    with pytest.raises(ValueError, match="case_id不安全"):
        Gate2BackgroundCheckpointWriter(
            repository_root=repository,
            output_root=tmp_path / "external-evidence",
            case_id="../escape",
            arm=ExperimentArm.B,
        )


def test_background_runner_records_terminal_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _response(
                "completed",
                output=_output_dict(),
                output_tokens=2500,
                reasoning_tokens=1200,
            )
        ],
    )
    provider = _provider(responses)
    repository = tmp_path / "repository"
    repository.mkdir()
    runner = Gate2BackgroundCalibrationRunner(
        repository_root=repository,
        budget_guard=Gate2CalibrationBudgetGuard(
            declared_account_balance_usd=Decimal("9"),
            required_reserve_usd=Decimal("7"),
            authorized_spend_usd=Decimal("0.45"),
        ),
    )
    result = runner.run(
        build_stage_c1_request(
            VISIBLE_CALIBRATION_CASES[0],
            ExperimentArm.B,
        ),
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )
    assert result.status is DryRunStatus.VALIDATED
    assert result.evidence_record.response_id == "resp-stage-c1-test"
    assert result.evidence_record.api_status == "completed"
    assert result.evidence_record.background_mode is True
    assert result.evidence_record.poll_count == 1
    assert result.evidence_record.usage.reasoning_tokens == 1200
    assert result.evidence_record.cost_usd == 0.095925


def test_background_runner_preserves_incomplete_usage_and_response_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [
            _response(
                "incomplete",
                output_tokens=10_000,
                reasoning_tokens=9_500,
                incomplete_reason="max_output_tokens",
            )
        ],
    )
    provider = _provider(responses)
    repository = tmp_path / "repository"
    repository.mkdir()
    runner = Gate2BackgroundCalibrationRunner(
        repository_root=repository,
        budget_guard=Gate2CalibrationBudgetGuard(
            declared_account_balance_usd=Decimal("9"),
            required_reserve_usd=Decimal("7"),
            authorized_spend_usd=Decimal("0.45"),
        ),
    )
    result = runner.run(
        build_stage_c1_request(
            VISIBLE_CALIBRATION_CASES[0],
            ExperimentArm.B,
        ),
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )
    assert result.status is DryRunStatus.PROVIDER_FAILED
    assert result.evidence_record.response_id == "resp-stage-c1-test"
    assert result.evidence_record.api_status == "incomplete"
    assert result.evidence_record.incomplete_reason == "max_output_tokens"
    assert result.evidence_record.usage.output_tokens == 10_000
    assert result.evidence_record.cost_usd == 0.320925
    assert result.evidence_record.background_mode is True
    assert {failure.code for failure in result.validation.hard_failures} == {
        "response_incomplete"
    }


def test_checkpoint_failure_preserves_response_id_without_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeBackgroundResponses(
        _response("queued"),
        [_response("completed", output=_output_dict(), output_tokens=1000)],
    )

    def fail_checkpoint(_: Gate2BackgroundCheckpoint) -> None:
        raise OSError("simulated-write-failure")

    provider = OpenAIGate2BackgroundProvider(
        client_factory=lambda **kwargs: _FakeClient(responses),
        sleep_fn=lambda _: None,
        on_checkpoint=fail_checkpoint,
    )
    with pytest.raises(Gate2LiveProviderError) as captured:
        provider.generate(_prompt())
    assert captured.value.code == "checkpoint_write_failed"
    assert captured.value.response_id == "resp-stage-c1-test"
    assert provider.call_count == 1
    assert responses.parse_calls == 1
    assert responses.retrieve_calls == 0


def test_real_sdk_background_parse_and_retrieve_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    output = _output_dict()
    requests: list[tuple[str, str]] = []

    def response_body(status: str) -> dict[str, object]:
        completed = status == "completed"
        return {
            "id": "resp-stage-c1-test",
            "object": "response",
            "created_at": int(time.time()),
            "status": status,
            "completed_at": int(time.time()) if completed else None,
            "background": True,
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": 10_000,
            "model": "gpt-5.6-sol",
            "output": (
                [
                    {
                        "id": "msg-stage-c1-test",
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
            "reasoning": {"effort": "medium", "summary": None},
            "store": False,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "usage": (
                {
                    "input_tokens": 4185,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 2500,
                    "output_tokens_details": {"reasoning_tokens": 1200},
                    "total_tokens": 6685,
                }
                if completed
                else None
            ),
        }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST":
            payload = json.loads(request.content)
            assert payload["background"] is True
            assert payload["store"] is False
            assert payload["reasoning"] == {"effort": "medium"}
            assert payload["max_output_tokens"] == 10_000
            assert payload["text"]["format"]["type"] == "json_schema"
            return httpx.Response(200, json=response_body("queued"), request=request)
        return httpx.Response(200, json=response_body("completed"), request=request)

    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs):
        return OpenAI(
            api_key="test-only-placeholder",
            http_client=httpx.Client(transport=transport),
            max_retries=0,
        )

    provider = OpenAIGate2BackgroundProvider(
        client_factory=client_factory,
        sleep_fn=lambda _: None,
    )
    result = provider.generate(_prompt())
    assert result.response_id == "resp-stage-c1-test"
    assert result.raw_output == output
    assert requests == [
        ("POST", "/v1/responses"),
        ("GET", "/v1/responses/resp-stage-c1-test"),
    ]
