"""Offline verification for the loopback-only Sites Phase 3B prototype."""

from __future__ import annotations

import http.client
import json
import sys
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import run_sites_phase3b_local_server as server_module  # noqa: E402

SITE = ROOT / "sites" / "phase3b-prototype"
SCHEMA = json.loads((ROOT / "contracts/sites_meihua_v1/response.schema.json").read_text(encoding="utf-8"))


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))


def exchange(port: int, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def main() -> int:
    checks: list[tuple[str, bool]] = []
    add = lambda name, passed: checks.append((name, bool(passed)))
    add("loopback accepted", server_module.validate_host("127.0.0.1") == "127.0.0.1")
    for host in ["0.0.0.0", "localhost", "192.168.1.8"]:
        try:
            server_module.validate_host(host)
            rejected = False
        except ValueError:
            rejected = True
        add(f"non-loopback rejected: {host}", rejected)

    server = server_module.create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    try:
        route_results = {}
        for path in ["/", "/assets/app.css", "/assets/app.js"]:
            route_results[path] = exchange(port, "GET", path)
            add(f"route 200: {path}", route_results[path][0] == 200)
        health_status, _health_headers, health_raw = exchange(port, "GET", "/healthz")
        health = json.loads(health_raw)
        add("healthz safe", health_status == 200 and health["network_scope"] == "loopback-only" and health["narrative_status"] == "UNVERIFIED")

        payload = {
            "contract_version": "SITES_MEIHUA_API_CONTRACT_V1",
            "request_id": "phase3b-synthetic-verification-001",
            "question_text": "我应该如何更稳妥地推进当前合作？",
            "numbers": [100, 27, 368],
            "locale": "zh-CN",
            "client_timestamp": "2026-07-13T10:00:00+08:00",
            "user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True},
        }
        status, headers, raw = exchange(port, "POST", "/api/v1/meihua", json.dumps(payload, ensure_ascii=False).encode(), {"Content-Type": "application/json"})
        response = json.loads(raw)
        jsonschema.validate(response, SCHEMA)
        add("valid request success", status == 200 and response["status"] == "SUCCESS")
        add("python engine source", response["audit"]["calculation_source"] == "PYTHON_AUTHORITATIVE_ENGINE")
        add("release gate frozen", response["narrative"]["status"] == "UNVERIFIED" and not any([response["release_gate"]["should_charge"], response["release_gate"]["formal_report_persistence_allowed"], response["release_gate"]["closed_beta_allowed"]]))
        add("api no-store", headers.get("Cache-Control") == "no-store")

        bad_status, _bad_headers, bad_raw = exchange(port, "POST", "/api/v1/meihua", b"{bad", {"Content-Type": "application/json"})
        jsonschema.validate(json.loads(bad_raw), SCHEMA)
        add("invalid json safe", bad_status == 400 and b"Traceback" not in bad_raw)
        type_status, _type_headers, type_raw = exchange(port, "POST", "/api/v1/meihua", b"x", {"Content-Type": "text/plain"})
        jsonschema.validate(json.loads(type_raw), SCHEMA)
        add("content type enforced", type_status == 415)
        large_status, _large_headers, large_raw = exchange(port, "POST", "/api/v1/meihua", b"", {"Content-Type": "application/json", "Content-Length": str(server_module.MAX_BODY_BYTES + 1)})
        jsonschema.validate(json.loads(large_raw), SCHEMA)
        add("body cap enforced", large_status == 413)
        missing_status, _missing_headers, missing_raw = exchange(port, "GET", "/unknown")
        add("unknown route safe", missing_status == 404 and b"Directory listing" not in missing_raw)

        csp = route_results["/"][1].get("Content-Security-Policy", "")
        add("csp complete", all(item in csp for item in ["default-src 'self'", "script-src 'self'", "style-src 'self'", "connect-src 'self'", "object-src 'none'", "frame-ancestors 'none'"]))
        add("security headers", all(route_results["/"][1].get(name) == value for name, value in {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"}.items()))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    frontend_sources = "\n".join(path.read_text(encoding="utf-8") for path in [SITE / "index.html", SITE / "assets/app.css", SITE / "assets/app.js"])
    server_source = Path(server_module.__file__).read_text(encoding="utf-8")
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/app.js").read_text(encoding="utf-8")
    parser = ElementCollector()
    parser.feed(html)
    for forbidden in ["http://", "https://", "OPENAI_API_KEY", "api.openai.com", "localStorage", "sessionStorage", "indexedDB", "document.cookie", "innerHTML", "eval(", "new Function"]:
        add(f"forbidden source absent: {forbidden}", forbidden not in frontend_sources)
    add("no inline script", "<script>" not in html)
    icons = [attrs for tag, attrs in parser.elements if tag == "link" and "icon" in (attrs.get("rel") or "").split()]
    icon_href = icons[0].get("href") or "" if len(icons) == 1 else ""
    add("favicon is embedded data svg", len(icons) == 1 and icons[0].get("type") == "image/svg+xml" and icon_href.startswith("data:image/svg+xml,") and "<svg" in unquote(icon_href.split(",", maxsplit=1)[1]))
    add("favicon adds no http resource", bool(icon_href) and not icon_href.startswith(("/", "http://", "https://")))
    fields = {attrs["id"]: attrs for tag, attrs in parser.elements if tag in {"textarea", "input"} and attrs.get("id")}
    field_ids = ["question", "number-1", "number-2", "number-3", "ack-deterministic", "ack-narrative"]
    add("form fields start without stale errors", all(fields[field_id].get("aria-invalid") in {None, "false"} and "form-error" not in (fields[field_id].get("aria-describedby") or "").split() for field_id in field_ids))
    add("form error association lifecycle present", all(marker in js for marker in ["validatedFields", "markFieldInvalid", "clearFieldError", "clearFormError", 'field.setAttribute("aria-describedby"', 'field.removeAttribute("aria-describedby")']))
    add("release gate displayed", all(text in html for text in ["UNVERIFIED", "当前不收费", "当前不保存", "仅限本地原型"]))
    add("same-origin service call", 'fetch("/api/v1/meihua"' in frontend_sources)
    add("adapter delegates", "process_sites_meihua_request" in server_source)
    add("no adapter algorithm", "cast_meihua" not in server_source)

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"PHASE3B_PROTOTYPE_CHECKS={len(checks)}")
    print(f"PHASE3B_PROTOTYPE_FAILED={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
