from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE2_DIR = ROOT / "evals" / "meihua" / "personalization_gate2_v001"
PLAN = GATE2_DIR / "offline_experiment_contract_and_implementation_plan_candidate.md"
README = GATE2_DIR / "README.md"
STATUS = GATE2_DIR / "stage_ab_status.json"
STAGE_C_STATUS = GATE2_DIR / "stage_c_status.json"
STAGE_C_FAILURE = GATE2_DIR / "stage_c_failure_analysis.md"
STAGE_C1_PLAN = GATE2_DIR / "stage_c1_offline_hardening_plan.md"
STAGE_C1_STATUS = GATE2_DIR / "stage_c1_status.json"
STAGE_C1_RESULT = GATE2_DIR / "stage_c1_retest_result.md"
STAGE_C2_PLAN = GATE2_DIR / "stage_c2_offline_contract_plan.md"
STAGE_C2_STATUS = GATE2_DIR / "stage_c2_status.json"
STAGE_C2_AUTHORIZATION_PROPOSAL = (
    GATE2_DIR / "stage_c2_live_retest_authorization_proposal.md"
)
STAGE_C2_RETEST_CONSTRAINTS = GATE2_DIR / "stage_c2_retest_constraints.txt"
STAGE_C2_RETEST_RESULT = GATE2_DIR / "stage_c2_retest_result.md"
STAGE_C3_AUTHORIZATION_PROPOSAL = (
    GATE2_DIR / "stage_c3_visible_chart_arms_authorization_proposal.md"
)
STAGE_C3_STATUS = GATE2_DIR / "stage_c3_status.json"


def test_gate2_contains_only_the_approved_governance_assets() -> None:
    assert {path.name for path in GATE2_DIR.iterdir()} == {
        PLAN.name,
        README.name,
        STATUS.name,
        STAGE_C_STATUS.name,
        STAGE_C_FAILURE.name,
        STAGE_C1_PLAN.name,
        STAGE_C1_STATUS.name,
        STAGE_C1_RESULT.name,
        STAGE_C2_PLAN.name,
        STAGE_C2_STATUS.name,
        STAGE_C2_AUTHORIZATION_PROPOSAL.name,
        STAGE_C2_RETEST_CONSTRAINTS.name,
        STAGE_C2_RETEST_RESULT.name,
        STAGE_C3_AUTHORIZATION_PROPOSAL.name,
        STAGE_C3_STATUS.name,
    }


def test_gate2_plan_records_stage_ab_authorization_and_keeps_live_work_closed() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "APPROVED_STAGE_A_B_IMPLEMENTATION" in text
    assert "本文不创建任何锁定案例" in text
    assert "真实模型调用授权" in text
    assert "API Key配置授权" in text
    assert "正式产品修改授权" in text
    assert "calls_per_result       1" in text
    assert "automatic_model_repair 0" in text
    assert "累计可支出上限为22美元" in text
    assert "不得动用至少7美元的预留余额" in text


def test_gate2_stage_ab_status_keeps_external_and_formal_boundaries_closed() -> None:
    status = __import__("json").loads(STATUS.read_text(encoding="utf-8"))

    assert status["stage_a_authorized"] is True
    assert status["stage_b_authorized"] is True
    assert status["external_model_calls"] == 0
    assert status["api_cost_usd"] == 0
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["next_stage_automatically_authorized"] is False


def test_gate2_stage_c_status_records_narrow_live_authorization() -> None:
    status = __import__("json").loads(STAGE_C_STATUS.read_text(encoding="utf-8"))

    assert status["stage_c_authorized"] is True
    assert status["stage_d_authorized"] is False
    assert status["authorized_spend_usd"] == 2
    assert status["required_reserve_usd"] == 7
    assert status["max_generation_calls"] == 6
    assert status["synthetic_data_only"] is True
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["next_stage_automatically_authorized"] is False
    assert status["external_model_calls"] == 2
    assert status["api_cost_usd"] is None
    assert status["diagnostic_retry_max_generation_calls"] == 1
    assert status["diagnostic_retry_external_model_calls"] == 1
    assert status["diagnostic_retry_automatic_model_repair_calls"] == 0
    assert status["diagnostic_retry_authorized_spend_usd"] == 0.35
    assert status["diagnostic_retry_status"] == "PROVIDER_FAILED_TIMEOUT"


def test_gate2_stage_c1_status_records_narrow_retest_and_keeps_stage_d_closed() -> None:
    status = __import__("json").loads(STAGE_C1_STATUS.read_text(encoding="utf-8"))

    assert status["paid_retest_authorized"] is True
    assert status["paid_retest_authorization_consumed"] is True
    assert status["external_model_calls"] == 1
    assert status["paid_retest_generation_calls"] == 1
    assert status["api_cost_usd"] == 0.136155
    assert status["paid_retest_status"] == "HARD_STOP_PROVIDER_FAILED_SCHEMA_INVALID"
    assert status["maximum_generation_calls_if_later_authorized"] == 1
    assert status["polling_creates_additional_generation"] is False
    assert status["resume_creates_additional_generation"] is False
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["stage_d_authorized"] is False
    assert status["next_stage_automatically_authorized"] is False


def test_gate2_stage_c2_status_is_offline_only_and_keeps_live_work_closed() -> None:
    status = __import__("json").loads(STAGE_C2_STATUS.read_text(encoding="utf-8"))

    assert status["schema_version"] == "gate2_schema_v2"
    assert status["previous_schema_version_preserved"] == "gate2_schema_v1"
    assert status["external_model_calls"] == 1
    assert status["api_cost_usd"] == 0.12798
    assert status["real_retest_authorized"] is True
    assert status["paid_retest_authorization_consumed"] is True
    assert status["authorized_declared_balance_usd"] == 8.71
    assert status["authorized_evidence_directory"].endswith(
        "gate2_personalization_stage_c2_retest_20260721"
    )
    assert status["offline_background_runner_implemented"] is True
    assert status["offline_default_openai_network_client_allowed"] is False
    assert status["offline_wrapped_openai_network_client_allowed"] is False
    assert status["offline_sdk_mock_transport_verified"] is True
    assert status["live_background_provider_implemented"] is True
    assert status["live_background_runner_implemented"] is True
    assert status["paid_entrypoint_implemented"] is True
    assert status["paid_entrypoint_pre_network_authorization_lock"] is True
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["stage_d_authorized"] is False
    assert status["next_stage_automatically_authorized"] is False
    assert status["strict_schema_source_trace_union_branches"] == 4
    assert status["authorization_proposal_created"] is True
    assert status["proposed_max_generation_calls"] == 1
    assert status["proposed_authorized_spend_usd"] == 0.5
    assert status["proposed_conservative_preflight_usd"] == 0.468769
    assert status["proposed_openai_sdk_version"] == "2.46.0"
    assert status["paid_retest_generation_calls"] == 1
    assert status["paid_retest_poll_count"] == 16
    assert status["paid_retest_status"] == "VALIDATED"
    assert status["evidence_manifest_file_count"] == 39
    assert len(status["evidence_manifest_sha256"]) == 64
    assert status["verification_gate2_tests_passed"] == 109
    assert status["verification_full_repository_tests_passed"] == 882


def test_gate2_stage_c2_authorization_proposal_is_exact_and_authorized() -> None:
    text = STAGE_C2_AUTHORIZATION_PROPOSAL.read_text(encoding="utf-8")
    constraints = STAGE_C2_RETEST_CONSTRAINTS.read_text(encoding="utf-8")

    assert "G2CAL-001/B" in text
    assert "最大生成POST：1次" in text
    assert "最大新增费用：0.50美元硬上限" in text
    assert "保守预检为0.468769美元" in text
    assert "所有GET只轮询同一ID" in text
    assert "SDK自动重试：0" in text
    assert "自动模型修复：0" in text
    assert "已授权、已消费" in text
    assert "openai==2.46.0" in constraints


def test_gate2_stage_c2_result_records_single_validated_retest() -> None:
    text = STAGE_C2_RETEST_RESULT.read_text(encoding="utf-8")

    assert "生成POST：1" in text
    assert "轮询GET：16" in text
    assert "自动SDK重试：0" in text
    assert "自动模型修复：0" in text
    assert "本地结果：`VALIDATED`" in text
    assert "0.127980美元" in text
    assert "17个检查点SHA-256全部匹配" in text
    assert "阶段 D：未进入" in text


def test_gate2_stage_c3_status_keeps_real_calls_and_stage_d_closed() -> None:
    status = __import__("json").loads(STAGE_C3_STATUS.read_text(encoding="utf-8"))

    assert status["stage_c3_status"] == "OFFLINE_READY_AWAITING_EXPLICIT_AUTHORIZATION"
    assert status["external_model_calls"] == 0
    assert status["api_cost_usd"] == 0
    assert status["real_visible_chart_arm_run_authorized"] is False
    assert status["candidate_case_id"] == "G2CAL-001"
    assert status["candidate_arms"] == ["C", "D"]
    assert status["candidate_max_generation_calls"] == 2
    assert status["candidate_total_spend_hard_limit_usd"] == 1.0
    assert status["proposed_total_conservative_preflight_usd"] == 0.95062
    assert status["offline_chart_arm_fake_e2e_verified"] is True
    assert status["offline_chart_arm_sdk_mock_transport_verified"] is True
    assert status["paid_entrypoint_implemented"] is True
    assert status["paid_entrypoint_authorized"] is False
    assert status["paid_entrypoint_pre_network_authorization_lock"] is True
    assert status["paid_entrypoint_pre_network_confirmation_lock"] is True
    assert status["paid_entrypoint_sequential_hard_stop_verified"] is True
    assert status["locked_test_set_status"] == "NOT_CREATED_OR_EXPOSED"
    assert status["formal_product_changed"] is False
    assert status["stage_d_authorized"] is False
    assert status["next_stage_automatically_authorized"] is False
    assert status["verification_gate2_tests_passed"] == 133
    assert status["verification_full_repository_tests_passed"] == 906


def test_gate2_stage_c3_proposal_is_minimal_and_requires_new_authorization() -> None:
    text = STAGE_C3_AUTHORIZATION_PROPOSAL.read_text(encoding="utf-8")

    assert "G2CAL-001/C" in text
    assert "G2CAL-001/D" in text
    assert "最大生成POST：2次" in text
    assert "总费用硬上限为1.00美元" in text
    assert "C组任何失败都不得运行D组" in text
    assert "SDK自动重试：0" in text
    assert "自动模型修复：0" in text
    assert "本文件只形成提案，不授权或执行任何真实请求" in text
    assert "不得创建或读取锁定测试集" in text
    assert "不得进入阶段D" in text


def test_gate2_plan_preserves_three_sources_and_four_arms() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for marker in ("REALITY_FACT", "CHART_FACT", "INTERPRETIVE_LINK"):
        assert marker in text
    for trace_field in (
        "trace_id",
        "link_mode",
        "REALITY_ONLY",
        "REALITY_AND_CHART",
        "reality_refs[]",
        "evidence_refs[]",
        "supports_fields[]",
        "interpretation_hypothesis",
    ):
        assert trace_field in text
    assert "B组使用`link_mode=REALITY_ONLY`" in text
    assert "C/D组使用`link_mode=REALITY_AND_CHART`" in text
    assert "`user_facing_reading`的五个字段都必须至少被一条`source_trace.supports_fields[]`覆盖" in text
    for arm in ("| A |", "| B |", "| C |", "| D |"):
        assert arm in text
    assert "question_text_used_for_calculation = false" in text
    assert "question_text_used_for_interpretation = true" in text


def test_gate2_plan_names_formal_systems_that_stay_unchanged() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for boundary in (
        "确定性排盘引擎",
        "正式网站和视觉v16",
        "V3接口与当前确定性报告",
        "meihua_interpretation_v1.txt",
        "InterpretationValidator",
        "Narrative Release Gate",
    ):
        assert boundary in text
