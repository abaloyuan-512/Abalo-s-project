import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

import abalo_iching.application.sites_meihua_service as service

CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v1"
FIXED_NOW = datetime(2026, 7, 13, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def load(name):
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


REQUEST_SCHEMA = load("request.schema.json")
RESPONSE_SCHEMA = load("response.schema.json")
ERROR_SCHEMA = load("error.schema.json")
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def is_aware_iso_datetime(value):
    parsed = datetime.fromisoformat(value)
    return "T" in value and parsed.tzinfo is not None


REQUEST_VALIDATOR = Draft202012Validator(REQUEST_SCHEMA, format_checker=FORMAT_CHECKER)
RESPONSE_VALIDATOR = Draft202012Validator(RESPONSE_SCHEMA, format_checker=FORMAT_CHECKER)


def actual_success():
    return service.process_sites_meihua_request(load("sample_request.json"), clock=lambda: FIXED_NOW)


def assert_valid_response(value):
    RESPONSE_VALIDATOR.validate(value)


def test_schemas_are_draft_202012_valid_and_response_refs_are_internal():
    for schema in (REQUEST_SCHEMA, RESPONSE_SCHEMA, ERROR_SCHEMA):
        Draft202012Validator.check_schema(schema)
    refs = []
    def walk(value):
        if isinstance(value, dict):
            refs.extend(item for key, item in value.items() if key == "$ref")
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
    walk(RESPONSE_SCHEMA)
    assert refs and all(item.startswith("#/") for item in refs)


def test_embedded_and_standalone_error_constraints_do_not_drift():
    standalone = {key: value for key, value in ERROR_SCHEMA.items() if key not in {"$schema", "$id", "title"}}
    assert RESPONSE_SCHEMA["$defs"]["error"] == standalone


def test_request_and_all_committed_response_samples_validate():
    REQUEST_VALIDATOR.validate(load("sample_request.json"))
    for name in ("sample_success_response.json", "sample_validation_error.json", "sample_release_blocked_response.json"):
        assert_valid_response(load(name))


def test_actual_success_and_validation_errors_validate():
    success = actual_success()
    assert_valid_response(success)
    for mutation in ({"question_text": ""}, {"numbers": [1, 2]}, {"numbers": [1, "2", 3]}):
        assert_valid_response(service.process_sites_meihua_request({**load("sample_request.json"), **mutation}, clock=lambda: FIXED_NOW))


@pytest.mark.parametrize("question", [
    "这件事具体哪一天会发生？",
    "他是不是在骗我？",
    "这只股票应该卖出吗？",
    "我想结束生命。",
])
def test_additive_p0_error_codes_validate_under_v1(question):
    response = service.process_sites_meihua_request(
        {**load("sample_request.json"), "question_text": question},
        clock=lambda: FIXED_NOW,
    )
    assert response["contract_version"] == "SITES_MEIHUA_API_CONTRACT_V1"
    assert response["status"] == "VALIDATION_ERROR"
    assert_valid_response(response)


def test_p0_patch_does_not_change_request_or_success_shape():
    request_schema = load("request.schema.json")
    assert request_schema["properties"]["contract_version"]["const"] == "SITES_MEIHUA_API_CONTRACT_V1"
    success = actual_success()
    assert success["status"] == "SUCCESS"
    assert success["errors"] == []
    assert_valid_response(success)


def test_actual_engine_error_validates(monkeypatch):
    monkeypatch.setattr(service, "cast_meihua", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("private detail")))
    response = service.process_sites_meihua_request(load("sample_request.json"), clock=lambda: FIXED_NOW)
    assert response["status"] == "ENGINE_ERROR"
    assert "private detail" not in json.dumps(response)
    assert_valid_response(response)


def test_release_blocked_sample_validates():
    response = load("sample_release_blocked_response.json")
    assert response["status"] == "RELEASE_BLOCKED"
    assert_valid_response(response)


@pytest.mark.parametrize("mutation", [
    lambda r: r.pop("release_gate"),
    lambda r: r.update({"unexpected_internal": True}),
    lambda r: r["audit"].update({"generated_at": "not-a-date"}),
    lambda r: r["audit"].update({"client_timestamp": "not-a-date"}),
    lambda r: r["audit"].update({"audit_id": "bad"}),
    lambda r: r["audit"].update({"request_hash": "ABC"}),
    lambda r: r["deterministic_result"].update({"input_numbers": [1, 2]}),
    lambda r: r["deterministic_result"].update({"moving_line": 7}),
    lambda r: r["deterministic_result"]["base_hexagram"].update({"king_wen_number": 65}),
    lambda r: r.update({"deterministic_result": None}),
    lambda r: r["errors"].append({"error_code": "INVALID_REQUEST", "message": "bad", "request_id": r["request_id"], "audit_id": r["audit"]["audit_id"]}),
    lambda r: r["narrative"].update({"available": True}),
    lambda r: r["release_gate"].update({"should_charge": True}),
    lambda r: r["release_gate"].update({"closed_beta_allowed": True}),
])
def test_invalid_success_boundaries_fail(mutation):
    response = actual_success()
    mutation(response)
    with pytest.raises(ValidationError):
        assert_valid_response(response)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update({"errors": []}),
    lambda r: r.update({"deterministic_result": actual_success()["deterministic_result"]}),
    lambda r: r["errors"][0].update({"error_code": "UNKNOWN_ERROR"}),
])
def test_invalid_error_boundaries_fail(mutation):
    response = service.process_sites_meihua_request({**load("sample_request.json"), "question_text": ""}, clock=lambda: FIXED_NOW)
    mutation(response)
    with pytest.raises(ValidationError):
        assert_valid_response(response)


@pytest.mark.parametrize("bad_id", [
    None, "", 42, {"value": "id"}, "x" * 129, "line\nbreak", "carriage\rreturn", "tab\tvalue", "control\u0085value",
])
def test_invalid_request_ids_are_never_echoed_and_response_validates(bad_id):
    payload = load("sample_request.json")
    payload["request_id"] = bad_id
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    serialized = json.dumps(response, ensure_ascii=False)
    assert response["request_id"] == "invalid-request"
    assert response["errors"][0]["request_id"] == "invalid-request"
    assert response["audit"]["audit_id"] == response["errors"][0]["audit_id"]
    if isinstance(bad_id, str) and bad_id:
        assert bad_id not in serialized
    assert_valid_response(response)


def test_missing_request_id_is_safe_and_valid():
    payload = load("sample_request.json")
    payload.pop("request_id")
    response = service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert response["request_id"] == "invalid-request"
    assert_valid_response(response)


def test_valid_request_id_is_preserved_in_success_and_error():
    payload = load("sample_request.json")
    assert service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)["request_id"] == payload["request_id"]
    payload["question_text"] = ""
    assert service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)["request_id"] == payload["request_id"]


def test_validation_is_network_isolated(monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    assert_valid_response(actual_success())
    assert_valid_response(load("sample_validation_error.json"))
