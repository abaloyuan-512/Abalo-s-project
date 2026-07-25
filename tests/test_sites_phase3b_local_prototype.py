import http.client
import json
import threading
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import jsonschema
import pytest

from abalo_iching.application import sites_meihua_service
from scripts import run_sites_phase3b_local_server as local_server

ROOT = Path(__file__).parents[1]
SITE = ROOT / "sites" / "phase3b-prototype"
RESPONSE_SCHEMA = json.loads((ROOT / "contracts/sites_meihua_v1/response.schema.json").read_text(encoding="utf-8"))
RESPONSE_SCHEMA_V2 = json.loads((ROOT / "contracts/sites_meihua_v2/response.schema.json").read_text(encoding="utf-8"))


def valid_request(question_text="我应该如何更稳妥地推进当前合作？"):
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V1",
        "request_id": "phase3b-synthetic-test-001",
        "question_text": question_text,
        "numbers": [100, 27, 368],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-13T10:00:00+08:00",
        "user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True},
    }


def valid_v2_request():
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V2",
        "request_id": "phase3g-structured-test-001",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": "PLAN_NEXT_STEP",
        "time_horizon": "NEXT_30_DAYS",
        "numbers": [100, 27, 368],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-15T10:00:00+08:00",
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "structured_question_confirmed": True,
        },
    }


@contextmanager
def running_server():
    server = local_server.create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    connection.close()
    return result


@pytest.mark.parametrize("value", ["x" * 500, " " + "x" * 498 + " "])
def test_raw_question_length_up_to_500_is_accepted_and_normalized(value):
    response = sites_meihua_service.process_sites_meihua_request(valid_request(value))
    assert response["status"] == "SUCCESS"
    assert response["question_text"] == value.strip()
    jsonschema.validate(response, RESPONSE_SCHEMA)


@pytest.mark.parametrize("value", ["x" * 501, " " + "x" * 500, "x" * 500 + " "])
def test_raw_question_length_over_500_is_rejected_before_engine(monkeypatch, value):
    monkeypatch.setattr(sites_meihua_service, "cast_meihua", lambda *_a, **_k: pytest.fail("cast_meihua called"))
    response = sites_meihua_service.process_sites_meihua_request(valid_request(value))
    assert response["status"] == "VALIDATION_ERROR"
    assert response["errors"][0]["error_code"] == "INVALID_REQUEST"
    jsonschema.validate(response, RESPONSE_SCHEMA)


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_empty_or_whitespace_question_is_rejected_and_schema_valid(value):
    response = sites_meihua_service.process_sites_meihua_request(valid_request(value))
    assert response["errors"][0]["error_code"] == "EMPTY_QUESTION"
    jsonschema.validate(response, RESPONSE_SCHEMA)


def test_request_hash_uses_normalized_question():
    padded = sites_meihua_service.process_sites_meihua_request(valid_request(" 合作如何推进？ "))
    normalized = sites_meihua_service.process_sites_meihua_request(valid_request("合作如何推进？"))
    assert padded["audit"]["request_hash"] == normalized["audit"]["request_hash"]


@pytest.mark.parametrize("host", ["0.0.0.0", "localhost", "192.168.1.8", "8.8.8.8", "::1"])
def test_server_rejects_every_host_except_literal_ipv4_loopback(host):
    with pytest.raises(ValueError, match="127.0.0.1"):
        local_server.validate_host(host)


def test_server_accepts_literal_ipv4_loopback():
    assert local_server.validate_host("127.0.0.1") == "127.0.0.1"


@pytest.mark.parametrize(
    ("path", "content_type"),
    [("/", "text/html"), ("/assets/app.css", "text/css"), ("/assets/app.js", "text/javascript")],
)
def test_static_routes_are_fixed_and_successful(path, content_type):
    with running_server() as port:
        status, headers, body = request(port, "GET", path)
    assert status == 200 and content_type in headers["Content-Type"] and body
    assert headers["Cache-Control"] == "no-store"


def test_healthz_is_safe_and_unverified():
    with running_server() as port:
        status, _headers, body = request(port, "GET", "/healthz")
    payload = json.loads(body)
    assert status == 200
    assert payload == {"status": "ok", "service": "sites-phase3b-local-prototype", "network_scope": "loopback-only", "narrative_status": "UNVERIFIED"}
    assert "Abalo-s-project" not in body.decode() and "OPENAI" not in body.decode()


def test_valid_post_calls_real_service_and_returns_schema_valid_success():
    body = json.dumps(valid_request(), ensure_ascii=False).encode()
    with running_server() as port:
        status, headers, raw = request(port, "POST", "/api/v1/meihua", body, {"Content-Type": "application/json"})
    payload = json.loads(raw)
    assert status == 200 and payload["status"] == "SUCCESS"
    assert headers["Cache-Control"] == "no-store"
    assert payload["audit"]["calculation_source"] == "PYTHON_AUTHORITATIVE_ENGINE"
    jsonschema.validate(payload, RESPONSE_SCHEMA)


def test_v2_post_is_explicitly_routed_to_structured_service():
    body = json.dumps(valid_v2_request(), ensure_ascii=False).encode()
    with running_server() as port:
        status, headers, raw = request(port, "POST", "/api/v2/meihua", body, {"Content-Type": "application/json"})
    payload = json.loads(raw)
    assert status == 200 and payload["status"] == "SUCCESS"
    assert headers["Cache-Control"] == "no-store"
    assert payload["contract_version"] == "SITES_MEIHUA_API_CONTRACT_V2"
    assert payload["normalized_question"].startswith("在“")
    jsonschema.validate(payload, RESPONSE_SCHEMA_V2)


def test_v1_and_v2_http_routes_do_not_cross_services(monkeypatch):
    calls = []
    real_v1 = local_server.process_sites_meihua_request
    real_v2 = local_server.process_sites_meihua_v2_request

    def tracked_v1(payload):
        calls.append("v1")
        return real_v1(payload)

    def tracked_v2(payload):
        calls.append("v2")
        return real_v2(payload)

    monkeypatch.setattr(local_server, "process_sites_meihua_request", tracked_v1)
    monkeypatch.setattr(local_server, "process_sites_meihua_v2_request", tracked_v2)
    with running_server() as port:
        request(port, "POST", "/api/v1/meihua", json.dumps(valid_request()).encode(), {"Content-Type": "application/json"})
        request(port, "POST", "/api/v2/meihua", json.dumps(valid_v2_request()).encode(), {"Content-Type": "application/json"})
    assert calls == ["v1", "v2"]


@pytest.mark.parametrize(("path", "version", "schema"), [
    ("/api/v1/meihua", "SITES_MEIHUA_API_CONTRACT_V1", RESPONSE_SCHEMA),
    ("/api/v2/meihua", "SITES_MEIHUA_API_CONTRACT_V2", RESPONSE_SCHEMA_V2),
])
def test_transport_errors_preserve_selected_contract(path, version, schema):
    with running_server() as port:
        status, _headers, raw = request(port, "POST", path, b"{bad", {"Content-Type": "application/json"})
    payload = json.loads(raw)
    assert status == 400 and payload["contract_version"] == version
    jsonschema.validate(payload, schema)


def test_http_adapter_delegates_to_process_service(monkeypatch):
    called = []
    real = local_server.process_sites_meihua_request

    def tracked(payload):
        called.append(payload["request_id"])
        return real(payload)

    monkeypatch.setattr(local_server, "process_sites_meihua_request", tracked)
    with running_server() as port:
        request(port, "POST", "/api/v1/meihua", json.dumps(valid_request()).encode(), {"Content-Type": "application/json"})
    assert called == ["phase3b-synthetic-test-001"]


def test_invalid_json_is_safe_contract_error():
    with running_server() as port:
        status, _headers, raw = request(port, "POST", "/api/v1/meihua", b"{bad", {"Content-Type": "application/json"})
    payload = json.loads(raw)
    assert status == 400 and payload["status"] == "VALIDATION_ERROR"
    jsonschema.validate(payload, RESPONSE_SCHEMA)
    assert "Traceback" not in raw.decode()


def test_non_json_content_type_is_rejected_safely():
    with running_server() as port:
        status, _headers, raw = request(port, "POST", "/api/v1/meihua", b"hello", {"Content-Type": "text/plain"})
    assert status == 415
    jsonschema.validate(json.loads(raw), RESPONSE_SCHEMA)


def test_oversized_body_is_rejected_without_reading_or_engine(monkeypatch):
    monkeypatch.setattr(local_server, "process_sites_meihua_request", lambda payload: pytest.fail("service called") if payload else sites_meihua_service.process_sites_meihua_request(payload))
    with running_server() as port:
        status, _headers, raw = request(port, "POST", "/api/v1/meihua", b"", {"Content-Type": "application/json", "Content-Length": str(local_server.MAX_BODY_BYTES + 1)})
    assert status == 413
    jsonschema.validate(json.loads(raw), RESPONSE_SCHEMA)


def test_unknown_path_is_safe_404_without_directory_listing():
    with running_server() as port:
        status, _headers, raw = request(port, "GET", "/../../")
    text = raw.decode()
    assert status == 404 and "Directory listing" not in text and str(ROOT) not in text


def test_unhandled_service_exception_never_exposes_traceback_or_path(monkeypatch):
    monkeypatch.setattr(local_server, "process_sites_meihua_request", lambda _payload: (_ for _ in ()).throw(RuntimeError(f"secret {ROOT}")))
    with running_server() as port:
        status, _headers, raw = request(port, "POST", "/api/v1/meihua", json.dumps(valid_request()).encode(), {"Content-Type": "application/json"})
    text = raw.decode()
    assert status == 500 and "Traceback" not in text and str(ROOT) not in text and "secret" not in text


@pytest.mark.parametrize("path", ["/", "/assets/app.css", "/assets/app.js"])
def test_static_routes_set_all_security_headers(path):
    with running_server() as port:
        _status, headers, _body = request(port, "GET", path)
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Frame-Options"] == "DENY"
    csp = headers["Content-Security-Policy"]
    for directive in ["default-src 'self'", "script-src 'self'", "style-src 'self'", "img-src 'self' data:", "connect-src 'self'", "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'"]:
        assert directive in csp


def test_api_headers_are_json_no_store_and_nosniff():
    with running_server() as port:
        _status, headers, _body = request(port, "POST", "/api/v1/meihua", b"{bad", {"Content-Type": "application/json"})
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"


def source_text():
    return "\n".join(path.read_text(encoding="utf-8") for path in [SITE / "index.html", SITE / "assets/app.css", SITE / "assets/app.js"])


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def parsed_elements():
    parser = ElementCollector()
    parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
    return parser.elements


def test_page_has_no_external_resources_or_inline_script():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert "http://" not in html and "https://" not in html and "<script>" not in html
    assert 'src="/assets/app.js?v=0.2.0"' in html and 'href="/assets/app.css?v=0.2.0"' in html


def test_favicon_is_a_single_embedded_svg_without_an_http_resource():
    icons = [attrs for tag, attrs in parsed_elements() if tag == "link" and "icon" in attrs.get("rel", "").split()]
    assert len(icons) == 1
    href = icons[0].get("href", "")
    assert icons[0].get("type") == "image/svg+xml"
    assert href.startswith("data:image/svg+xml,")
    assert not href.startswith(("/", "http://", "https://"))
    assert "<svg" in unquote(href.split(",", maxsplit=1)[1])


def test_form_fields_start_without_stale_error_associations():
    fields = {attrs["id"]: attrs for tag, attrs in parsed_elements() if tag in {"select", "input"} and "id" in attrs}
    for field_id in ["question-domain", "decision-goal", "time-horizon", "number-1", "number-2", "number-3", "ack-deterministic", "ack-narrative", "ack-structured"]:
        assert fields[field_id].get("aria-invalid") in {None, "false"}
        assert "form-error" not in fields[field_id].get("aria-describedby", "").split()
    assert "textarea" not in {tag for tag, _attrs in parsed_elements()}


def test_form_error_association_covers_all_fields_and_has_a_clear_lifecycle():
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    assert "number-${index}" in js
    for field_id in ["ack-deterministic", "ack-narrative"]:
        assert field_id in js
    for behavior in ["validatedFields", "markFieldInvalid", "clearFieldError", "clearFormError", 'field.setAttribute("aria-describedby"', 'field.removeAttribute("aria-describedby")', 'field.setAttribute("aria-invalid", "true")', 'field.setAttribute("aria-invalid", "false")']:
        assert behavior in js
    assert "resetExperience" in js and "clearFormError();" in js


@pytest.mark.parametrize("forbidden", ["localStorage", "sessionStorage", "indexedDB", "document.cookie", "innerHTML", "eval(", "new Function", "OPENAI_API_KEY", "api.openai.com"])
def test_frontend_avoids_storage_unsafe_dom_key_and_external_model(forbidden):
    assert forbidden not in source_text()


def test_frontend_posts_contract_only_to_same_origin_endpoint():
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    assert 'fetch("/api/v2/meihua"' in js
    for field in ["contract_version", "request_id", "question_domain", "decision_goal", "time_horizon", "numbers", "locale", "client_timestamp", "user_acknowledgements", "structured_question_confirmed"]:
        assert field in js
    for forbidden in ["question_text", "question_context", "base_hexagram:", "evidence:", "deterministic_conclusion:"]:
        assert forbidden not in js


def test_frontend_uses_finite_goals_clears_numbers_and_has_no_free_text():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    assert "<textarea" not in html
    assert "question-count" not in html and "maxlength=" not in html
    assert js.count("clearNumbers();") >= 3
    assert "GOALS_BY_DOMAIN" in js and "populateGoals" in js
    for domain in ["WORK_CAREER", "PROJECT_COOPERATION", "RELATIONSHIP_COMMUNICATION", "PERSONAL_PLANNING"]:
        assert domain in js
    assert 'setText("result-question", `服务端规范化问题：' in js


def test_structured_form_has_native_keyboard_order_and_summary_before_numbers():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    ids = ["question-domain", "decision-goal", "time-horizon", "summary-domain", "number-1", "number-2", "number-3", "ack-deterministic", "ack-narrative", "ack-structured", "submit-button"]
    positions = [html.index(f'id="{value}"') for value in ids]
    assert positions == sorted(positions)


def test_frontend_release_gate_is_visible_and_frozen():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for text in ["UNVERIFIED", "当前不收费", "当前不保存", "仅限本地原型", "这是一个边界清晰的本地原型"]:
        assert text in html


def test_frontend_has_loading_input_success_and_error_states():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    for marker in ["question-form", "loading-status", "result-content", "result-error", "evidence-summary"]:
        assert marker in html
    for code in ["INVALID_REQUEST", "INVALID_NUMBER_COUNT", "INVALID_NUMBER_TYPE", "CLIENT_INPUT_NOT_ACCEPTED", "ENGINE_ERROR"]:
        assert code in js


def test_frontend_rejects_malformed_release_envelope_before_render():
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    for guard in ["validEnvelope", "should_charge === false", "formal_report_persistence_allowed === false", "closed_beta_allowed === false", 'narrative_release_status === "UNVERIFIED"']:
        assert guard in js
    assert 'renderError(null, "响应格式异常")' in js


def test_frontend_success_view_names_all_required_deterministic_fields():
    text = source_text()
    for label in ["本次卦象与行动建议", "核心倾向", "导师式导读", "为什么会得到这个倾向", "接下来可以怎样做", "给自己的复盘问题", "本卦", "互卦", "变卦", "动爻", "体卦", "初始用卦", "变化用卦", "初始体用关系", "变化体用关系", "五行", "旺衰", "节气 / 月支", "程序证据", "查看技术详情"]:
        assert label in text


def test_frontend_renders_mentor_report_without_unsafe_html() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    for marker in ["mentor-opening", "reading-guide", "reasoning-list", "action-plan", "caution-list", "review-list", "mentor-boundary"]:
        assert f'id="{marker}"' in html
    for behavior in ["validMentorReport", "renderTextItems", "renderActions", "renderStringList"]:
        assert behavior in js
    assert "innerHTML" not in js


def test_frontend_product_view_keeps_internal_fields_in_closed_technical_details():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    before_details, technical = html.split('<details id="technical-details"', maxsplit=1)
    assert "Evidence" not in before_details
    assert "PYTHON_AUTHORITATIVE_ENGINE" not in before_details
    assert "SITES_MEIHUA_API_CONTRACT_V1" not in before_details
    assert "request_id" not in html and "audit_id" not in html
    assert "原始结论代码" in technical and "原始证据类型" in technical
    assert "open" not in technical.split(">", maxsplit=1)[0]


def test_frontend_reset_and_scroll_respect_local_only_and_reduced_motion():
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    assert "resetExperience" in js
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in js
    assert 'fetch("/api/v2/meihua"' in js
    assert js.count("fetch(") == 1


def test_adapter_has_no_algorithm_provider_key_or_external_client():
    source = Path(local_server.__file__).read_text(encoding="utf-8")
    for forbidden in ["cast_meihua", "ConclusionSynthesizer", "OPENAI_API_KEY", "openai", "requests.", "urllib.request", "httpx"]:
        assert forbidden not in source
    assert "process_sites_meihua_request" in source
