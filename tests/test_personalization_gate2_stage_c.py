from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx
from openai import OpenAI

from abalo_iching.personalization_gate2.budget import (
    Gate2BudgetError,
    Gate2CalibrationBudgetGuard,
)
from abalo_iching.personalization_gate2.calibration_cases import (
    VISIBLE_CALIBRATION_CASES,
    build_manifest,
    build_request,
)
from abalo_iching.personalization_gate2.live_provider import OpenAIGate2Provider
from abalo_iching.personalization_gate2.live_runner import Gate2CalibrationRunner
from abalo_iching.personalization_gate2.models import (
    DryRunStatus,
    ExperimentArm,
    Gate2ExperimentOutput,
    Gate2Usage,
)
from abalo_iching.personalization_gate2.pricing import Gate2TokenPricing
from abalo_iching.personalization_gate2.calibration_prompt_builder import (
    Gate2CalibrationPromptBuilder,
)
from scripts.run_personalization_gate2_stage_c_diagnostic_retry import (
    AUTHORIZED_SPEND_USD as DIAGNOSTIC_RETRY_BUDGET_USD,
    EXPECTED_GENERATION_CALLS as DIAGNOSTIC_RETRY_CALLS,
)


ROOT = Path(__file__).resolve().parents[1]


def _output_dict(*, unsafe: bool = False) -> dict[str, object]:
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
            "text": (
                "对方内心一定反对。"
                if unsafe
                else "关键是让最终负责人形成可观察的正式回应。"
            ),
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


class _FakeResponses:
    def __init__(self, output: dict[str, object], *, incomplete: bool = False) -> None:
        self.output = output
        self.incomplete = incomplete
        self.calls = 0

    def parse(self, **kwargs):
        self.calls += 1
        parsed = Gate2ExperimentOutput.model_validate(self.output)
        return SimpleNamespace(
            status="incomplete" if self.incomplete else "completed",
            output_parsed=parsed,
            output_text=json.dumps(self.output, ensure_ascii=False),
            output=[],
            usage=SimpleNamespace(
                input_tokens=1200,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=0,
                    cache_write_tokens=0,
                ),
                output_tokens=800,
                output_tokens_details=SimpleNamespace(reasoning_tokens=300),
                total_tokens=2000,
            ),
            id="resp-stage-c-test",
            model="gpt-5.6-sol",
        )


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses


def _provider(responses: _FakeResponses) -> OpenAIGate2Provider:
    return OpenAIGate2Provider(
        client_factory=lambda **kwargs: _FakeClient(responses)
    )


def _budget() -> Gate2CalibrationBudgetGuard:
    return Gate2CalibrationBudgetGuard(
        declared_account_balance_usd=Decimal("9"),
        authorized_spend_usd=Decimal("2"),
        required_reserve_usd=Decimal("7"),
    )


def test_stage_c_budget_preserves_seven_dollar_reserve() -> None:
    with pytest.raises(Gate2BudgetError, match="预留"):
        Gate2CalibrationBudgetGuard(
            declared_account_balance_usd=Decimal("9"),
            authorized_spend_usd=Decimal("2.01"),
        )
    guard = _budget()
    guard.authorize(Decimal("1.99"))
    with pytest.raises(Gate2BudgetError, match="硬上限"):
        guard.authorize(Decimal("2.01"))


def test_gpt_5_6_sol_pricing_uses_current_standard_rates() -> None:
    pricing = Gate2TokenPricing()
    usage = Gate2Usage(
        input_tokens=1000,
        cached_input_tokens=100,
        cache_write_tokens=200,
        output_tokens=500,
        total_tokens=1500,
    )
    assert pricing.calculate(usage) == Decimal("0.019800")


def test_visible_calibration_manifest_freezes_two_cases_and_no_locked_payload() -> None:
    manifest = build_manifest()
    assert len(manifest.entries) == 2
    assert manifest.locked_payload_included is False
    assert all(entry.arm_order == tuple(ExperimentArm) for entry in manifest.entries)
    assert all(
        entry.real_chart_mapping_id != entry.mismatched_chart_mapping_id
        for entry in manifest.entries
    )


def test_all_six_calls_fit_two_dollar_conservative_preflight_ceiling() -> None:
    provider = OpenAIGate2Provider()
    builder = Gate2CalibrationPromptBuilder()
    estimates = [
        provider.pricing.conservative_preflight_estimate(
            builder.build(build_request(case, arm)),
            max_output_tokens=provider.max_output_tokens,
        )
        for case in VISIBLE_CALIBRATION_CASES
        for arm in (ExperimentArm.B, ExperimentArm.C, ExperimentArm.D)
    ]
    assert len(estimates) == 6
    assert sum(estimates, Decimal("0")) <= Decimal("2")


def test_diagnostic_retry_is_limited_to_one_call_and_35_cents() -> None:
    provider = OpenAIGate2Provider()
    request = build_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    prompt = Gate2CalibrationPromptBuilder().build(request)
    estimate = provider.pricing.conservative_preflight_estimate(
        prompt,
        max_output_tokens=provider.max_output_tokens,
    )
    assert DIAGNOSTIC_RETRY_CALLS == 1
    assert DIAGNOSTIC_RETRY_BUDGET_USD == Decimal("0.35")
    assert estimate <= DIAGNOSTIC_RETRY_BUDGET_USD


def test_live_runner_calls_once_and_writes_external_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeResponses(_output_dict())
    provider = _provider(responses)
    simulated_repository = tmp_path / "repository"
    simulated_repository.mkdir()
    result = Gate2CalibrationRunner(
        repository_root=simulated_repository,
        budget_guard=_budget(),
    ).run(
        build_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B),
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )
    assert result.status is DryRunStatus.VALIDATED
    assert provider.call_count == 1
    assert responses.calls == 1
    assert result.evidence_record.response_id == "resp-stage-c-test"
    assert result.evidence_record.cost_usd == 0.03
    assert result.evidence_record.human_review == {
        "status": "PENDING",
        "reviewer": None,
        "scores": None,
        "notes": None,
    }


def test_first_hard_failure_is_preserved_without_model_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeResponses(_output_dict(unsafe=True))
    provider = _provider(responses)
    simulated_repository = tmp_path / "repository"
    simulated_repository.mkdir()
    result = Gate2CalibrationRunner(
        repository_root=simulated_repository,
        budget_guard=_budget(),
    ).run(
        build_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B),
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )
    assert result.status is DryRunStatus.FAILED_VALIDATION
    assert provider.call_count == 1
    assert "mind_reading" in {
        failure.code for failure in result.validation.hard_failures
    }
    assert result.evidence_record.first_raw_output["core_conflict"]["text"] == "对方内心一定反对。"


def test_incomplete_response_is_recorded_and_not_retried(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    responses = _FakeResponses(_output_dict(), incomplete=True)
    provider = _provider(responses)
    simulated_repository = tmp_path / "repository"
    simulated_repository.mkdir()
    result = Gate2CalibrationRunner(
        repository_root=simulated_repository,
        budget_guard=_budget(),
    ).run(
        build_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B),
        provider=provider,
        evidence_root=tmp_path / "external-evidence",
    )
    assert result.status is DryRunStatus.PROVIDER_FAILED
    assert provider.call_count == 1
    assert responses.calls == 1
    assert result.evidence_record.first_raw_output is None
    assert result.evidence_record.cost_usd is None
    assert {failure.code for failure in result.validation.hard_failures} == {
        "response_incomplete"
    }


def test_real_openai_sdk_parse_path_accepts_valid_gate2_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    output = _output_dict()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-sol"
        assert payload["store"] is False
        assert payload["tools"] == []
        assert payload["reasoning"]["effort"] == "xhigh"
        body = {
            "id": "resp-sdk-parse-test",
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "completed_at": int(time.time()),
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": 6000,
            "model": "gpt-5.6-sol",
            "output": [
                {
                    "id": "msg-sdk-parse-test",
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
            ],
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {"effort": "xhigh", "summary": None},
            "store": False,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "usage": {
                "input_tokens": 1200,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 800,
                "output_tokens_details": {"reasoning_tokens": 300},
                "total_tokens": 2000,
            },
        }
        return httpx.Response(200, json=body, request=request)

    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs):
        return OpenAI(
            api_key="test-only-placeholder",
            http_client=httpx.Client(transport=transport),
            max_retries=0,
        )

    provider = OpenAIGate2Provider(client_factory=client_factory)
    prompt = Gate2CalibrationPromptBuilder().build(
        build_request(VISIBLE_CALIBRATION_CASES[0], ExperimentArm.B)
    )
    result = provider.generate(prompt)
    assert result.response_id == "resp-sdk-parse-test"
    assert result.raw_output == output
    assert result.usage.total_tokens == 2000
