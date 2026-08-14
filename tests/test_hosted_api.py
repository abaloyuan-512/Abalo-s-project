import http.client
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest

from scripts import run_hosted_api as hosted_api

ENGINE_KEY = "test-only-engine-key-that-is-long-enough"
ROOT = Path(__file__).resolve().parents[1]


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


def valid_owner_preview_request() -> dict[str, object]:
    return {
        "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
        "request_id": "hosted-owner-preview-v1",
        "question_text": "这次合作已经反复推迟，我还应该继续投入吗？",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "decision_stage": "ALREADY_ACTING",
        "key_uncertainty": "OTHER_RESPONSE",
        "decision_risk_profile": "STANDARD",
        "confirmed_facts": ["双方已经沟通过两次。"],
        "unknowns": ["不知道最终负责人是否已经看过方案。"],
        "options": [],
        "actions_already_taken": [],
        "observable_responses": [],
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-22T12:00:00+08:00",
        "user_acknowledgements": {
            "owner_preview_only": True,
            "live_model_cost_acknowledged": True,
            "no_formal_persistence": True,
            "user_statements_not_verified_facts": True,
        },
    }


def valid_guided_intake_request() -> dict[str, object]:
    return {
        "contract_version": "SITES_GUIDED_INTAKE_CONTRACT_V1",
        "session_id": "hosted-intake-001",
        "question_text": "这次合作，我还应该继续投入吗？",
        "turns": [],
        "locale": "zh-CN",
    }


def valid_direct_reading_request() -> dict[str, object]:
    return {
        "contract_version": "SITES_DIRECT_READING_V2_NONPROD_V2",
        "request_id": "drv2-5555555555555555",
        "question_text": "我要不要考虑换工作这件事？",
        "numbers": [5, 6, 3],
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


def test_direct_private_server_sinks_require_explicit_synthetic_confirmation() -> None:
    with pytest.raises(ValueError, match="confirmed synthetic"):
        hosted_api.create_server(
            "127.0.0.1",
            0,
            ENGINE_KEY,
            direct_reading_internal_audit_sink=lambda _value: None,
        )


def test_health_check_discloses_versions_but_no_secret_or_repository_path(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    with running_server() as port:
        status, headers, payload = request(port, "GET", "/healthz")
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "abalo-authoritative-engine"
    assert payload["git_commit"] == "abcdef123456"
    assert payload["owner_preview_contract"] == "SITES_OWNER_PREVIEW_CONTRACT_V1"
    assert payload["page8_contract"] == "SITES_PAGE8_READING_V1"
    assert payload["prompt_version"]
    assert payload["validator_version"]
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
    assert payload["deterministic_result"]["clarity_report"]["template_version"] == "SITES_CLARITY_REPORT_V3"


def test_owner_preview_route_is_authenticated_and_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ABALO_OWNER_PREVIEW_ENABLED", raising=False)
    with running_server() as port:
        unauthorized, _headers, _payload = request(
            port,
            "POST",
            "/api/preview/v1/meihua",
            payload=valid_owner_preview_request(),
        )
        status, headers, payload = request(
            port,
            "POST",
            "/api/preview/v1/meihua",
            key=ENGINE_KEY,
            payload=valid_owner_preview_request(),
        )
    assert unauthorized == 401
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert payload["status"] == "PREVIEW_DISABLED"
    assert payload["personalized_reading"] is None


def test_guided_intake_route_is_authenticated_and_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ABALO_GUIDED_INTAKE_ENABLED", raising=False)
    with running_server() as port:
        unauthorized, _headers, _payload = request(
            port, "POST", "/api/intake/v1/turn", payload=valid_guided_intake_request()
        )
        disabled, headers, payload = request(
            port,
            "POST",
            "/api/intake/v1/turn",
            key=ENGINE_KEY,
            payload=valid_guided_intake_request(),
        )
    assert unauthorized == 401
    assert disabled == 503
    assert headers["Cache-Control"] == "no-store"
    assert payload == {"status": "intake_disabled"}


def test_guided_intake_route_returns_one_model_question(monkeypatch) -> None:
    monkeypatch.delenv("ABALO_GUIDED_INTAKE_ENABLED", raising=False)
    monkeypatch.setenv("ABALO_OWNER_PREVIEW_ENABLED", "true")
    expected = {
        "contract_version": "SITES_GUIDED_INTAKE_CONTRACT_V1",
        "session_id": "hosted-intake-001",
        "status": "ASK",
        "assistant_message": "先确认观察范围。",
        "next_question": "你希望在多长时间内看清这件事？",
    }
    monkeypatch.setattr(
        hosted_api,
        "process_sites_guided_intake_v1_request",
        lambda payload: {**expected, "question_text": payload["question_text"]},
    )
    with running_server() as port:
        status, _headers, payload = request(
            port,
            "POST",
            "/api/intake/v1/turn",
            key=ENGINE_KEY,
            payload=valid_guided_intake_request(),
        )
    assert status == 200
    assert payload["status"] == "ASK"
    assert payload["next_question"] == "你希望在多长时间内看清这件事？"


def test_owner_preview_job_is_async_authenticated_and_idempotent(monkeypatch) -> None:
    calls = 0
    release = threading.Event()

    def processor(payload, **_kwargs):
        nonlocal calls
        calls += 1
        release.wait(timeout=2)
        return {
            "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
            "request_id": payload["request_id"],
            "status": "SUCCESS",
            "deterministic_result": {},
            "personalized_reading": {"core_judgment": "测试成功"},
            "preview_meta": {"actual_api_cost_usd": 0.01},
            "error": None,
        }

    monkeypatch.setattr(hosted_api, "process_sites_owner_preview_v1_request", processor)
    payload = valid_owner_preview_request()
    with running_server() as port:
        unauthorized, _headers, _payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", payload=payload
        )
        first, _headers, first_payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=payload
        )
        duplicate, _headers, duplicate_payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=payload
        )
        conflict_payload = {**payload, "question_text": "这是另一个长度足够的问题。"}
        conflict, _headers, _payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=conflict_payload
        )
        release.set()
        terminal = None
        for _ in range(50):
            terminal, _headers, terminal_payload = request(
                port,
                "GET",
                f"/api/preview/v1/meihua/jobs/{payload['request_id']}",
                key=ENGINE_KEY,
            )
            if terminal == 200:
                break
            time.sleep(0.01)

    assert unauthorized == 401
    assert first == 202
    assert duplicate == 202
    assert first_payload["status"] == "RUNNING"
    assert first_payload["preview_meta"]["stage"] == "GENERATING_AND_VALIDATING"
    assert first_payload["preview_meta"]["elapsed_ms"] >= 0
    assert duplicate_payload["request_id"] == payload["request_id"]
    assert duplicate_payload["preview_meta"]["stage"] == "GENERATING_AND_VALIDATING"
    assert conflict == 409
    assert calls == 1
    assert terminal == 200
    assert terminal_payload["status"] == "SUCCESS"
    assert terminal_payload["preview_meta"]["stage"] == "COMPLETE"
    assert terminal_payload["preview_meta"]["elapsed_ms"] >= 0


def test_owner_preview_job_rejects_excess_concurrency_without_generation(monkeypatch) -> None:
    calls = 0
    release = threading.Event()

    def processor(payload, **_kwargs):
        nonlocal calls
        calls += 1
        release.wait(timeout=2)
        return {
            "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
            "request_id": payload["request_id"],
            "status": "SUCCESS",
            "deterministic_result": {},
            "personalized_reading": {"core_judgment": "测试成功"},
            "preview_meta": {"actual_api_cost_usd": 0.01},
            "error": None,
        }

    monkeypatch.setattr(hosted_api, "process_sites_owner_preview_v1_request", processor)
    requests = [
        {**valid_owner_preview_request(), "request_id": f"hosted-beta-concurrency-{index}"}
        for index in range(3)
    ]
    with running_server() as port:
        first, _headers, _payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=requests[0]
        )
        second, _headers, _payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=requests[1]
        )
        third, _headers, third_payload = request(
            port, "POST", "/api/preview/v1/meihua/jobs", key=ENGINE_KEY, payload=requests[2]
        )
        release.set()

    assert first == 202
    assert second == 202
    assert third == 429
    assert third_payload["status"] == "PREVIEW_BUSY"
    assert calls == 2


def test_direct_reading_job_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ABALO_DIRECT_READING_V2_ENABLED", raising=False)
    monkeypatch.setattr(
        hosted_api,
        "prepare_direct_reading_v2_request",
        lambda *_a, **_k: pytest.fail("direct reading processor called"),
    )
    with running_server() as port:
        status, _headers, payload = request(
            port,
            "POST",
            "/api/preview/v2/direct-reading/jobs",
            key=ENGINE_KEY,
            payload=valid_direct_reading_request(),
        )
    assert status == 503
    assert payload == {"status": "direct_reading_disabled"}


def test_direct_reading_job_twenty_duplicates_call_processor_once(monkeypatch) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    calls = 0
    prepare_calls = 0
    release = threading.Event()
    real_prepare = hosted_api.prepare_direct_reading_v2_request

    def prepare(*args, **kwargs):
        nonlocal prepare_calls
        prepare_calls += 1
        return real_prepare(*args, **kwargs)

    def processor(prepared, **kwargs):
        nonlocal calls
        calls += 1
        kwargs["progress_callback"]("MODEL_STREAMING")
        release.wait(timeout=3)
        frozen = json.loads(
            (ROOT / "outputs/v011_stability_run_ledger.json").read_text(encoding="utf-8")
        )["cases"][0]["released_direct_reading"]
        return {
            "contract_version": "SITES_DIRECT_READING_V2_NONPROD_V2",
            "status": "SUCCESS",
            "direct_reading": frozen,
            "audit": {"request_id": prepared.request_id, "model": "internal-only"},
            "error_code": None,
            "error_message": None,
            "retryable": False,
            "failure_stage": None,
        }

    monkeypatch.setattr(hosted_api, "prepare_direct_reading_v2_request", prepare)
    monkeypatch.setattr(hosted_api, "process_prepared_direct_reading_v2_request", processor)
    payload = {
        **valid_direct_reading_request(),
        "question_text": "我现在必须二选一：把主要资源集中到一个新产品并承担更大波动，还是继续平均分散在多个成熟方向？",
        "numbers": [38, 71, 24],
    }
    with running_server() as port:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [
                pool.submit(
                    request,
                    port,
                    "POST",
                    "/api/preview/v2/direct-reading/jobs",
                    key=ENGINE_KEY,
                    payload=payload,
                )
                for _ in range(20)
            ]
            time.sleep(0.1)
            release.set()
            responses = [future.result(timeout=5) for future in futures]
        assert all(status in {200, 202} for status, _headers, _body in responses)
        assert calls == 1
        assert prepare_calls == 1
        pending_bodies = [body for status, _headers, body in responses if status == 202]
        assert pending_bodies
        assert all("preview_meta" not in body for body in pending_bodies)
        assert any(body["chart_facts"]["base_hexagram"]["name"] for body in pending_bodies)
        conflict = request(
            port,
            "POST",
            "/api/preview/v2/direct-reading/jobs",
            key=ENGINE_KEY,
            payload={**payload, "question_text": "这是另一个完全不同的问题。"},
        )
        assert conflict[0] == 409
        terminal = request(
            port,
            "GET",
            f"/api/preview/v2/direct-reading/jobs/{payload['request_id']}",
            key=ENGINE_KEY,
        )
    assert terminal[0] == 200
    assert terminal[2]["status"] == "SUCCESS"
    serialized = json.dumps(terminal[2], ensure_ascii=False)
    assert "internal-only" not in serialized
    assert "usage" not in serialized


def test_direct_reading_stage_is_top_level_monotonic_and_unknown_stages_are_ignored(monkeypatch) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    release = threading.Event()

    def processor(prepared, **kwargs):
        callback = kwargs["progress_callback"]
        callback("MODEL_STREAMING")
        callback("MODEL_REQUESTED")
        callback("UNTRUSTED_STAGE")
        release.wait(timeout=3)
        callback("VALIDATING")
        return {
            "contract_version": hosted_api.DIRECT_READING_CONTRACT_VERSION,
            "status": "SUCCESS",
            "direct_reading": {
                "text": "## 判断\n完整正文",
                "content_format": "MARKDOWN",
                "chart_facts": prepared.chart_facts.model_dump(mode="json"),
            },
            "audit": {"request_id": prepared.request_id},
            "error_code": None,
            "error_message": None,
            "retryable": False,
            "failure_stage": None,
        }

    monkeypatch.setattr(hosted_api, "process_prepared_direct_reading_v2_request", processor)
    payload = {**valid_direct_reading_request(), "request_id": "drv2-7777777777777777"}
    with running_server() as port:
        submitted = request(port, "POST", hosted_api.DIRECT_READING_JOB_PATH, key=ENGINE_KEY, payload=payload)
        assert submitted[0] == 202
        running = request(
            port,
            "GET",
            f"{hosted_api.DIRECT_READING_JOB_PREFIX}{payload['request_id']}",
            key=ENGINE_KEY,
        )
        assert running[0] == 202
        assert running[2]["stage"] == "MODEL_STREAMING"
        assert "preview_meta" not in running[2]
        assert running[2]["chart_facts"]["base_hexagram"]["name"]
        release.set()


def test_direct_reading_unhandled_error_log_does_not_include_exception_message(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    secret = "用户原问秘密不得进入日志"

    def processor(*_args, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(hosted_api, "process_prepared_direct_reading_v2_request", processor)
    payload = {**valid_direct_reading_request(), "request_id": "drv2-8888888888888888"}
    with running_server() as port:
        assert request(port, "POST", hosted_api.DIRECT_READING_JOB_PATH, key=ENGINE_KEY, payload=payload)[0] == 202
        deadline = time.monotonic() + 3
        terminal = None
        while time.monotonic() < deadline:
            terminal = request(
                port,
                "GET",
                f"{hosted_api.DIRECT_READING_JOB_PREFIX}{payload['request_id']}",
                key=ENGINE_KEY,
            )
            if terminal[0] == 200:
                break
            time.sleep(0.01)
    assert terminal is not None and terminal[2]["status"] == "UNAVAILABLE"
    assert secret not in caplog.text
    assert "error_code=UNHANDLED" in caplog.text


def test_direct_reading_prepare_error_log_does_not_include_exception_message(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    secret = "同步排盘异常携带用户原问"

    def prepare(*_args, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(hosted_api, "prepare_direct_reading_v2_request", prepare)
    payload = {**valid_direct_reading_request(), "request_id": "drv2-bbbbbbbbbbbbbbbb"}
    with running_server() as port:
        response = request(
            port,
            "POST",
            hosted_api.DIRECT_READING_JOB_PATH,
            key=ENGINE_KEY,
            payload=payload,
        )
    assert response[0] == 500
    assert response[2]["status"] == "UNAVAILABLE"
    assert response[2]["failure_stage"] == "ENGINE"
    assert secret not in caplog.text
    assert "direct_reading_submit" in caplog.text
    assert "error_code=UNHANDLED" in caplog.text
