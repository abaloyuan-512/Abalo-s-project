"""Authenticated public transport for the authoritative Python chart engine."""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
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

from abalo_iching.application.sites_meihua_service_v2 import (  # noqa: E402
    process_sites_meihua_v2_request,
)

MAX_BODY_BYTES = 16 * 1024
MIN_KEY_LENGTH = 32
LOGGER = logging.getLogger("abalo.hosted_api")


def validate_engine_key(value: str | None) -> str:
    key = (value or "").strip()
    if len(key) < MIN_KEY_LENGTH:
        raise ValueError(f"ABALO_ENGINE_KEY must contain at least {MIN_KEY_LENGTH} characters")
    return key


class HostedApiServer(ThreadingHTTPServer):
    engine_key: str


class HostedApiHandler(BaseHTTPRequestHandler):
    server_version = "AbaloEngine/1"
    sys_version = ""

    @property
    def hosted_server(self) -> HostedApiServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, _format: str, *args: object) -> None:
        del args

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        provided = self.headers.get("X-Abalo-Engine-Key", "")
        return hmac.compare_digest(provided.encode("utf-8"), self.hosted_server.engine_key.encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/healthz":
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        self._send_json(HTTPStatus.OK, {"status": "ok", "service": "abalo-authoritative-engine"})

    def do_POST(self) -> None:  # noqa: N802
        started = time.perf_counter()
        if self.path.split("?", 1)[0] != "/api/v2/meihua":
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"status": "unauthorized"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"status": "unsupported_media_type"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "request_too_large"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_json"})
            return
        try:
            response = process_sites_meihua_v2_request(payload, input_provenance="REAL")
        except Exception:  # pragma: no cover - final network boundary
            LOGGER.exception("hosted_engine_unhandled_error")
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "engine_unavailable"})
            return
        self._send_json(HTTPStatus.OK, response)
        LOGGER.info(
            "status=%s audit_id=%s latency_ms=%d",
            response.get("status", "UNKNOWN"),
            response.get("audit", {}).get("audit_id", "unavailable"),
            round((time.perf_counter() - started) * 1000),
        )


def create_server(host: str, port: int, engine_key: str) -> HostedApiServer:
    if not host or port < 0 or port > 65535:
        raise ValueError("invalid hosted API address")
    server = HostedApiServer((host, port), HostedApiHandler)
    server.engine_key = validate_engine_key(engine_key)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the authenticated Abalo hosted API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args(argv)
    try:
        server = create_server(args.host, args.port, os.environ.get("ABALO_ENGINE_KEY", ""))
    except ValueError as exc:
        print(f"START_BLOCKED: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(f"listening on {args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
