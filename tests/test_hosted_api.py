import http.client
import json
import threading
from contextlib import contextmanager

import pytest

from scripts import run_hosted_api as hosted_api

ENGINE_KEY = "test-only-engine-key-that-is-long-enough"


def valid_request() -> dict[str, object]:
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V2",
        "request_id": "hosted-real-request-001",
        "question_domain": "WORK_CAREER",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-17T12:00:00+08:00",
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "structured_question_confirmed": True,
        },
    }


def valid_v3_request() -> dict[str, object]:
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V3",
        "request_id": "hosted-real-request-v3",
        "question_text": "这次合作，我还应该继续投入吗？",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "decision_stage": "ALREADY_ACTING",
        "key_uncertainty": "OTHER_RESPONSE",
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-18T12:00:00+08:00",
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "question_text_not_evidence": True,
        },
    }


@contextmanager
def running_server():
    server = hosted_api.create_server("127.0.0.1", 0, ENGINE_KEY)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def request(port: int, method: str, path: str, *, key: str = "", payload: object | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-Abalo-Engine-Key"] = key
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), json.loads(response.read())
    connection.close()
    return result


def test_engine_key_is_mandatory_and_not_accepted_when_short() -> None:
    with pytest.raises(ValueError, match="32"):
        hosted_api.create_server("127.0.0.1", 0, "short")


def test_health_check_discloses_no_secret_or_repository_path() -> None:
    with running_server() as port:
        status, headers, payload = request(port, "GET", "/healthz")
    assert status == 200
    assert payload == {"status": "ok", "service": "abalo-authoritative-engine"}
    assert headers["Cache-Control"] == "no-store"
    assert "Abalo-s-project" not in json.dumps(payload)


@pytest.mark.parametrize("key", ["", "wrong-key-that-is-also-long-enough-000"])
def test_missing_or_wrong_key_cannot_reach_engine(monkeypatch, key: str) -> None:
    monkeypatch.setattr(hosted_api, "process_sites_meihua_v2_request", lambda *_a, **_k: pytest.fail("engine called"))
    with running_server() as port:
        status, _headers, payload = request(port, "POST", "/api/v2/meihua", key=key, payload=valid_request())
    assert status == 401
    assert payload == {"status": "unauthorized"}


def test_authorized_request_returns_real_provenance_and_mentor_report() -> None:
    with running_server() as port:
        status, headers, payload = request(port, "POST", "/api/v2/meihua", key=ENGINE_KEY, payload=valid_request())
    assert status == 200
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert payload["status"] == "SUCCESS"
    assert payload["audit"]["synthetic_or_real_input"] == "REAL"
    assert payload["deterministic_result"]["mentor_report"]["template_version"] == "SITES_MENTOR_REPORT_V1"


def test_authorized_v3_request_returns_concrete_question_and_clarity_report() -> None:
    with running_server() as port:
        status, _headers, payload = request(port, "POST", "/api/v3/meihua", key=ENGINE_KEY, payload=valid_v3_request())
    assert status == 200
    assert payload["status"] == "SUCCESS"
    assert payload["user_question"] == "这次合作，我还应该继续投入吗？"
    assert payload["audit"]["synthetic_or_real_input"] == "REAL"
    assert payload["audit"]["question_text_used_for_calculation"] is False
    assert payload["deterministic_result"]["clarity_report"]["template_version"] == "SITES_CLARITY_REPORT_V2"
