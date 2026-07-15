import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application.sites_meihua_service import CONTRACT_VERSION, process_sites_meihua_request
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.meihua import MeihuaInput, cast_meihua
from scripts.render_sites_phase3a_preview import render_response_html

FIXED_NOW = datetime(2026, 7, 13, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v1"


def request() -> dict:
    return json.loads((CONTRACT_DIR / "sample_request.json").read_text(encoding="utf-8"))


def process(payload=None):
    return process_sites_meihua_request(request() if payload is None else payload, clock=lambda: FIXED_NOW)


def test_valid_request_matches_authoritative_engine_and_synthesizer():
    response = process()
    chart = cast_meihua(MeihuaInput(100, 27, 368, FIXED_NOW, "Asia/Shanghai", request()["request_id"]))
    knowledge = select_knowledge(chart, policy=KnowledgeAccessPolicy())
    synthesis = ConclusionSynthesizer().synthesize(chart, knowledge)
    result = response["deterministic_result"]
    assert response["status"] == "SUCCESS"
    assert result["base_hexagram"]["king_wen_number"] == chart.base_hexagram.king_wen_number
    assert result["mutual_hexagram"]["king_wen_number"] == chart.mutual_hexagram.king_wen_number
    assert result["changed_hexagram"]["king_wen_number"] == chart.changed_hexagram.king_wen_number
    assert result["moving_line"] == chart.moving_line
    assert result["body_use"]["body_trigram"] == chart.body_trigram.name_zh
    assert result["five_elements"]["body"] == chart.body_trigram.element.value
    assert result["seasonal_strength"]["body"] == chart.season_context.body_strength.value
    assert result["deterministic_conclusion"] == synthesis.model_dump(mode="json")


@pytest.mark.parametrize(("mutation", "code"), [
    ({"question_text": ""}, "EMPTY_QUESTION"),
    ({"numbers": [1, 2]}, "INVALID_NUMBER_COUNT"),
    ({"numbers": [1, 2, 3, 4]}, "INVALID_NUMBER_COUNT"),
    ({"numbers": [1, "2", 3]}, "INVALID_NUMBER_TYPE"),
    ({"numbers": [1, True, 3]}, "INVALID_NUMBER_TYPE"),
    ({"numbers": [0, 2, 3]}, "INVALID_NUMBER_TYPE"),
    ({"question_text": "第一个问题？第二个问题？"}, "MULTIPLE_QUESTIONS_NOT_ALLOWED"),
    ({"base_hexagram": {"king_wen_number": 1}}, "CLIENT_CALCULATION_NOT_ACCEPTED"),
    ({"evidence": []}, "CLIENT_CALCULATION_NOT_ACCEPTED"),
    ({"evidence_refs": ["EV01"]}, "CLIENT_CALCULATION_NOT_ACCEPTED"),
])
def test_invalid_requests_have_stable_safe_errors(mutation, code):
    payload = {**request(), **mutation}
    response = process(payload)
    assert response["errors"][0]["error_code"] == code
    assert response["request_id"] == payload["request_id"]
    serialized = json.dumps(response, ensure_ascii=False)
    assert "Traceback" not in serialized and "Abalo-s-project" not in serialized


@pytest.mark.parametrize(("question", "code"), [
    ("具体哪一天会有结果？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("这次一定会成功吗？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("他到底爱不爱我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("公司是不是准备裁掉我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("我是否应该停药？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这只股票什么时候买入？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("下一期彩票买什么号码？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这场官司会不会赢？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我想自杀，等卦象出来再求助。", "IMMEDIATE_SAFETY_RISK"),
])
def test_p0_rejections_are_safe_and_have_no_deterministic_result(monkeypatch, question, code):
    import abalo_iching.application.sites_meihua_service as service

    monkeypatch.setattr(service, "cast_meihua", lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")))
    response = process({**request(), "question_text": question})
    assert response["status"] == "VALIDATION_ERROR"
    assert response["deterministic_result"] is None
    assert response["errors"][0]["error_code"] == code
    serialized = json.dumps(response, ensure_ascii=False)
    assert question not in serialized
    assert "pattern" not in serialized.lower() and "regex" not in serialized.lower()


@pytest.mark.parametrize("variant", [
    "valid", "missing_numbers", "zero_numbers", "unacknowledged",
    "bad_timestamp", "bad_locale", "multiple_question_marks",
])
def test_immediate_safety_precedes_divination_fields(monkeypatch, variant):
    import abalo_iching.application.sites_meihua_service as service

    payload = {
        **request(),
        "question_text": "我现在想伤害自己，要不要等卦象出来再决定是否求助？",
    }
    if variant == "missing_numbers":
        payload.pop("numbers")
    elif variant == "zero_numbers":
        payload["numbers"] = [0, 2, 3]
    elif variant == "unacknowledged":
        payload["user_acknowledgements"] = {
            "deterministic_only": False,
            "narrative_unverified": False,
        }
    elif variant == "bad_timestamp":
        payload["client_timestamp"] = "not-a-time"
    elif variant == "bad_locale":
        payload["locale"] = "en-US"
    elif variant == "multiple_question_marks":
        payload["question_text"] += "还要继续吗？"
    monkeypatch.setattr(
        service,
        "cast_meihua",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")),
    )
    response = process(payload)
    assert response["status"] == "VALIDATION_ERROR"
    assert response["errors"][0]["error_code"] == "IMMEDIATE_SAFETY_RISK"
    assert response["deterministic_result"] is None


@pytest.mark.parametrize(("question", "code"), [
    ("我能不能把药量减一半？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这只基金还能不能加仓？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("下一期大乐透选哪些号？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这场官司我能赢吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("供应商是不是故意骗我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
])
@pytest.mark.parametrize("variant", ["valid", "missing_numbers", "unacknowledged"])
def test_other_p0_categories_precede_divination_fields(monkeypatch, question, code, variant):
    import abalo_iching.application.sites_meihua_service as service

    payload = {**request(), "question_text": question}
    if variant == "missing_numbers":
        payload.pop("numbers")
    elif variant == "unacknowledged":
        payload["user_acknowledgements"] = {
            "deterministic_only": False,
            "narrative_unverified": False,
        }
    monkeypatch.setattr(
        service,
        "cast_meihua",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")),
    )
    response = process(payload)
    assert response["status"] == "VALIDATION_ERROR"
    assert response["errors"][0]["error_code"] == code
    assert response["deterministic_result"] is None


def test_client_timestamp_is_audit_only():
    first = process()
    payload = {**request(), "client_timestamp": "2035-01-01T00:00:00+08:00"}
    second = process(payload)
    assert first["deterministic_result"] == second["deterministic_result"]
    assert second["audit"]["client_timestamp_used_for_calculation"] is False


def test_release_and_narrative_are_frozen():
    response = process()
    assert response["narrative"] == {
        "status": "UNVERIFIED", "available": False, "content": None,
        "blocked_reason": "解释功能尚未完成真实路径验证",
        "live_validation_status": "BLOCKED_BY_EXECUTION_POLICY",
    }
    assert response["release_gate"] == {
        "should_charge": False, "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False, "narrative_release_status": "UNVERIFIED",
    }


def test_contract_version_request_id_and_json_serialization():
    response = process()
    assert response["contract_version"] == CONTRACT_VERSION == "SITES_MEIHUA_API_CONTRACT_V1"
    assert response["request_id"] == request()["request_id"]
    json.dumps(response, ensure_ascii=False)


def test_response_exposes_safe_evidence_summary_not_raw_evidence():
    response = process()
    summary = response["deterministic_result"]["evidence_summary"]
    assert summary["count"] > 0 and summary["approved_knowledge_items_used"] == 0
    serialized = json.dumps(response, ensure_ascii=False)
    assert "rule_statement" not in serialized and "source_ref" not in serialized


def test_service_does_not_read_key_or_import_provider(monkeypatch):
    import os
    monkeypatch.setattr(os, "getenv", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("environment read")))
    response = process()
    assert response["status"] == "SUCCESS"
    assert "openai_provider" not in json.dumps(response)


def test_service_does_not_call_legacy_replay(monkeypatch):
    from abalo_iching.interpretation import historical_replay
    monkeypatch.setattr(historical_replay, "resolve_legacy_evidence_id", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy resolver called")))
    monkeypatch.setattr(historical_replay, "replay_legacy_v3_output_text_with_audit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy deduplicator called")))
    assert process()["status"] == "SUCCESS"


def test_preview_is_safe_and_explicitly_unverified(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "forbidden-test-value")
    page = render_response_html(process())
    assert "UNVERIFIED" in page and "解释功能尚未完成真实路径验证" in page
    assert "PYTHON_AUTHORITATIVE_ENGINE" in page
    assert "forbidden-test-value" not in page
    assert "system prompt" not in page.lower() and "Abalo-s-project" not in page


def test_contract_artifacts_are_valid_json_and_samples_are_synthetic():
    for path in CONTRACT_DIR.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    assert request()["request_id"].startswith("phase3a-synthetic")
