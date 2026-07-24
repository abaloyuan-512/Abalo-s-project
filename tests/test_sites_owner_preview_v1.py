from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application.sites_owner_preview_v1 import (
    OWNER_PREVIEW_CONTRACT_VERSION,
    OWNER_PREVIEW_MAX_POLL_ATTEMPTS,
    _live_generator,
    process_sites_owner_preview_v1_request,
)
from abalo_iching.personalization_gate2.background_provider import (
    OpenAIGate2BackgroundProvider,
)
from abalo_iching.personalization_gate2.models import (
    Gate2ProviderResult,
    Gate2Usage,
)
from abalo_iching.personalization_gate2.live_provider import Gate2LiveProviderError


FIXED_NOW = datetime(2026, 7, 22, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def request(**changes):
    payload = {
        "contract_version": OWNER_PREVIEW_CONTRACT_VERSION,
        "request_id": "owner-preview-test",
        "question_text": "这次合作已经反复推迟，我还应该继续投入吗？",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "decision_stage": "ALREADY_ACTING",
        "key_uncertainty": "OTHER_RESPONSE",
        "decision_risk_profile": "STANDARD",
        "confirmed_facts": ["双方已经沟通过两次。", "本周需要决定是否继续预留资源。"],
        "unknowns": ["不知道最终负责人是否已经看过方案。"],
        "options": [],
        "actions_already_taken": ["已经发送一页方案摘要。"],
        "observable_responses": ["直属负责人认可方向，但没有给出时间。"],
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-22T13:58:00+08:00",
        "user_acknowledgements": {
            "owner_preview_only": True,
            "live_model_cost_acknowledged": True,
            "no_formal_persistence": True,
            "user_statements_not_verified_facts": True,
        },
    }
    payload.update(changes)
    return payload


def valid_output(prompt):
    reality = prompt.input_payload["reality_context"]
    rw_ref = reality["explicit_facts"][0]["ref"]
    rw_text = reality["explicit_facts"][0]["text"]
    ev = next(
        item
        for item in prompt.input_payload["chart_context"]["evidence"]
        if item["ref"] == "EV10"
    )
    change_ev = next(
        item
        for item in prompt.input_payload["chart_context"]["evidence"]
        if item["ref"] == "EV13"
    )
    required = [
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
        "core_conflict.text",
        "opposite_posture_and_reason.reason",
        "one_action.action_text",
        "switch_conditions[0].condition_text",
        "user_facing_reading.question_responses[0].answer_text",
    ]
    return {
        "context_facts": [{"fact_text": rw_text, "reality_refs": [rw_ref]}],
        "unknowns": [
            {"unknown_text": item["text"], "must_not_infer": True}
            for item in reality["unknowns"]
        ],
        "chart_signals": [
            {
                "signal_text": ev["text"],
                "evidence_refs": [ev["ref"]],
                "knowledge_review_status": ev["knowledge_review_status"],
            },
            {
                "signal_text": change_ev["text"],
                "evidence_refs": [change_ev["ref"]],
                "knowledge_review_status": change_ev["knowledge_review_status"],
            },
        ],
        "core_conflict": {"text": "眼前关键不在继续追加投入，而在先取得明确回应。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"], change_ev["ref"]], "interpretation_hypothesis": True},
        "judgment_signature": {"direction": "等待", "method": "澄清", "agency": "双方共同", "main_conflict": "回应", "action_intensity": "中"},
        "opposite_posture_and_reason": {"opposite_posture": "继续追加投入", "reason": "已有回应仍不明确，贸然追加会放大沉没成本。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"], change_ev["ref"]]},
        "one_action": {"action_text": "向最终负责人发出一页确认函，并明确需要答复的两个问题。", "target_or_person": "最终负责人", "observable_result": "收到明确答复，或在约定期限内仍无答复。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"], change_ev["ref"]]},
        "switch_conditions": [{"condition_text": "若收到明确资源与时间承诺，再转为推进。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"], change_ev["ref"]]}],
        "source_trace": [
            {"trace_id": rw_ref, "source_kind": "REALITY_FACT", "source_ref": rw_ref, "supports_fields": ["context_facts[0].fact_text"], "link_mode": "NOT_APPLICABLE", "reality_refs": [], "evidence_refs": [], "interpretation_hypothesis": False},
            {"trace_id": ev["ref"], "source_kind": "CHART_FACT", "source_ref": ev["ref"], "supports_fields": ["chart_signals[0].signal_text"], "link_mode": "NOT_APPLICABLE", "reality_refs": [], "evidence_refs": [], "interpretation_hypothesis": False},
            {"trace_id": change_ev["ref"], "source_kind": "CHART_FACT", "source_ref": change_ev["ref"], "supports_fields": ["chart_signals[1].signal_text"], "link_mode": "NOT_APPLICABLE", "reality_refs": [], "evidence_refs": [], "interpretation_hypothesis": False},
            {"trace_id": "IL01", "source_kind": "INTERPRETIVE_LINK", "source_ref": "IL01", "supports_fields": required, "link_mode": "REALITY_AND_CHART", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"], change_ev["ref"]], "interpretation_hypothesis": True},
        ],
        "user_facing_reading": {
            "core_judgment": "先不要追加投入，先把决定权和答复期限问到明处。",
            "explanation": "目前最重要的缺口是最终负责人的明确回应。卦象只提供观察角度，不能替代这份现实答复。",
            "reality_application": "把本周视为一次确认窗口：看对方是否愿意给出资源、负责人和时间。",
            "action": "向最终负责人发送一页确认函，只问资源是否保留、何时作出决定，并记录实际答复。",
            "switch_condition": "若得到明确资源与时间承诺，可以继续；若仍只有口头认可而无安排，应停止追加投入。",
            "question_responses": [{
                "question_text": prompt.input_payload["question_clauses"][0],
                "answer_text": "可以先取得明确回应，但不要在答复前追加投入。",
            }],
        },
    }


def test_live_generator_waits_for_same_response_for_up_to_six_minutes(monkeypatch):
    captured = {}
    sentinel = object()

    def fake_init(self, **kwargs):
        captured.update(kwargs)

    def fake_generate(self, prompt):
        captured["prompt"] = prompt
        return sentinel

    monkeypatch.setattr(OpenAIGate2BackgroundProvider, "__init__", fake_init)
    monkeypatch.setattr(OpenAIGate2BackgroundProvider, "generate", fake_generate)

    prompt = object()
    assert _live_generator(prompt) is sentinel
    assert captured["prompt"] is prompt
    assert captured["max_poll_attempts"] == OWNER_PREVIEW_MAX_POLL_ATTEMPTS == 180


def test_owner_preview_is_disabled_by_default_without_calling_openai(monkeypatch):
    monkeypatch.delenv("ABALO_OWNER_PREVIEW_ENABLED", raising=False)
    response = process_sites_owner_preview_v1_request(request(), clock=lambda: FIXED_NOW)
    assert response["status"] == "PREVIEW_DISABLED"
    assert response["personalized_reading"] is None
    assert response["preview_meta"]["formal_persistence_allowed"] is False


def test_owner_preview_generates_once_validates_and_returns_only_user_reading():
    captured = []

    def generator(prompt):
        captured.append(prompt)
        return Gate2ProviderResult(
            response_id="test-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=valid_output(prompt),
            usage=Gate2Usage(input_tokens=1000, output_tokens=1000, total_tokens=2000),
            cost_usd=0.035,
            api_status="completed",
            background_mode=True,
            poll_count=1,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )
    assert response["status"] == "SUCCESS"
    assert len(captured) == 1
    assert response["user_question"] == request()["question_text"]
    assert response["structured_intake"]["question_domain"] == "PROJECT_COOPERATION"
    assert response["personalized_reading"]["core_judgment"].startswith("先不要追加投入")
    assert response["preview_meta"]["actual_api_cost_usd"] == 0.035
    assert response["preview_meta"]["hard_cost_limit_enabled"] is True
    assert response["preview_meta"]["max_preflight_cost_usd"] == 0.5
    assert response["preview_meta"]["preflight_estimated_cost_usd"] > 0
    assert response["preview_meta"]["stored"] is False
    assert response["preview_meta"]["input_unknowns_canonicalized"] is True
    assert response["preview_meta"]["model_unknowns_replaced"] is False
    assert response["deterministic_result"]["base_hexagram"]["name"]
    assert "source_trace" not in response
    assert captured[0].input_payload["reality_context"]["data_classification"] == "OWNER_PROVIDED_PRIVATE_PREVIEW"
    assert "synthetic_only" not in str(captured[0].input_payload)
    assert captured[0].prompt_version == "guanxiang_owner_preview_v6"
    assert captured[0].input_payload["interpretation_packet"]["packet_version"] == "SITES_INTERPRETATION_PACKET_V1"
    assert captured[0].input_payload["interpretation_packet"]["epistemic_boundary"].startswith("PACKET_ITEMS_ARE_CHART")
    assert {item["ref"] for item in captured[0].input_payload["chart_context"]["evidence"]} >= {
        "EV10",
        "EV11",
        "EV12",
        "EV13",
    }
    assert "判断优先与解释资料包使用约束" in captured[0].system_instructions
    assert "最小可逆、低成本验证、收集反馈、保留调整空间" in captured[0].system_instructions
    for field in (
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
    ):
        assert field in captured[0].system_instructions


def test_owner_preview_records_high_actual_cost_without_hard_block():
    def generator(prompt):
        return Gate2ProviderResult(
            response_id="test-high-cost-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=valid_output(prompt),
            usage=Gate2Usage(input_tokens=1000, output_tokens=1000, total_tokens=2000),
            cost_usd=1.25,
            api_status="completed",
            background_mode=True,
            poll_count=1,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "SUCCESS"
    assert response["preview_meta"]["actual_api_cost_usd"] == 1.25
    assert response["preview_meta"]["hard_cost_limit_enabled"] is True


def test_owner_preview_allows_prohibited_phrase_only_inside_verbatim_unknown():
    def generator(prompt):
        return Gate2ProviderResult(
            response_id="test-verbatim-unknown-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=valid_output(prompt),
            usage=Gate2Usage(input_tokens=1000, output_tokens=1000, total_tokens=2000),
            cost_usd=0.035,
            api_status="completed",
            background_mode=True,
            poll_count=1,
        )

    response = process_sites_owner_preview_v1_request(
        request(unknowns=["不知道这次合作是否一定会继续。"]),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "SUCCESS"
    assert response["preview_meta"]["validator_version"] == "guanxiang_owner_preview_validator_v6"


@pytest.mark.parametrize(
    "model_unknowns",
    [
        [],
        [{"unknown_text": "不知道负责人是否已经阅读方案。", "must_not_infer": True}],
    ],
)
def test_owner_preview_restores_input_unknowns_without_retry(model_unknowns):
    calls = 0

    def generator(prompt):
        nonlocal calls
        calls += 1
        output = valid_output(prompt)
        output["unknowns"] = model_unknowns
        return Gate2ProviderResult(
            response_id="test-restored-unknowns-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.035,
            api_status="completed",
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "SUCCESS"
    assert response["preview_meta"]["input_unknowns_canonicalized"] is True
    assert response["preview_meta"]["model_unknowns_replaced"] is True
    assert response["preview_meta"]["automatic_model_repair_calls"] == 0
    assert calls == 1


def test_owner_preview_accepts_exact_aggregate_source_trace_paths_from_live_output():
    def generator(prompt):
        output = valid_output(prompt)
        output["source_trace"][0]["supports_fields"] = ["context_facts"]
        output["source_trace"][1]["supports_fields"] = ["chart_signals"]
        output["source_trace"][-1]["supports_fields"] = [
            "switch_conditions"
            if field == "switch_conditions[0].condition_text"
            else field
            for field in output["source_trace"][-1]["supports_fields"]
        ]
        return Gate2ProviderResult(
            response_id="test-aggregate-trace-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.035,
            api_status="completed",
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "SUCCESS"
    assert response["preview_meta"]["prompt_version"] == "guanxiang_owner_preview_v6"
    assert response["preview_meta"]["validator_version"] == "guanxiang_owner_preview_validator_v6"


def test_owner_preview_rejects_output_that_ignores_interpretation_packet():
    def generator(prompt):
        output = valid_output(prompt)
        ordinary = prompt.input_payload["chart_context"]["evidence"][0]
        change = next(
            item
            for item in prompt.input_payload["chart_context"]["evidence"]
            if item["ref"] == "EV03"
        )
        for signal, replacement in zip(output["chart_signals"], (ordinary, change), strict=True):
            old_ref = signal["evidence_refs"][0]
            signal["signal_text"] = replacement["text"]
            signal["evidence_refs"] = [replacement["ref"]]
            signal["knowledge_review_status"] = replacement["knowledge_review_status"]
            trace = next(item for item in output["source_trace"] if item["source_ref"] == old_ref)
            trace["trace_id"] = replacement["ref"]
            trace["source_ref"] = replacement["ref"]
            for link in output["source_trace"]:
                link["evidence_refs"] = [
                    replacement["ref"] if ref == old_ref else ref
                    for ref in link["evidence_refs"]
                ]
            for section in ("core_conflict", "opposite_posture_and_reason", "one_action"):
                output[section]["evidence_refs"] = [
                    replacement["ref"] if ref == old_ref else ref
                    for ref in output[section]["evidence_refs"]
                ]
            for condition in output["switch_conditions"]:
                condition["evidence_refs"] = [
                    replacement["ref"] if ref == old_ref else ref
                    for ref in condition["evidence_refs"]
                ]
        return Gate2ProviderResult(
            response_id="test-packet-unused",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.01,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    assert "interpretation_packet_unused" in response["preview_meta"]["quality_failure_codes"]


def test_owner_preview_still_rejects_unknown_aggregate_source_trace_path():
    def generator(prompt):
        output = valid_output(prompt)
        output["source_trace"][0]["supports_fields"] = ["context_factz"]
        return Gate2ProviderResult(
            response_id="test-invalid-aggregate-trace-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.035,
            api_status="completed",
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    assert response["preview_meta"]["hard_failure_codes"] == ["unknown_supported_field"]


def test_owner_preview_rejects_missing_unknowns_before_generation():
    called = False

    def generator(_prompt):
        nonlocal called
        called = True
        raise AssertionError("must not generate")

    response = process_sites_owner_preview_v1_request(
        request(unknowns=[]),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )
    assert response["status"] == "VALIDATION_ERROR"
    assert called is False


def test_owner_preview_hard_stops_invalid_model_output_without_retry():
    calls = 0

    def generator(prompt):
        nonlocal calls
        calls += 1
        output = valid_output(prompt)
        output["unknowns"] = []
        output["user_facing_reading"]["action"] = "必须立刻辞职"
        return Gate2ProviderResult(
            response_id="test-response-id",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.035,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )
    assert response["status"] == "PREVIEW_FAILED"
    assert response["personalized_reading"] is None
    assert response["preview_meta"]["actual_api_cost_usd"] == 0.035
    assert response["preview_meta"]["hard_cost_limit_enabled"] is True
    assert response["preview_meta"]["failure_stage"] == "OUTPUT_VALIDATION"
    assert "forced_irreversible_decision" in response["preview_meta"]["hard_failure_codes"]
    assert "unknowns_not_preserved" not in response["preview_meta"]["hard_failure_codes"]
    assert response["preview_meta"]["model_unknowns_replaced"] is True
    assert calls == 1


def test_owner_preview_rejects_unanswered_multi_clause_question():
    def generator(prompt):
        return Gate2ProviderResult(
            response_id="test-question-coverage",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=valid_output(prompt),
            cost_usd=0.01,
        )

    response = process_sites_owner_preview_v1_request(
        request(question_text="能否继续做下去？是否有长期发展？能否得到想要的？"),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    assert "question_coverage_missing" in response["preview_meta"]["quality_failure_codes"]


@pytest.mark.parametrize(
    ("field", "text", "expected_code"),
    [
        ("core_judgment", "信息不足，暂时无法判断。", "non_answer_judgment"),
        ("question_responses", "信息不足，暂时无法判断。", "question_clauses_unanswered"),
        ("action", "先完成一个最小版本，再决定是否继续。", "irreversible_domain_mismatch"),
    ],
)
def test_owner_preview_rejects_new_selfserve_quality_failures(field, text, expected_code):
    def generator(prompt):
        output = valid_output(prompt)
        if field == "question_responses":
            output["user_facing_reading"][field][0]["answer_text"] = text
        else:
            output["user_facing_reading"][field] = text
        return Gate2ProviderResult(
            response_id=f"test-{expected_code}",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.01,
        )

    response = process_sites_owner_preview_v1_request(
        request(decision_risk_profile="HIGH_IRREVERSIBLE"),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    assert expected_code in response["preview_meta"]["quality_failure_codes"]


def test_owner_preview_requires_two_visible_chart_facts_including_change_or_line():
    def generator(prompt):
        output = valid_output(prompt)
        removed_ref = output["chart_signals"][1]["evidence_refs"][0]
        output["chart_signals"] = output["chart_signals"][:1]
        output["source_trace"] = [
            trace for trace in output["source_trace"] if trace["source_ref"] != removed_ref
        ]
        for section in (
            "core_conflict",
            "opposite_posture_and_reason",
            "one_action",
        ):
            output[section]["evidence_refs"] = [
                ref for ref in output[section]["evidence_refs"] if ref != removed_ref
            ]
        for condition in output["switch_conditions"]:
            condition["evidence_refs"] = [
                ref for ref in condition["evidence_refs"] if ref != removed_ref
            ]
        for trace in output["source_trace"]:
            trace["evidence_refs"] = [
                ref for ref in trace["evidence_refs"] if ref != removed_ref
            ]
        return Gate2ProviderResult(
            response_id="test-chart-distinctiveness",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.01,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    codes = response["preview_meta"]["quality_failure_codes"]
    assert "chart_distinctiveness_missing" in codes
    assert "change_or_line_missing" in codes


def test_owner_preview_rejects_question_answer_supported_only_as_input_restatement():
    answer_field = "user_facing_reading.question_responses[0].answer_text"

    def generator(prompt):
        output = valid_output(prompt)
        output["source_trace"][0]["supports_fields"].append(answer_field)
        output["source_trace"][-1]["supports_fields"].remove(answer_field)
        return Gate2ProviderResult(
            response_id="test-input-restatement",
            provider_name="FAKE_OWNER_PREVIEW",
            model="gpt-5.6-sol",
            raw_output=output,
            cost_usd=0.01,
        )

    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_FAILED"
    assert "input_restated_without_insight" in response["preview_meta"]["quality_failure_codes"]


def test_owner_preview_blocks_before_generation_when_preflight_exceeds_limit(monkeypatch):
    called = False

    def generator(_prompt):
        nonlocal called
        called = True
        raise AssertionError("must not generate")

    monkeypatch.setenv("ABALO_OWNER_PREVIEW_MAX_PREFLIGHT_USD", "0.01")
    response = process_sites_owner_preview_v1_request(
        request(),
        generator=generator,
        clock=lambda: FIXED_NOW,
    )

    assert response["status"] == "PREVIEW_BUDGET_BLOCKED"
    assert response["preview_meta"]["hard_cost_limit_enabled"] is True
    assert response["preview_meta"]["max_preflight_cost_usd"] == 0.01
    assert response["preview_meta"]["preflight_estimated_cost_usd"] > 0.01
    assert called is False


def test_owner_preview_records_safe_provider_diagnostics_without_sensitive_payload(caplog):
    def generator(_prompt):
        raise Gate2LiveProviderError(
            "structured_output_schema_invalid",
            "synthetic schema failure",
            response_id="resp-sensitive-raw-id",
            api_status="completed",
            cost_usd=0.123,
            poll_count=7,
            raw_output={"secret": "raw model output"},
        )

    with caplog.at_level("WARNING", logger="abalo.owner_preview"):
        response = process_sites_owner_preview_v1_request(
            request(question_text="这是绝不能进入日志的用户问题。"),
            generator=generator,
            clock=lambda: FIXED_NOW,
        )

    assert response["status"] == "PREVIEW_FAILED"
    assert response["preview_meta"]["failure_codes"] == ["structured_output_schema_invalid"]
    assert response["preview_meta"]["provider_api_status"] == "completed"
    assert response["preview_meta"]["provider_poll_count"] == 7
    assert response["preview_meta"]["actual_api_cost_usd"] == 0.123
    assert "structured_output_schema_invalid" in caplog.text
    assert "resp-sensitive-raw-id" not in caplog.text
    assert "绝不能进入日志" not in caplog.text
    assert "raw model output" not in caplog.text
