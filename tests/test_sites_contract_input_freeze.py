import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator, FormatChecker

import abalo_iching.application.sites_meihua_service as service
from scripts.run_sites_contract_conformance_sweep import build_contract_sweep, build_seasonal_sweep

CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v1"
REQUEST_SCHEMA = json.loads((CONTRACT_DIR / "request.schema.json").read_text(encoding="utf-8"))
RESPONSE_SCHEMA = json.loads((CONTRACT_DIR / "response.schema.json").read_text(encoding="utf-8"))
CHECKER = FormatChecker()


@CHECKER.checks("date-time", raises=(TypeError, ValueError))
def is_contract_datetime(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return "T" in value and parsed.tzinfo is not None


REQUEST_VALIDATOR = Draft202012Validator(REQUEST_SCHEMA, format_checker=CHECKER)
RESPONSE_VALIDATOR = Draft202012Validator(RESPONSE_SCHEMA, format_checker=CHECKER)
FIXED_NOW = datetime(2026, 7, 13, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def base_request():
    return json.loads((CONTRACT_DIR / "sample_request.json").read_text(encoding="utf-8"))


VALID_IDS = ["a", "A" * 128, "550e8400-e29b-41d4-a716-446655440000", "client.v1:case_007-run"]
INVALID_IDS = [" ", " leading", "trailing ", "middle space", "invalid-request", "x" * 129, "中文", "a/b", "a?b", "a\nb", "a\rb", "a\tb", "a\u0085b"]
VALID_TIMESTAMPS = ["2026-07-13T10:00:00+08:00", "2026-07-13T02:00:00Z", "2026-07-13T10:00:00.123456+08:00"]
INVALID_TIMESTAMPS = ["2026-07-13 10:00:00+08:00", "2026-07-13T10:00:00", "2026-07-13", "2026-02-30T10:00:00+08:00", "2026-07-13T10:00:00+25:00", "2026-07-13\t10:00:00+08:00", "2026-07-13\n10:00:00+08:00", 123]


@pytest.mark.parametrize("request_id", VALID_IDS)
def test_valid_request_ids_match_schema_and_service(request_id):
    payload = {**base_request(), "request_id": request_id}
    assert REQUEST_VALIDATOR.is_valid(payload)
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["status"] == "SUCCESS" and response["request_id"] == request_id
    RESPONSE_VALIDATOR.validate(response)


@pytest.mark.parametrize("request_id", INVALID_IDS)
def test_invalid_request_ids_match_schema_and_service_without_cast(monkeypatch, request_id):
    payload = {**base_request(), "request_id": request_id}
    assert not REQUEST_VALIDATOR.is_valid(payload)
    monkeypatch.setattr(service, "cast_meihua", lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")))
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["status"] == "VALIDATION_ERROR" and response["request_id"] == "invalid-request"
    RESPONSE_VALIDATOR.validate(response)


@pytest.mark.parametrize("timestamp", VALID_TIMESTAMPS)
def test_valid_timestamps_match_schema_and_service(timestamp):
    payload = {**base_request(), "client_timestamp": timestamp}
    assert REQUEST_VALIDATOR.is_valid(payload)
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["status"] == "SUCCESS" and response["audit"]["client_timestamp"] == timestamp
    RESPONSE_VALIDATOR.validate(response)


@pytest.mark.parametrize("timestamp", INVALID_TIMESTAMPS)
def test_invalid_timestamps_match_schema_and_service_without_cast(monkeypatch, timestamp):
    payload = {**base_request(), "client_timestamp": timestamp}
    assert not REQUEST_VALIDATOR.is_valid(payload)
    monkeypatch.setattr(service, "cast_meihua", lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")))
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["status"] == "VALIDATION_ERROR"
    RESPONSE_VALIDATOR.validate(response)


@pytest.mark.parametrize("question", ["", " ", "\n", "\t", "\u2003"])
def test_blank_questions_match_schema_and_service(question):
    payload = {**base_request(), "question_text": question}
    assert not REQUEST_VALIDATOR.is_valid(payload)
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["errors"][0]["error_code"] == "EMPTY_QUESTION"
    RESPONSE_VALIDATOR.validate(response)


@pytest.mark.parametrize("mutation", [
    {"numbers": [1, 2]}, {"numbers": [1, 2, 3, 4]}, {"numbers": [1, "2", 3]},
    {"locale": "en-US"}, {"user_acknowledgements": {"deterministic_only": True, "narrative_unverified": False}},
    {"extra": True}, {"base_hexagram": {}}, {"evidence": []},
])
def test_other_rejected_contract_inputs_do_not_reach_engine(monkeypatch, mutation):
    payload = {**base_request(), **mutation}
    assert not REQUEST_VALIDATOR.is_valid(payload)
    monkeypatch.setattr(service, "cast_meihua", lambda *a, **k: (_ for _ in ()).throw(AssertionError("cast called")))
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["status"] == "VALIDATION_ERROR"
    RESPONSE_VALIDATOR.validate(response)


def test_contract_conformance_covers_all_384_authoritative_results():
    rows, summary = build_contract_sweep()
    assert len(rows) == 384
    assert summary == {"completed": 384, "passed": 384, "hexagrams_covered": 64, "hexagram_line_pairs": 384, "all_six_lines_per_hexagram": True, "should_charge_true": 0, "formal_persistence_true": 0, "closed_beta_true": 0, "narrative_not_unverified": 0, "external_api_calls": 0}


def test_seasonal_contract_sweep_is_12_of_12():
    rows, summary = build_seasonal_sweep()
    assert len(rows) == 12 and summary == {"completed": 12, "passed": 12, "client_timestamp_used_true": 0}
    assert all(row["seasonal_strength"]["solar_term"] and row["seasonal_strength"]["month_branch"] for row in rows)
