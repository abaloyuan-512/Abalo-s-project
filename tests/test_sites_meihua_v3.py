import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema

from abalo_iching.application.sites_meihua_service_v3 import process_sites_meihua_v3_request

CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v3"
FIXED_NOW = datetime(2026, 7, 18, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def request(**changes):
    payload = {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V3",
        "request_id": "v3-concrete-question",
        "question_text": "这次合作，我还应该继续投入吗？",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "decision_stage": "ALREADY_ACTING",
        "key_uncertainty": "OTHER_RESPONSE",
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-18T10:00:00+08:00",
        "user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True, "question_text_not_evidence": True},
    }
    payload.update(changes)
    return payload


def process(payload=None):
    return process_sites_meihua_v3_request(payload or request(), clock=lambda: FIXED_NOW)


def test_v3_request_and_response_schemas_accept_real_service_output():
    request_schema = json.loads((CONTRACT_DIR / "request.schema.json").read_text(encoding="utf-8"))
    response_schema = json.loads((CONTRACT_DIR / "response.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(request_schema)
    jsonschema.Draft202012Validator.check_schema(response_schema)
    jsonschema.validate(request(), request_schema, format_checker=jsonschema.FormatChecker())
    jsonschema.validate(process(), response_schema, format_checker=jsonschema.FormatChecker())


def test_v3_echoes_question_but_marks_it_non_calculative():
    response = process()
    assert response["status"] == "SUCCESS"
    assert response["user_question"] == "这次合作，我还应该继续投入吗？"
    assert response["audit"]["question_text_used_for_calculation"] is False
    assert response["deterministic_result"]["clarity_report"]["template_version"] == "SITES_CLARITY_REPORT_V2"


def test_changing_question_text_does_not_change_deterministic_chart():
    first = process()
    second = process(request(question_text="这份工作，我是否应该继续争取新的职责？"))
    for field in ["base_hexagram", "mutual_hexagram", "changed_hexagram", "moving_line", "body_use", "deterministic_conclusion"]:
        assert first["deterministic_result"][field] == second["deterministic_result"][field]
    assert first["audit"]["request_hash"] != second["audit"]["request_hash"]


def test_clarity_report_leads_with_direction_signals_and_reversible_action():
    report = process()["deterministic_result"]["clarity_report"]
    assert report["answer"]
    assert report["what_it_means"]
    assert len(report["continue_signals"]) == 3
    assert len(report["pause_signals"]) == 3
    assert "实际回复" in report["next_action"]
    assert "不参与排盘" in report["boundary_note"]


def test_v3_rejects_invalid_free_text_without_echoing_it():
    sentinel = "X" * 161
    response = process(request(question_text=sentinel))
    assert response["status"] == "VALIDATION_ERROR"
    assert response["deterministic_result"] is None
    assert sentinel not in json.dumps(response, ensure_ascii=False)
