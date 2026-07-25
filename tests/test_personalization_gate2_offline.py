from __future__ import annotations

import hashlib
import json
from tempfile import TemporaryDirectory
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from abalo_iching.personalization_gate2.budget import Gate2BudgetError, Gate2BudgetGuard
from abalo_iching.personalization_gate2.evidence import Gate2EvidenceWriter
from abalo_iching.personalization_gate2.fake_provider import FakeGate2Provider
from abalo_iching.personalization_gate2.models import (
    DatasetRole,
    DryRunStatus,
    ExperimentArm,
    ExperimentRunManifest,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    RunManifestEntry,
)
from abalo_iching.personalization_gate2.prompt_builder import Gate2PromptBuilder
from abalo_iching.personalization_gate2.runner import Gate2ExecutionBlocked, Gate2OfflineRunner
from abalo_iching.personalization_gate2.validators import Gate2ExperimentValidator


ROOT = Path(__file__).resolve().parents[1]


def _request_dict(arm: ExperimentArm, *, dataset_role: DatasetRole = DatasetRole.CALIBRATION) -> dict:
    is_baseline = arm is ExperimentArm.A
    chart_context = None
    if arm in (ExperimentArm.C, ExperimentArm.D):
        chart_context = {
            "chart_mapping_id": "CHART-TRUE" if arm is ExperimentArm.C else "CHART-MISMATCH",
            "is_mismatched_control": arm is ExperimentArm.D,
            "evidence": [
                {
                    "ref": "EV01",
                    "canonical_evidence_id": "meihua.synthetic.EV01",
                    "text": "合成盘面显示变化发生在起始阶段。",
                    "knowledge_review_status": "CANONICAL_ONLY",
                }
            ],
        }
    return {
        "metadata": {
            "case_id": "SYN-001",
            "arm": arm.value,
            "dataset_role": dataset_role.value,
            "contract_version": "gate2_contract_v1",
            "prompt_version": "NOT_APPLICABLE" if is_baseline else "personalization_gate2_offline_v2",
            "schema_version": "gate2_schema_v1",
            "validator_version": "personalization_gate2_validator_v2",
            "model": "NOT_APPLICABLE" if is_baseline else "fake-structured-model",
            "reasoning_effort": "NOT_APPLICABLE" if is_baseline else "FAKE",
            "max_output_tokens": 1800,
            "store": False,
            "tools": [],
        },
        "reality": {
            "synthetic_data_confirmed": True,
            "question_text": "我已经准备了一段时间，是否应该正式提出这个方案？",
            "question_domain": "工作",
            "decision_goal": "判断现在应继续准备还是正式提出方案",
            "explicit_facts": [
                {"ref": "RW01", "text": "方案的核心材料已经完成。"},
                {"ref": "RW02", "text": "有决定权的人还没有正式看过方案。"},
            ],
            "unknowns": [{"text": "对方最终是否会批准方案。"}],
            "options": [],
            "hard_constraints": [],
            "actions_already_taken": [],
            "observable_responses": [],
        },
        "chart_context": chart_context,
        "deterministic_v16_output": "先做最小可逆行动并观察反馈。" if is_baseline else None,
        "question_text_used_for_calculation": False,
        "question_text_used_for_interpretation": True,
    }


def _output_dict(arm: ExperimentArm) -> dict:
    chart_arm = arm in (ExperimentArm.C, ExperimentArm.D)
    evidence_refs = ["EV01"] if chart_arm else []
    link_mode = "REALITY_AND_CHART" if chart_arm else "REALITY_ONLY"
    source_trace = [
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
    ]
    if chart_arm:
        source_trace.append(
            {
                "trace_id": "EV01",
                "source_kind": "CHART_FACT",
                "source_ref": "EV01",
                "supports_fields": ["chart_signals[0]"],
                "link_mode": "NOT_APPLICABLE",
                "reality_refs": [],
                "evidence_refs": [],
                "interpretation_hypothesis": False,
            }
        )
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
            "link_mode": link_mode,
            "reality_refs": ["RW01", "RW02"],
            "evidence_refs": evidence_refs,
            "interpretation_hypothesis": True,
        }
    )
    return {
        "context_facts": [
            {"fact_text": "方案的核心材料已经完成。", "reality_refs": ["RW01"]},
            {"fact_text": "有决定权的人还没有正式看过方案。", "reality_refs": ["RW02"]},
        ],
        "unknowns": [
            {"unknown_text": "对方最终是否会批准方案。", "must_not_infer": True}
        ],
        "chart_signals": ([{
            "signal_text": "变化处在起始阶段，重点是把准备转成正式动作。",
            "evidence_refs": ["EV01"],
            "knowledge_review_status": "CANONICAL_ONLY",
        }] if chart_arm else []),
        "core_conflict": {
            "text": "问题已经不是材料是否齐全，而是是否让决策者正式回应。",
            "reality_refs": ["RW01", "RW02"],
            "evidence_refs": evidence_refs,
            "interpretation_hypothesis": True,
        },
        "judgment_signature": {
            "direction": "推进", "method": "澄清", "agency": "在用户",
            "main_conflict": "回应", "action_intensity": "中",
        },
        "opposite_posture_and_reason": {
            "opposite_posture": "继续独自准备",
            "reason": "材料已经完成，继续准备不会回答决策者是否支持。",
            "reality_refs": ["RW01", "RW02"], "evidence_refs": evidence_refs,
        },
        "one_action": {
            "action_text": "约一次正式沟通并提交完整方案。",
            "target_or_person": "有决定权的人",
            "observable_result": "对方明确下一步、补充条件或拒绝理由。",
            "reality_refs": ["RW01", "RW02"], "evidence_refs": evidence_refs,
        },
        "switch_conditions": [{
            "condition_text": "若对方提出明确补充条件，就转为补齐条件后再推进。",
            "reality_refs": ["RW02"], "evidence_refs": evidence_refs,
        }],
        "source_trace": source_trace,
        "user_facing_reading": {
            "core_judgment": "可以正式提出方案，不必再只在内部准备。",
            "explanation": "现有材料已经足以进入一次正式沟通。",
            "reality_application": "现在缺少的是有决定权者的明确回应。",
            "action": "把完整方案交给有决定权的人，并直接询问下一步。",
            "switch_condition": "若对方提出明确条件，就按条件补齐；若只让你继续等待，则停止额外加码。",
        },
    }


def _request(arm: ExperimentArm, **kwargs) -> Gate2ExperimentRequest:
    return Gate2ExperimentRequest.model_validate(_request_dict(arm, **kwargs))


def _output(arm: ExperimentArm) -> Gate2ExperimentOutput:
    return Gate2ExperimentOutput.model_validate(_output_dict(arm))


def test_contract_accepts_all_four_arms_with_strict_boundaries() -> None:
    for arm in ExperimentArm:
        request = _request(arm)
        assert request.metadata.arm is arm
        assert request.question_text_used_for_calculation is False
        assert request.question_text_used_for_interpretation is True


def test_contract_rejects_chart_payload_in_b_arm() -> None:
    payload = _request_dict(ExperimentArm.B)
    payload["chart_context"] = _request_dict(ExperimentArm.C)["chart_context"]
    with pytest.raises(ValidationError, match="B 组不得携带卦象"):
        Gate2ExperimentRequest.model_validate(payload)


def test_contract_rejects_unexpected_fields() -> None:
    payload = _request_dict(ExperimentArm.B)
    payload["api_key"] = "forbidden"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Gate2ExperimentRequest.model_validate(payload)


def test_source_trace_requires_dual_refs_for_chart_link() -> None:
    payload = _output_dict(ExperimentArm.C)
    payload["source_trace"][-1]["evidence_refs"] = []
    with pytest.raises(ValidationError, match="REALITY_AND_CHART"):
        Gate2ExperimentOutput.model_validate(payload)


@pytest.mark.parametrize("arm", [ExperimentArm.B, ExperimentArm.C, ExperimentArm.D])
def test_validator_accepts_valid_arm_output(arm: ExperimentArm) -> None:
    report = Gate2ExperimentValidator().validate(_request(arm), _output(arm))
    assert report.hard_passed
    assert report.quality_passed


def test_validator_rejects_unknown_evidence_reference() -> None:
    payload = _output_dict(ExperimentArm.C)
    payload["one_action"]["evidence_refs"] = ["EV99"]
    report = Gate2ExperimentValidator().validate(_request(ExperimentArm.C), Gate2ExperimentOutput.model_validate(payload))
    assert "unknown_evidence_ref" in {failure.code for failure in report.hard_failures}


def test_validator_rejects_reality_fact_text_not_supported_by_rw_reference() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["context_facts"][0]["fact_text"] = "对方已经正式批准方案。"
    report = Gate2ExperimentValidator().validate(
        _request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload)
    )
    assert "reality_fact_text_mismatch" in {failure.code for failure in report.hard_failures}


def test_validator_scans_hard_safety_terms_and_dates_across_full_output() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["core_conflict"]["text"] = "对方内心一定反对，并应在2026-08-09行动。"
    report = Gate2ExperimentValidator().validate(
        _request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload)
    )
    codes = {failure.code for failure in report.hard_failures}
    assert "mind_reading" in codes
    assert "generated_specific_date" in codes


def test_validator_rejects_unreferenced_unknown_source_and_field_path() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["source_trace"].insert(0, {
        "trace_id": "RW99",
        "source_kind": "REALITY_FACT",
        "source_ref": "RW99",
        "supports_fields": ["invented.path"],
        "link_mode": "NOT_APPLICABLE",
        "reality_refs": [],
        "evidence_refs": [],
        "interpretation_hypothesis": False,
    })
    report = Gate2ExperimentValidator().validate(
        _request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload)
    )
    codes = {failure.code for failure in report.hard_failures}
    assert "unknown_reality_ref" in codes
    assert "unknown_supported_field" in codes


def test_validator_rejects_chart_language_in_b_arm() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["user_facing_reading"]["explanation"] = "本卦说明应该推进。"
    report = Gate2ExperimentValidator().validate(_request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload))
    assert "b_arm_traditional_content" in {failure.code for failure in report.hard_failures}


def test_validator_rejects_fabricated_knowledge_review_status() -> None:
    payload = _output_dict(ExperimentArm.C)
    payload["chart_signals"][0]["knowledge_review_status"] = "APPROVED"
    report = Gate2ExperimentValidator().validate(
        _request(ExperimentArm.C), Gate2ExperimentOutput.model_validate(payload)
    )
    assert "knowledge_status_mismatch" in {failure.code for failure in report.hard_failures}


def test_validator_requires_final_field_source_coverage() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["source_trace"][-1]["supports_fields"].remove("user_facing_reading.action")
    report = Gate2ExperimentValidator().validate(_request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload))
    assert "missing_final_field_trace" in {failure.code for failure in report.hard_failures}


def test_validator_keeps_quality_failure_separate_from_hard_safety() -> None:
    payload = _output_dict(ExperimentArm.B)
    payload["user_facing_reading"]["action"] = "做一个最小可逆行动，收集反馈。"
    report = Gate2ExperimentValidator().validate(_request(ExperimentArm.B), Gate2ExperimentOutput.model_validate(payload))
    assert report.hard_passed
    assert {failure.code for failure in report.quality_failures} == {"generic_default_posture"}


def test_validator_records_cross_arm_collapse_as_quality_failure() -> None:
    output = _output(ExperimentArm.C)
    failures = Gate2ExperimentValidator().validate_arm_set({
        ExperimentArm.B: output, ExperimentArm.C: output, ExperimentArm.D: output,
    })
    assert {failure.code for failure in failures} == {"judgment_signature_collapsed", "action_collapsed"}


def test_prompt_builder_excludes_chart_from_b_and_includes_schema() -> None:
    package = Gate2PromptBuilder().build(_request(ExperimentArm.B))
    assert package.input_payload["chart_context"] is None
    assert package.input_payload["allowed_evidence_refs"] == []
    assert "properties" in package.input_payload["output_schema"]
    assert len(package.prompt_sha256) == 64


def test_prompt_builder_exposes_only_short_evidence_refs_not_canonical_ids() -> None:
    package = Gate2PromptBuilder().build(_request(ExperimentArm.C))
    serialized = json.dumps(package.input_payload, ensure_ascii=False)
    assert "EV01" in serialized
    assert "meihua.synthetic.EV01" not in serialized


def test_budget_guard_allows_only_zero_cost_fake_provider() -> None:
    guard = Gate2BudgetGuard()
    guard.authorize(provider_name="FAKE", estimated_cost_usd=Decimal("0"))
    guard.record_actual_cost(Decimal("0"))
    with pytest.raises(Gate2BudgetError, match="真实模型"):
        guard.authorize(provider_name="OPENAI", estimated_cost_usd=Decimal("0"))
    with pytest.raises(Gate2BudgetError, match="零美元"):
        guard.authorize(provider_name="FAKE", estimated_cost_usd=Decimal("0.01"))


def test_fake_runner_calls_once_and_writes_verifiable_external_evidence() -> None:
    with TemporaryDirectory(prefix="gate2-test-", dir=ROOT) as temp_dir:
        sandbox = Path(temp_dir)
        simulated_repository = sandbox / "simulated-repository"
        provider = FakeGate2Provider([_output_dict(ExperimentArm.C)])
        result = Gate2OfflineRunner(repository_root=simulated_repository).run(
            _request(ExperimentArm.C),
            provider=provider,
            evidence_root=sandbox / "external-evidence",
        )
        assert result.status is DryRunStatus.VALIDATED
        assert provider.call_count == 1
        assert result.evidence_record.cost_usd == 0
        assert result.evidence_record.evidence_reference_map == {
            "EV01": "meihua.synthetic.EV01"
        }
        assert len(result.evidence_record.schema_sha256) == 64
        assert len(result.evidence_record.validator_sha256) == 64
        run_dir = Path(result.evidence_directory or "")
        record_bytes = (run_dir / "run_record.json").read_bytes()
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert b"\r\n" not in record_bytes
        assert manifest["files"]["run_record.json"]["sha256"] == hashlib.sha256(record_bytes).hexdigest()


@pytest.mark.parametrize("arm", [ExperimentArm.B, ExperimentArm.C, ExperimentArm.D])
def test_fake_runner_completes_each_model_arm_with_one_zero_cost_call(arm: ExperimentArm) -> None:
    provider = FakeGate2Provider([_output_dict(arm)])
    result = Gate2OfflineRunner(repository_root=ROOT).run(_request(arm), provider=provider)
    assert result.status is DryRunStatus.VALIDATED
    assert provider.call_count == 1
    assert result.evidence_record.usage.total_tokens == 0
    assert result.evidence_record.cost_usd == 0


def test_runner_hard_stops_if_fake_provider_reports_nonzero_cost() -> None:
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    original_generate = provider.generate
    provider.generate = lambda prompt: original_generate(prompt).model_copy(
        update={"cost_usd": 0.01}
    )
    with pytest.raises(Gate2BudgetError, match="零美元"):
        Gate2OfflineRunner(repository_root=ROOT).run(_request(ExperimentArm.B), provider=provider)
    assert provider.call_count == 1


def test_runner_rejects_reconfigured_budget_guard_before_provider_call() -> None:
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    guard = Gate2BudgetGuard(
        authorized_spend_usd=Decimal("1"),
        live_model_calls_authorized=True,
    )
    with pytest.raises(Gate2ExecutionBlocked, match="不得被重新配置"):
        Gate2OfflineRunner(repository_root=ROOT, budget_guard=guard).run(
            _request(ExperimentArm.B), provider=provider
        )
    assert provider.call_count == 0


@pytest.mark.parametrize(
    ("field", "stale_value", "message"),
    [
        ("prompt_version", "personalization_gate2_offline_v1", "Prompt 版本"),
        ("schema_version", "gate2_schema_stale", "Schema 版本"),
        ("validator_version", "personalization_gate2_validator_v1", "Validator 版本"),
    ],
)
def test_runner_rejects_stale_component_coordinates_before_provider_call(
    field: str,
    stale_value: str,
    message: str,
) -> None:
    payload = _request_dict(ExperimentArm.B)
    payload["metadata"][field] = stale_value
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    with pytest.raises(Gate2ExecutionBlocked, match=message):
        Gate2OfflineRunner(repository_root=ROOT).run(
            Gate2ExperimentRequest.model_validate(payload),
            provider=provider,
        )
    assert provider.call_count == 0


def test_schema_failure_preserves_first_raw_output_and_does_not_repair() -> None:
    provider = FakeGate2Provider([{"unexpected": "first output must remain"}])
    result = Gate2OfflineRunner(repository_root=ROOT).run(_request(ExperimentArm.B), provider=provider)
    assert result.status is DryRunStatus.SCHEMA_FAILED
    assert provider.call_count == 1
    assert result.evidence_record.first_raw_output == {"unexpected": "first output must remain"}
    assert {failure.code for failure in result.validation.hard_failures} == {"schema_invalid"}


def test_locked_dataset_is_blocked_before_provider_call() -> None:
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    with pytest.raises(Gate2ExecutionBlocked, match="锁定测试集"):
        Gate2OfflineRunner(repository_root=ROOT).run(_request(ExperimentArm.B, dataset_role=DatasetRole.LOCKED), provider=provider)
    assert provider.call_count == 0


def test_sensitive_input_is_blocked_before_provider_call() -> None:
    payload = _request_dict(ExperimentArm.B)
    payload["reality"]["question_text"] = "请联系 test@example.com 讨论这个真实案例"
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    with pytest.raises(Gate2ExecutionBlocked, match="受保护信息"):
        Gate2OfflineRunner(repository_root=ROOT).run(Gate2ExperimentRequest.model_validate(payload), provider=provider)
    assert provider.call_count == 0


def test_a_baseline_never_calls_provider() -> None:
    result = Gate2OfflineRunner(repository_root=ROOT).run(_request(ExperimentArm.A))
    assert result.status is DryRunStatus.BASELINE
    assert result.evidence_record.provider_name == "NONE"
    assert result.evidence_record.cost_usd == 0


def test_evidence_writer_rejects_repository_directory() -> None:
    provider = FakeGate2Provider([_output_dict(ExperimentArm.B)])
    with pytest.raises(ValueError, match="Git 仓库之外"):
        Gate2OfflineRunner(repository_root=ROOT).run(
            _request(ExperimentArm.B), provider=provider, evidence_root=ROOT / "forbidden-evidence"
        )


def test_case_id_and_evidence_writer_block_absolute_path_escape() -> None:
    payload = _request_dict(ExperimentArm.B)
    payload["metadata"]["case_id"] = str(ROOT / "escaped-evidence")
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        Gate2ExperimentRequest.model_validate(payload)

    with TemporaryDirectory(prefix="gate2-path-test-", dir=ROOT) as temp_dir:
        sandbox = Path(temp_dir)
        simulated_repository = sandbox / "simulated-repository"
        simulated_repository.mkdir()
        result = Gate2OfflineRunner(repository_root=simulated_repository).run(
            _request(ExperimentArm.B),
            provider=FakeGate2Provider([_output_dict(ExperimentArm.B)]),
        )
        escaped_record = result.evidence_record.model_copy(
            update={"case_id": str(simulated_repository / "escaped-evidence")}
        )
        with pytest.raises(ValueError, match="不得逃逸|Git 仓库之外"):
            Gate2EvidenceWriter(repository_root=simulated_repository).write(
                escaped_record,
                sandbox / "external-evidence",
            )


def test_run_manifest_freezes_all_four_arms_once() -> None:
    manifest = ExperimentRunManifest(
        manifest_version="gate2_manifest_v1",
        locked_payload_included=False,
        entries=[RunManifestEntry(
            case_id="SYN-001",
            arm_order=(ExperimentArm.C, ExperimentArm.A, ExperimentArm.D, ExperimentArm.B),
            real_chart_mapping_id="CHART-TRUE",
            mismatched_chart_mapping_id="CHART-MISMATCH",
        )],
    )
    assert manifest.entries[0].arm_order[0] is ExperimentArm.C
    with pytest.raises(ValidationError, match="A/B/C/D"):
        RunManifestEntry(
            case_id="SYN-002",
            arm_order=(ExperimentArm.A,) * 4,
            real_chart_mapping_id="CHART-TRUE",
            mismatched_chart_mapping_id="CHART-MISMATCH",
        )
