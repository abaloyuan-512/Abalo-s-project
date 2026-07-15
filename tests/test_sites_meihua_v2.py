import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema
import pytest

import abalo_iching.application.sites_meihua_service as v1_service
import abalo_iching.application.sites_meihua_service_v2 as service

CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v2"
V1_CONTRACT_DIR = Path(__file__).parents[1] / "contracts" / "sites_meihua_v1"
FIXED_NOW = datetime(2026, 7, 15, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
CLIENT_FREE_TEXT_SENTINEL = "CLIENT_FREE_TEXT_MUST_NOT_BE_ECHOED"
SUCCESS_ONLY_FIELDS = {"structured_intake", "normalized_question", "question_template_version"}


def load(name):
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def request(**changes):
    payload = load("sample_request.json")
    payload.update(changes)
    return payload


def process(payload=None):
    return service.process_sites_meihua_v2_request(
        request() if payload is None else payload,
        clock=lambda: FIXED_NOW,
    )


def assert_response_schema_rejects(payload):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            payload,
            load("response.schema.json"),
            format_checker=jsonschema.FormatChecker(),
        )


def test_v2_schemas_and_samples_are_valid():
    request_schema = load("request.schema.json")
    response_schema = load("response.schema.json")
    error_schema = load("error.schema.json")
    for schema in [request_schema, response_schema, error_schema]:
        jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(request(), request_schema, format_checker=jsonschema.FormatChecker())
    jsonschema.validate(load("sample_success_response.json"), response_schema, format_checker=jsonschema.FormatChecker())
    jsonschema.validate(load("sample_validation_error.json"), response_schema, format_checker=jsonschema.FormatChecker())
    jsonschema.validate(process(), response_schema, format_checker=jsonschema.FormatChecker())


def test_embedded_error_schema_cannot_drift_from_standalone_schema():
    standalone = load("error.schema.json")
    normalized_standalone = {
        key: value
        for key, value in standalone.items()
        if key not in {"$schema", "$id", "title"}
    }
    assert load("response.schema.json")["$defs"]["error"] == normalized_standalone


NO_ENGINE_REJECTION_CASES = [
    ("unknown-domain", "v2", {"question_domain": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("unknown-goal", "v2", {"decision_goal": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("unknown-horizon", "v2", {"time_horizon": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("work-adjust-boundaries", "v2", {"question_domain": "WORK_CAREER", "decision_goal": "ADJUST_COMMITMENT_BOUNDARIES"}, ()),
    ("relationship-identify-obstacles", "v2", {"question_domain": "RELATIONSHIP_COMMUNICATION", "decision_goal": "IDENTIFY_OBSTACLES"}, ()),
    ("personal-prepare-communication", "v2", {"question_domain": "PERSONAL_PLANNING", "decision_goal": "PREPARE_COMMUNICATION"}, ()),
    ("v1-version-to-v2", "v2", {"contract_version": "SITES_MEIHUA_API_CONTRACT_V1"}, ()),
    ("v2-version-to-v1", "v1", {"contract_version": "SITES_MEIHUA_API_CONTRACT_V2"}, ()),
    ("question-text", "v2", {"question_text": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("normalized-question", "v2", {"normalized_question": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("question-context", "v2", {"question_context": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("background", "v2", {"background": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("client-generated-question", "v2", {"client_generated_question": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("client-hexagram", "v2", {"base_hexagram": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("client-evidence", "v2", {"evidence": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("client-conclusion", "v2", {"conclusion": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("client-derived-result", "v2", {"deterministic_result": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("numbers-missing", "v2", {}, ("numbers",)),
    ("number-count", "v2", {"numbers": [1, 2]}, ()),
    ("number-type", "v2", {"numbers": [1, "2", 3]}, ()),
    ("number-range", "v2", {"numbers": [1, 2, 1000]}, ()),
    ("locale", "v2", {"locale": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("timestamp", "v2", {"client_timestamp": CLIENT_FREE_TEXT_SENTINEL}, ()),
    ("acknowledgements-missing", "v2", {}, ("user_acknowledgements",)),
    ("deterministic-ack-false", "v2", {"user_acknowledgements": {"deterministic_only": False, "narrative_unverified": True, "structured_question_confirmed": True}}, ()),
    ("narrative-ack-false", "v2", {"user_acknowledgements": {"deterministic_only": True, "narrative_unverified": False, "structured_question_confirmed": True}}, ()),
    ("structured-question-ack-false", "v2", {"user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True, "structured_question_confirmed": False}}, ()),
]


@pytest.mark.parametrize(
    ("_case_name", "target", "changes", "removed_fields"),
    NO_ENGINE_REJECTION_CASES,
    ids=[case[0] for case in NO_ENGINE_REJECTION_CASES],
)
def test_all_27_rejection_classes_never_call_engine(
    monkeypatch, _case_name, target, changes, removed_fields
):
    engine_calls = 0

    def tracked_cast(*_args, **_kwargs):
        nonlocal engine_calls
        engine_calls += 1
        raise AssertionError("invalid input reached the deterministic engine")

    if target == "v2":
        payload = request(**copy.deepcopy(changes))
        for field in removed_fields:
            payload.pop(field, None)
        monkeypatch.setattr(service, "cast_meihua", tracked_cast)
        response = process(payload)
    else:
        payload = json.loads((V1_CONTRACT_DIR / "sample_request.json").read_text(encoding="utf-8"))
        payload.update(copy.deepcopy(changes))
        for field in removed_fields:
            payload.pop(field, None)
        monkeypatch.setattr(v1_service, "cast_meihua", tracked_cast)
        response = v1_service.process_sites_meihua_request(payload, clock=lambda: FIXED_NOW)
    assert engine_calls == 0
    assert response["status"] == "VALIDATION_ERROR"
    assert response["deterministic_result"] is None
    assert SUCCESS_ONLY_FIELDS.isdisjoint(response)
    assert CLIENT_FREE_TEXT_SENTINEL not in json.dumps(response, ensure_ascii=False)


@pytest.mark.parametrize("status", ["VALIDATION_ERROR", "ENGINE_ERROR", "RELEASE_BLOCKED"])
@pytest.mark.parametrize("success_field", sorted(SUCCESS_ONLY_FIELDS))
def test_error_statuses_reject_success_only_fields(status, success_field):
    response = load("sample_validation_error.json")
    response["status"] = status
    response[success_field] = copy.deepcopy(load("sample_success_response.json")[success_field])
    assert_response_schema_rejects(response)


@pytest.mark.parametrize("status", ["VALIDATION_ERROR", "ENGINE_ERROR", "RELEASE_BLOCKED"])
def test_error_statuses_reject_non_null_deterministic_result(status):
    response = load("sample_validation_error.json")
    response["status"] = status
    response["deterministic_result"] = copy.deepcopy(
        load("sample_success_response.json")["deterministic_result"]
    )
    assert_response_schema_rejects(response)


@pytest.mark.parametrize("missing_field", sorted(SUCCESS_ONLY_FIELDS))
def test_success_status_requires_all_success_only_fields(missing_field):
    response = load("sample_success_response.json")
    response.pop(missing_field)
    assert_response_schema_rejects(response)


@pytest.mark.parametrize(("domain", "goal"), [
    ("WORK_CAREER", "PLAN_NEXT_STEP"),
    ("PROJECT_COOPERATION", "PREPARE_COMMUNICATION"),
    ("RELATIONSHIP_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES"),
    ("PERSONAL_PLANNING", "OBSERVE_VERIFY_SIGNALS"),
])
def test_each_domain_success_calls_engine_once_and_returns_server_question(monkeypatch, domain, goal):
    calls = []
    real = service.cast_meihua

    def tracked(value):
        calls.append(value)
        return real(value)

    monkeypatch.setattr(service, "cast_meihua", tracked)
    response = process(request(question_domain=domain, decision_goal=goal))
    assert response["status"] == "SUCCESS"
    assert len(calls) == 1
    assert response["structured_intake"]["question_domain"] == domain
    assert response["normalized_question"].startswith("在“")
    assert response["question_template_version"] == "SITES_STRUCTURED_QUESTION_TEMPLATE_V1"
    assert response["audit"]["question_template_version"] == response["question_template_version"]
    assert response["narrative"]["status"] == "UNVERIFIED"
    assert response["release_gate"]["should_charge"] is False


def test_request_hash_is_deterministic_and_bound_to_server_generated_question():
    first = process()
    second = process(copy.deepcopy(request()))
    changed = process(request(time_horizon="NEXT_QUARTER"))
    assert first["audit"]["request_hash"] == second["audit"]["request_hash"]
    assert first["audit"]["request_hash"] != changed["audit"]["request_hash"]
    assert first["normalized_question"] != changed["normalized_question"]


def test_v1_and_v2_contract_versions_cannot_be_mixed():
    v2_schema = load("request.schema.json")
    bad = request(contract_version="SITES_MEIHUA_API_CONTRACT_V1")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, v2_schema)
    assert process(bad)["contract_version"] == "SITES_MEIHUA_API_CONTRACT_V2"


def test_v2_request_schema_rejects_disallowed_domain_goal_combination():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            request(question_domain="WORK_CAREER", decision_goal="ADJUST_COMMITMENT_BOUNDARIES"),
            load("request.schema.json"),
        )


def test_engine_error_is_safe_and_schema_valid(monkeypatch):
    monkeypatch.setattr(service, "cast_meihua", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("private")))
    response = process()
    assert response["status"] == "ENGINE_ERROR"
    assert "private" not in json.dumps(response, ensure_ascii=False)
    jsonschema.validate(response, load("response.schema.json"), format_checker=jsonschema.FormatChecker())
