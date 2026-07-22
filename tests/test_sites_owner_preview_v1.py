from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_owner_preview_v1 import (
    OWNER_PREVIEW_CONTRACT_VERSION,
    process_sites_owner_preview_v1_request,
)
from abalo_iching.personalization_gate2.models import (
    Gate2ProviderResult,
    Gate2Usage,
)


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
    ev = prompt.input_payload["chart_context"]["evidence"][0]
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
    ]
    return {
        "context_facts": [{"fact_text": rw_text, "reality_refs": [rw_ref]}],
        "unknowns": [
            {"unknown_text": item["text"], "must_not_infer": True}
            for item in reality["unknowns"]
        ],
        "chart_signals": [{
            "signal_text": ev["text"],
            "evidence_refs": [ev["ref"]],
            "knowledge_review_status": ev["knowledge_review_status"],
        }],
        "core_conflict": {"text": "眼前关键不在继续追加投入，而在先取得明确回应。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"]], "interpretation_hypothesis": True},
        "judgment_signature": {"direction": "等待", "method": "澄清", "agency": "双方共同", "main_conflict": "回应", "action_intensity": "中"},
        "opposite_posture_and_reason": {"opposite_posture": "继续追加投入", "reason": "已有回应仍不明确，贸然追加会放大沉没成本。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"]]},
        "one_action": {"action_text": "向最终负责人发出一页确认函，并明确需要答复的两个问题。", "target_or_person": "最终负责人", "observable_result": "收到明确答复，或在约定期限内仍无答复。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"]]},
        "switch_conditions": [{"condition_text": "若收到明确资源与时间承诺，再转为推进。", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"]]}],
        "source_trace": [
            {"trace_id": rw_ref, "source_kind": "REALITY_FACT", "source_ref": rw_ref, "supports_fields": ["context_facts[0].fact_text"], "link_mode": "NOT_APPLICABLE", "reality_refs": [], "evidence_refs": [], "interpretation_hypothesis": False},
            {"trace_id": ev["ref"], "source_kind": "CHART_FACT", "source_ref": ev["ref"], "supports_fields": ["chart_signals[0].signal_text"], "link_mode": "NOT_APPLICABLE", "reality_refs": [], "evidence_refs": [], "interpretation_hypothesis": False},
            {"trace_id": "IL01", "source_kind": "INTERPRETIVE_LINK", "source_ref": "IL01", "supports_fields": required, "link_mode": "REALITY_AND_CHART", "reality_refs": [rw_ref], "evidence_refs": [ev["ref"]], "interpretation_hypothesis": True},
        ],
        "user_facing_reading": {
            "core_judgment": "先不要追加投入，先把决定权和答复期限问到明处。",
            "explanation": "目前最重要的缺口是最终负责人的明确回应。卦象只提供观察角度，不能替代这份现实答复。",
            "reality_application": "把本周视为一次确认窗口：看对方是否愿意给出资源、负责人和时间。",
            "action": "向最终负责人发送一页确认函，只问资源是否保留、何时作出决定，并记录实际答复。",
            "switch_condition": "若得到明确资源与时间承诺，可以继续；若仍只有口头认可而无安排，应停止追加投入。",
        },
    }


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
    assert response["personalized_reading"]["core_judgment"].startswith("先不要追加投入")
    assert response["preview_meta"]["actual_api_cost_usd"] == 0.035
    assert response["preview_meta"]["hard_cost_limit_enabled"] is False
    assert response["preview_meta"]["preflight_estimated_cost_usd"] > 0
    assert response["preview_meta"]["stored"] is False
    assert response["deterministic_result"]["base_hexagram"]["name"]
    assert "source_trace" not in response
    assert captured[0].input_payload["reality_context"]["data_classification"] == "OWNER_PROVIDED_PRIVATE_PREVIEW"
    assert "synthetic_only" not in str(captured[0].input_payload)
    assert captured[0].prompt_version == "guanxiang_owner_preview_v2"
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
    assert response["preview_meta"]["hard_cost_limit_enabled"] is False


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
    assert response["preview_meta"]["hard_cost_limit_enabled"] is False
    assert calls == 1
