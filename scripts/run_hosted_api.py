"""Authenticated public transport for the authoritative Python chart engine."""

from __future__ import annotations

import argparse
import hmac
import hashlib
import json
import logging
import os
import re
import sys
import threading
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
from abalo_iching.application.sites_guided_intake_v1 import (  # noqa: E402
    GuidedIntakeError,
    process_sites_guided_intake_v1_request,
)
from abalo_iching.application.sites_meihua_service_v3 import (  # noqa: E402
    process_sites_meihua_v3_request,
)
from abalo_iching.application.sites_owner_preview_v1 import (  # noqa: E402
    process_sites_owner_preview_v1_request,
)

MAX_BODY_BYTES = 16 * 1024
OWNER_PREVIEW_MAX_BODY_BYTES = 32 * 1024
OWNER_PREVIEW_JOB_PREFIX = "/api/preview/v1/meihua/jobs/"
OWNER_PREVIEW_JOB_PATH = "/api/preview/v1/meihua/jobs"
GUIDED_INTAKE_PATH = "/api/intake/v1/turn"
# Completed jobs remain retrievable after the model polling lifecycle ends.
OWNER_PREVIEW_JOB_TTL_SECONDS = 45 * 60
OWNER_PREVIEW_MAX_ACTIVE_JOBS = 2
OWNER_PREVIEW_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MIN_KEY_LENGTH = 32
LOGGER = logging.getLogger("abalo.hosted_api")


def validate_engine_key(value: str | None) -> str:
    key = (value or "").strip()
    if len(key) < MIN_KEY_LENGTH:
        raise ValueError(f"ABALO_ENGINE_KEY must contain at least {MIN_KEY_LENGTH} characters")
    return key


class HostedApiServer(ThreadingHTTPServer):
    engine_key: str
    owner_preview_jobs: dict[str, dict[str, Any]]
    owner_preview_jobs_lock: threading.Lock


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
        if path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "abalo-authoritative-engine"})
            return
        if not path.startswith(OWNER_PREVIEW_JOB_PREFIX):
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"status": "unauthorized"})
            return
        request_id = path.removeprefix(OWNER_PREVIEW_JOB_PREFIX)
        if not OWNER_PREVIEW_REQUEST_ID_PATTERN.fullmatch(request_id):
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        with self.hosted_server.owner_preview_jobs_lock:
            self._cleanup_owner_preview_jobs_locked()
            job = self.hosted_server.owner_preview_jobs.get(request_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                return
            response = job.get("response")
            status = str(job["status"])
        if response is None:
            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
                    "request_id": request_id,
                    "status": status,
                },
            )
            return
        self._send_json(HTTPStatus.OK, response)

    def _cleanup_owner_preview_jobs_locked(self) -> None:
        cutoff = time.monotonic() - OWNER_PREVIEW_JOB_TTL_SECONDS
        expired = [
            request_id
            for request_id, job in self.hosted_server.owner_preview_jobs.items()
            if float(job["updated_at"]) < cutoff
        ]
        for request_id in expired:
            del self.hosted_server.owner_preview_jobs[request_id]

    def _run_owner_preview_job(self, request_id: str, payload: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            response = process_sites_owner_preview_v1_request(payload, input_provenance="REAL")
        except Exception:  # pragma: no cover - final background boundary
            LOGGER.exception("owner_preview_job_unhandled_error request_id=%s", request_id)
            response = {
                "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
                "request_id": request_id,
                "status": "PREVIEW_FAILED",
                "deterministic_result": None,
                "personalized_reading": None,
                "preview_meta": {
                    "owner_preview_only": True,
                    "should_charge": False,
                    "formal_persistence_allowed": False,
                },
                "error": "新版解读服务暂时不可用，请稍后再试。",
            }
        with self.hosted_server.owner_preview_jobs_lock:
            job = self.hosted_server.owner_preview_jobs.get(request_id)
            if job is not None:
                job["status"] = str(response.get("status", "PREVIEW_FAILED"))
                job["response"] = response
                job["updated_at"] = time.monotonic()
        LOGGER.info(
            "owner_preview_job status=%s request_id=%s latency_ms=%d",
            response.get("status", "UNKNOWN"),
            request_id,
            round((time.perf_counter() - started) * 1000),
        )

    def do_POST(self) -> None:  # noqa: N802
        started = time.perf_counter()
        path = self.path.split("?", 1)[0]
        if path not in {
            "/api/v2/meihua",
            "/api/v3/meihua",
            "/api/preview/v1/meihua",
            OWNER_PREVIEW_JOB_PATH,
            GUIDED_INTAKE_PATH,
        }:
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
        max_body_bytes = (
            OWNER_PREVIEW_MAX_BODY_BYTES
            if path in {"/api/preview/v1/meihua", OWNER_PREVIEW_JOB_PATH, GUIDED_INTAKE_PATH}
            else MAX_BODY_BYTES
        )
        if content_length < 0 or content_length > max_body_bytes:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "request_too_large"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_json"})
            return
        try:
            if path == GUIDED_INTAKE_PATH:
                session_id = str(payload.get("session_id", ""))[:32] if isinstance(payload, dict) else "invalid"
                turns = payload.get("turns", []) if isinstance(payload, dict) else []
                turn_count = len(turns) if isinstance(turns, list) else -1
                intake_enabled = os.environ.get("ABALO_GUIDED_INTAKE_ENABLED", "").strip().lower() == "true"
                owner_preview_enabled = os.environ.get("ABALO_OWNER_PREVIEW_ENABLED", "").strip().lower() == "true"
                if not (intake_enabled or owner_preview_enabled):
                    LOGGER.warning(
                        "guided_intake_unavailable reason=disabled session_id=%s turn_count=%d",
                        session_id,
                        turn_count,
                    )
                    self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "intake_disabled"})
                    return
                try:
                    response = process_sites_guided_intake_v1_request(payload)
                except ValueError:
                    LOGGER.warning(
                        "guided_intake_unavailable reason=invalid_request session_id=%s turn_count=%d",
                        session_id,
                        turn_count,
                    )
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                except GuidedIntakeError:
                    LOGGER.warning(
                        "guided_intake_unavailable reason=model_request session_id=%s turn_count=%d latency_ms=%d",
                        session_id,
                        turn_count,
                        round((time.perf_counter() - started) * 1000),
                    )
                    self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "intake_unavailable"})
                    return
                self._send_json(HTTPStatus.OK, response)
                LOGGER.info(
                    "guided_intake status=%s session_id=%s turn_count=%d latency_ms=%d",
                    response.get("status", "UNKNOWN"),
                    session_id,
                    turn_count,
                    round((time.perf_counter() - started) * 1000),
                )
                return
            if path == OWNER_PREVIEW_JOB_PATH:
                if not isinstance(payload, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                request_id = str(payload.get("request_id", ""))
                if not OWNER_PREVIEW_REQUEST_ID_PATTERN.fullmatch(request_id):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                digest = hashlib.sha256(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                with self.hosted_server.owner_preview_jobs_lock:
                    self._cleanup_owner_preview_jobs_locked()
                    job = self.hosted_server.owner_preview_jobs.get(request_id)
                    if job is not None and job["digest"] != digest:
                        self._send_json(HTTPStatus.CONFLICT, {"status": "request_id_conflict"})
                        return
                    if job is None:
                        active_jobs = sum(
                            1
                            for existing_job in self.hosted_server.owner_preview_jobs.values()
                            if existing_job.get("response") is None
                        )
                        if active_jobs >= OWNER_PREVIEW_MAX_ACTIVE_JOBS:
                            self._send_json(
                                HTTPStatus.TOO_MANY_REQUESTS,
                                {
                                    "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
                                    "request_id": request_id,
                                    "status": "PREVIEW_BUSY",
                                    "error": "当前已有解读正在生成，请稍后再试。",
                                },
                            )
                            return
                        job = {
                            "digest": digest,
                            "status": "RUNNING",
                            "response": None,
                            "updated_at": time.monotonic(),
                        }
                        self.hosted_server.owner_preview_jobs[request_id] = job
                        threading.Thread(
                            target=self._run_owner_preview_job,
                            args=(request_id, payload),
                            daemon=True,
                            name=f"owner-preview-{request_id[:24]}",
                        ).start()
                    response = job.get("response")
                    status = str(job["status"])
                if response is not None:
                    self._send_json(HTTPStatus.OK, response)
                else:
                    self._send_json(
                        HTTPStatus.ACCEPTED,
                        {
                            "contract_version": "SITES_OWNER_PREVIEW_CONTRACT_V1",
                            "request_id": request_id,
                            "status": status,
                        },
                    )
                return
            if path == "/api/preview/v1/meihua":
                processor = process_sites_owner_preview_v1_request
            elif path == "/api/v3/meihua":
                processor = process_sites_meihua_v3_request
            else:
                processor = process_sites_meihua_v2_request
            response = processor(payload, input_provenance="REAL")
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
    server.owner_preview_jobs = {}
    server.owner_preview_jobs_lock = threading.Lock()
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
