"""Loopback-only HTTP adapter for the Sites Phase 3B local prototype."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching.application.sites_meihua_service import (  # noqa: E402
    process_sites_meihua_request,
)

_contract_error_response = process_sites_meihua_request

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_BODY_BYTES = 16 * 1024
SITE_ROOT = ROOT / "sites" / "phase3b-prototype"
LOGGER = logging.getLogger("sites.phase3b.local")

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

STATIC_ROUTES = {
    "/": (SITE_ROOT / "index.html", "text/html; charset=utf-8"),
    "/assets/app.css": (SITE_ROOT / "assets" / "app.css", "text/css; charset=utf-8"),
    "/assets/app.js": (SITE_ROOT / "assets" / "app.js", "text/javascript; charset=utf-8"),
}


def validate_host(host: str) -> str:
    """Keep the prototype unambiguously bound to IPv4 loopback."""
    if host != HOST:
        raise ValueError("Phase 3B local prototype only accepts --host 127.0.0.1")
    return host


def _adapter_error() -> dict[str, Any]:
    """Reuse Contract V1's safe validation envelope without invoking the engine."""
    return _contract_error_response({})


class Phase3BRequestHandler(BaseHTTPRequestHandler):
    """Serve a fixed file allowlist and one Contract V1 endpoint."""

    server_version = "SitesPhase3BLocal/1"
    sys_version = ""

    def log_message(self, _format: str, *args: object) -> None:
        del args

    def _send_headers(self, status: int, content_type: str, size: int, *, no_store: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        if no_store:
            self.send_header("Cache-Control", "no-store")
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()

    def _send_bytes(self, status: int, body: bytes, content_type: str, *, no_store: bool = False) -> None:
        self._send_headers(status, content_type, len(body), no_store=no_store)
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8", no_store=True)

    def _safe_log(self, status: int, response: dict[str, Any], started: float) -> None:
        request_id = response.get("request_id", "invalid-request")
        audit_id = response.get("audit", {}).get("audit_id", "unavailable")
        errors = response.get("errors") or []
        classification = errors[0].get("error_code", "NONE") if errors else "NONE"
        LOGGER.info(
            "request_id=%s status=%s audit_id=%s latency_ms=%d error=%s",
            request_id,
            status,
            audit_id,
            round((time.perf_counter() - started) * 1000),
            classification,
        )

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "sites-phase3b-local-prototype",
                    "network_scope": "loopback-only",
                    "narrative_status": "UNVERIFIED",
                },
            )
            return
        route = STATIC_ROUTES.get(path)
        if route is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        file_path, content_type = route
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "unavailable"})
            return
        self._send_bytes(HTTPStatus.OK, body, content_type)

    def do_POST(self) -> None:  # noqa: N802
        started = time.perf_counter()
        if self.path.split("?", 1)[0] != "/api/v1/meihua":
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            response = _adapter_error()
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, response)
            self._safe_log(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, response, started)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            response = _adapter_error()
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, response)
            self._safe_log(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, response, started)
            return
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            response = _adapter_error()
            self._send_json(HTTPStatus.BAD_REQUEST, response)
            self._safe_log(HTTPStatus.BAD_REQUEST, response, started)
            return
        try:
            response = process_sites_meihua_request(payload)
        except Exception:  # pragma: no cover - defensive transport boundary
            response = _adapter_error()
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, response)
            self._safe_log(HTTPStatus.INTERNAL_SERVER_ERROR, response, started)
            return
        self._send_json(HTTPStatus.OK, response)
        self._safe_log(HTTPStatus.OK, response, started)


def create_server(host: str = HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    validate_host(host)
    if port < 0 or port > 65535:
        raise ValueError("port must be between 0 and 65535")
    return ThreadingHTTPServer((host, port), Phase3BRequestHandler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the loopback-only Sites Phase 3B prototype")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        server = create_server(args.host, args.port)
    except ValueError as exc:
        print(f"START_BLOCKED: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(f"http://{HOST}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
