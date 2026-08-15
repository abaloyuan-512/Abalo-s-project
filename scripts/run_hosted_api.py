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
import unicodedata
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

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
from abalo_iching.application.sites_direct_reading_v3 import (  # noqa: E402
    CONTRACT_VERSION as DIRECT_READING_CONTRACT_VERSION,
    PROMPT_VERSION as DIRECT_READING_PROMPT_VERSION,
    OpenAIDirectReadingProvider,
    DirectReadingPreparedRequest,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
    public_direct_reading_payload,
)
from abalo_iching.application.sites_direct_high_product_v1 import (  # noqa: E402
    DirectHighEntryMode,
    build_direct_high_product_presentation,
)
from abalo_iching.application.sites_conditional_intake_product_v1 import (  # noqa: E402
    CONTRACT_VERSION as CONDITIONAL_INTAKE_CONTRACT_VERSION,
    OpenAIConditionalIntakeProvider,
    process_conditional_intake_request,
)
from abalo_iching.application.sites_owner_preview_v1 import (  # noqa: E402
    OWNER_PREVIEW_CONTRACT_VERSION,
    OWNER_PREVIEW_PROMPT_VERSION,
    OWNER_PREVIEW_VALIDATOR_VERSION,
    process_sites_owner_preview_v1_request,
)
from abalo_iching.application.sites_page8_reading_v1 import (  # noqa: E402
    PAGE8_READING_VERSION,
)

MAX_BODY_BYTES = 16 * 1024
OWNER_PREVIEW_MAX_BODY_BYTES = 32 * 1024
OWNER_PREVIEW_JOB_PREFIX = "/api/preview/v1/meihua/jobs/"
OWNER_PREVIEW_JOB_PATH = "/api/preview/v1/meihua/jobs"
DIRECT_READING_JOB_PREFIX = "/api/preview/v2/direct-reading/jobs/"
DIRECT_READING_JOB_PATH = "/api/preview/v2/direct-reading/jobs"
CONDITIONAL_INTAKE_PATH = "/api/preview/v2/direct-reading/intake"
GUIDED_INTAKE_PATH = "/api/intake/v1/turn"
# Completed jobs remain retrievable after the model polling lifecycle ends.
OWNER_PREVIEW_JOB_TTL_SECONDS = 45 * 60
OWNER_PREVIEW_MAX_ACTIVE_JOBS = 2
OWNER_PREVIEW_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
DIRECT_READING_REQUEST_ID_PATTERN = re.compile(r"^drv2-[a-f0-9]{16,64}$")
DIRECT_READING_STAGE_ORDER = {
    "CASTING": 0,
    "CAST_READY": 1,
    "MODEL_REQUESTED": 2,
    "MODEL_STREAMING": 3,
    "MODEL_COMPLETED": 4,
    "VALIDATING": 5,
}
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
    direct_reading_jobs: dict[str, dict[str, Any]]
    direct_reading_jobs_lock: threading.Lock
    conditional_intake_sessions: dict[str, dict[str, Any]]
    conditional_intake_sessions_lock: threading.Lock
    direct_reading_diagnostic_sink: Callable[[dict[str, Any]], None] | None
    direct_reading_internal_audit_sink: Callable[[dict[str, Any]], None] | None
    direct_reading_synthetic_diagnostic_confirmed: bool


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
            commit = os.environ.get("RENDER_GIT_COMMIT", "").strip()
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "abalo-authoritative-engine",
                    "git_commit": commit[:12] if commit else "unknown",
                    "owner_preview_contract": OWNER_PREVIEW_CONTRACT_VERSION,
                    "page8_contract": PAGE8_READING_VERSION,
                    "prompt_version": OWNER_PREVIEW_PROMPT_VERSION,
                    "validator_version": OWNER_PREVIEW_VALIDATOR_VERSION,
                },
            )
            return
        if not path.startswith((OWNER_PREVIEW_JOB_PREFIX, DIRECT_READING_JOB_PREFIX)):
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"status": "unauthorized"})
            return
        is_direct = path.startswith(DIRECT_READING_JOB_PREFIX)
        prefix = DIRECT_READING_JOB_PREFIX if is_direct else OWNER_PREVIEW_JOB_PREFIX
        request_id = path.removeprefix(prefix)
        pattern = DIRECT_READING_REQUEST_ID_PATTERN if is_direct else OWNER_PREVIEW_REQUEST_ID_PATTERN
        if not pattern.fullmatch(request_id):
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        jobs = self.hosted_server.direct_reading_jobs if is_direct else self.hosted_server.owner_preview_jobs
        jobs_lock = (
            self.hosted_server.direct_reading_jobs_lock
            if is_direct
            else self.hosted_server.owner_preview_jobs_lock
        )
        with jobs_lock:
            self._cleanup_jobs_locked(jobs)
            job = jobs.get(request_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                return
            response = job.get("response")
            status = str(job["status"])
        if response is None:
            elapsed_ms = max(0, round((time.monotonic() - float(job["started_at"])) * 1000))
            if is_direct:
                self._send_json(
                    HTTPStatus.ACCEPTED,
                    self._direct_pending_payload(request_id, job),
                )
                return
            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "contract_version": (
                        "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1"
                        if is_direct
                        else "SITES_OWNER_PREVIEW_CONTRACT_V1"
                    ),
                    "request_id": request_id,
                    "status": status,
                    "preview_meta": {
                        "stage": str(job.get("stage", "GENERATING")),
                        **({} if is_direct else {"elapsed_ms": elapsed_ms}),
                    },
                },
            )
            return
        self._send_json(HTTPStatus.OK, response)

    @staticmethod
    def _direct_pending_payload(request_id: str, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "contract_version": "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
            "request_id": request_id,
            "status": "RUNNING",
            "stage": str(job.get("stage", "CASTING")),
            "chart_facts": job.get("chart_facts"),
            "direct_reading": None,
            "error_code": None,
            "error_message": None,
            "retryable": False,
            "failure_stage": None,
        }

    def _cleanup_owner_preview_jobs_locked(self) -> None:
        self._cleanup_jobs_locked(self.hosted_server.owner_preview_jobs)

    @staticmethod
    def _cleanup_jobs_locked(jobs: dict[str, dict[str, Any]]) -> None:
        cutoff = time.monotonic() - OWNER_PREVIEW_JOB_TTL_SECONDS
        expired = [
            request_id
            for request_id, job in jobs.items()
            if float(job["updated_at"]) < cutoff
        ]
        for request_id in expired:
            del jobs[request_id]

    def _update_direct_stage(self, request_id: str, stage: str) -> None:
        if stage not in DIRECT_READING_STAGE_ORDER:
            return
        with self.hosted_server.direct_reading_jobs_lock:
            job = self.hosted_server.direct_reading_jobs.get(request_id)
            current = str(job.get("stage", "CASTING")) if job is not None else "CASTING"
            if (
                job is not None
                and job.get("response") is None
                and DIRECT_READING_STAGE_ORDER.get(stage, -1)
                >= DIRECT_READING_STAGE_ORDER.get(current, -1)
            ):
                job["stage"] = stage
                job["updated_at"] = time.monotonic()

    def _run_direct_reading_job(
        self,
        request_id: str,
        prepared: DirectReadingPreparedRequest,
        entry_mode: DirectHighEntryMode,
        route_audit: dict[str, Any],
    ) -> None:
        try:
            configured_effort = os.environ.get("ABALO_DIRECT_READING_REASONING_EFFORT", "high").strip().lower()
            reasoning_effort = configured_effort if configured_effort in {"medium", "high"} else "high"
            internal = process_prepared_direct_reading_v2_request(
                prepared,
                provider=OpenAIDirectReadingProvider(reasoning_effort=reasoning_effort),
                progress_callback=lambda stage: self._update_direct_stage(request_id, stage),
                diagnostic_sink=self.hosted_server.direct_reading_diagnostic_sink,
                synthetic_diagnostic_confirmed=(
                    self.hosted_server.direct_reading_synthetic_diagnostic_confirmed
                ),
            )
            if self.hosted_server.direct_reading_internal_audit_sink is not None:
                self.hosted_server.direct_reading_internal_audit_sink(
                    {
                        "request_id": request_id,
                        "outcome": str(internal.get("status", "UNKNOWN")),
                        "audit": internal.get("audit"),
                    }
                )
            response = public_direct_reading_payload(internal)
            if internal.get("status") == "SUCCESS":
                try:
                    presentation = build_direct_high_product_presentation(prepared, internal)
                except (TypeError, ValueError):
                    response = {
                        "contract_version": "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
                        "request_id": request_id,
                        "status": "BLOCKED_OUTPUT",
                        "direct_reading": None,
                        "product_presentation": None,
                        "direct_high": {
                            "entry_mode": entry_mode.value,
                            **route_audit,
                            "automatic_retries": 0,
                        },
                        "error_code": "P8_P9_PRODUCT_MAPPING_FAILED",
                        "error_message": "本次解卦未通过页面内容映射核验，未发布结果。",
                        "retryable": False,
                        "failure_stage": "CONTENT",
                    }
                else:
                    response["product_presentation"] = presentation.model_dump(mode="json")
                    response["direct_high"] = {
                        "entry_mode": entry_mode.value,
                        **route_audit,
                        "automatic_retries": 0,
                    }
        except Exception:  # pragma: no cover - final background boundary
            LOGGER.error(
                "direct_reading_job status=UNAVAILABLE error_code=UNHANDLED request_id=%s",
                request_id,
            )
            response = {
                "contract_version": "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
                "request_id": request_id,
                "status": "UNAVAILABLE",
                "direct_reading": None,
                "error_code": "SERVICE_UNAVAILABLE",
                "error_message": "解卦服务暂时不可用。",
                "retryable": False,
                "failure_stage": "PROVIDER",
            }
        with self.hosted_server.direct_reading_jobs_lock:
            job = self.hosted_server.direct_reading_jobs.get(request_id)
            if job is not None:
                job["status"] = str(response.get("status", "UNAVAILABLE"))
                job["stage"] = "COMPLETE" if response.get("status") == "SUCCESS" else "FAILED"
                job["response"] = response
                job["updated_at"] = time.monotonic()
        LOGGER.info("direct_reading_job status=%s request_id=%s", response.get("status", "UNKNOWN"), request_id)

    def _submit_conditional_intake(self, payload: dict[str, Any]) -> None:
        if payload.get("contract_version") != CONDITIONAL_INTAKE_CONTRACT_VERSION:
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_contract"})
            return
        enabled = os.environ.get("ABALO_CONDITIONAL_INTAKE_ENABLED", "").strip().lower() == "true"
        if not enabled:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "conditional_intake_disabled"})
            return
        response = process_conditional_intake_request(
            payload,
            provider=OpenAIConditionalIntakeProvider(),
        )
        if response.get("status") == "INVALID_REQUEST":
            self._send_json(HTTPStatus.BAD_REQUEST, response)
            return
        intake_id = str(response["intake_id"])
        with self.hosted_server.conditional_intake_sessions_lock:
            self.hosted_server.conditional_intake_sessions[intake_id] = {
                "question_sha256": response["original_question_sha_before"],
                "status": response["status"],
                "ambiguity_kind": response.get("ambiguity_kind"),
                "failure_code": response.get("failure_code"),
                "router_attempts": response["router_attempts"],
                "consumed": False,
                "created_at": time.monotonic(),
            }
        self._send_json(HTTPStatus.OK, response)

    @staticmethod
    def _canonical_question_sha(question: object) -> str | None:
        if type(question) is not str:
            return None
        return hashlib.sha256(question.encode("utf-8")).hexdigest().upper()

    def _intake_route_for_high(
        self,
        payload: dict[str, Any],
        entry_mode: DirectHighEntryMode,
        *,
        consume: bool,
    ) -> tuple[dict[str, Any], dict[str, str] | None] | None:
        intake_id = payload.get("intake_id")
        if intake_id is None:
            return ({
                "route": "DIRECT_HIGH",
                "router_attempts": 0,
                "intake_status": "BYPASSED",
                "router_failure_code": None,
            }, None)
        if type(intake_id) is not str:
            return None
        with self.hosted_server.conditional_intake_sessions_lock:
            session = self.hosted_server.conditional_intake_sessions.get(intake_id)
            if session is None or session.get("consumed") is True:
                return None
            if session.get("question_sha256") != self._canonical_question_sha(payload.get("question_text")):
                return None
            decision = session.get("status")
            answer = payload.get("clarification_answer")
            optional_context: dict[str, str] | None = None
            if decision == "PASS":
                if entry_mode is not DirectHighEntryMode.CLEAR or answer is not None:
                    return None
                intake_status = "PASSED"
            elif decision == "ASK_ONCE":
                if entry_mode is DirectHighEntryMode.CONFIRMED:
                    if type(answer) is not str:
                        return None
                    normalized = unicodedata.normalize("NFC", answer).strip()
                    if normalized != answer or not 1 <= len(answer) <= 400:
                        return None
                    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in answer):
                        return None
                    optional_context = {"discernment_note": f"[用户一次澄清原话] {answer}"}
                    intake_status = "ASKED_ONCE_ANSWERED"
                elif entry_mode is DirectHighEntryMode.SKIP and answer is None:
                    intake_status = "ASKED_ONCE_SKIPPED"
                else:
                    return None
            else:
                return None
            if consume:
                session["consumed"] = True
            return ({
                "route": "CONDITIONAL_INTAKE_THEN_HIGH",
                "router_attempts": int(session.get("router_attempts", 1)),
                "intake_status": intake_status,
                "router_failure_code": session.get("failure_code"),
            }, optional_context)

    def _submit_direct_reading_job(self, payload: dict[str, Any]) -> None:
        request_id = str(payload.get("request_id", ""))
        if not DIRECT_READING_REQUEST_ID_PATTERN.fullmatch(request_id):
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
            return
        enabled = os.environ.get("ABALO_DIRECT_READING_V2_ENABLED", "").strip().lower() == "true"
        if not enabled:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "direct_reading_disabled"})
            return
        if payload.get("contract_version") != DIRECT_READING_CONTRACT_VERSION:
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_contract"})
            return
        try:
            entry_mode = DirectHighEntryMode(payload.get("entry_mode", "CLEAR"))
        except (TypeError, ValueError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_entry_mode"})
            return
        digest = hashlib.sha256(
            json.dumps(
                {"payload": payload, "prompt_version": DIRECT_READING_PROMPT_VERSION},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        jobs = self.hosted_server.direct_reading_jobs
        with self.hosted_server.direct_reading_jobs_lock:
            self._cleanup_jobs_locked(jobs)
            job = jobs.get(request_id)
            if job is not None and job["digest"] != digest:
                self._send_json(HTTPStatus.CONFLICT, {"status": "request_id_conflict"})
                return
            if job is not None:
                response = job.get("response")
                if response is not None:
                    self._send_json(HTTPStatus.OK, response)
                else:
                    self._send_json(HTTPStatus.ACCEPTED, self._direct_pending_payload(request_id, job))
                return
            intake_route = self._intake_route_for_high(payload, entry_mode, consume=False)
            if intake_route is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_or_consumed_intake"})
                return
            active_jobs = sum(1 for item in jobs.values() if item.get("response") is None)
            if active_jobs >= OWNER_PREVIEW_MAX_ACTIVE_JOBS:
                self._send_json(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    {
                        "contract_version": "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
                        "request_id": request_id,
                        "status": "PREVIEW_BUSY",
                        "error": "当前已有解读正在生成，请稍后再试。",
                    },
                )
                return
            job = {
                "digest": digest,
                "status": "RUNNING",
                "stage": "CASTING",
                "chart_facts": None,
                "response": None,
                "started_at": time.monotonic(),
                "updated_at": time.monotonic(),
            }
            jobs[request_id] = job

        intake_route = self._intake_route_for_high(payload, entry_mode, consume=True)
        if intake_route is None:
            with self.hosted_server.direct_reading_jobs_lock:
                jobs.pop(request_id, None)
            self._send_json(HTTPStatus.CONFLICT, {"status": "intake_already_consumed"})
            return
        route_audit, optional_context = intake_route

        prepared = prepare_direct_reading_v2_request(
            {
                "question_text": payload.get("question_text"),
                "numbers": payload.get("numbers"),
                "optional_context": optional_context,
            },
            request_id=request_id,
        )
        if isinstance(prepared, dict):
            response = public_direct_reading_payload(prepared)
            with self.hosted_server.direct_reading_jobs_lock:
                job = jobs[request_id]
                job["status"] = str(response.get("status", "INVALID_REQUEST"))
                job["stage"] = "FAILED"
                job["response"] = response
                job["updated_at"] = time.monotonic()
            self._send_json(HTTPStatus.OK, response)
            return

        with self.hosted_server.direct_reading_jobs_lock:
            job = jobs[request_id]
            job["stage"] = "CAST_READY"
            job["chart_facts"] = prepared.chart_facts.model_dump(mode="json")
            job["updated_at"] = time.monotonic()
        threading.Thread(
            target=self._run_direct_reading_job,
            args=(request_id, prepared, entry_mode, route_audit),
            daemon=True,
            name=f"direct-reading-{request_id[:24]}",
        ).start()
        self._send_json(HTTPStatus.ACCEPTED, self._direct_pending_payload(request_id, job))

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
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        preview_meta = response.get("preview_meta")
        response["preview_meta"] = {
            **(preview_meta if isinstance(preview_meta, dict) else {}),
            "stage": "COMPLETE" if response.get("status") == "SUCCESS" else "FAILED",
            "elapsed_ms": elapsed_ms,
        }
        with self.hosted_server.owner_preview_jobs_lock:
            job = self.hosted_server.owner_preview_jobs.get(request_id)
            if job is not None:
                job["status"] = str(response.get("status", "PREVIEW_FAILED"))
                job["stage"] = str(response["preview_meta"]["stage"])
                job["response"] = response
                job["updated_at"] = time.monotonic()
        LOGGER.info(
            "owner_preview_job status=%s request_id=%s latency_ms=%d",
            response.get("status", "UNKNOWN"),
            request_id,
            elapsed_ms,
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
            DIRECT_READING_JOB_PATH,
            CONDITIONAL_INTAKE_PATH,
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
            if path == CONDITIONAL_INTAKE_PATH:
                if not isinstance(payload, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                self._submit_conditional_intake(payload)
                return
            if path == DIRECT_READING_JOB_PATH:
                if not isinstance(payload, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                request_id = str(payload.get("request_id", ""))
                try:
                    self._submit_direct_reading_job(payload)
                except Exception:  # final privacy boundary for deterministic preparation
                    safe_request_id = (
                        request_id
                        if DIRECT_READING_REQUEST_ID_PATTERN.fullmatch(request_id)
                        else "unavailable"
                    )
                    LOGGER.error(
                        "direct_reading_submit status=UNAVAILABLE error_code=UNHANDLED request_id=%s",
                        safe_request_id,
                    )
                    response = {
                        "contract_version": "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
                        "request_id": safe_request_id,
                        "status": "UNAVAILABLE",
                        "direct_reading": None,
                        "error_code": "SERVICE_UNAVAILABLE",
                        "error_message": "解卦服务暂时不可用。",
                        "retryable": False,
                        "failure_stage": "ENGINE",
                    }
                    if safe_request_id != "unavailable":
                        with self.hosted_server.direct_reading_jobs_lock:
                            job = self.hosted_server.direct_reading_jobs.get(safe_request_id)
                            if job is not None:
                                job["status"] = "UNAVAILABLE"
                                job["stage"] = "FAILED"
                                job["response"] = response
                                job["updated_at"] = time.monotonic()
                    self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, response)
                return
            if path == OWNER_PREVIEW_JOB_PATH:
                if not isinstance(payload, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                request_id = str(payload.get("request_id", ""))
                is_direct = False
                pattern = DIRECT_READING_REQUEST_ID_PATTERN if is_direct else OWNER_PREVIEW_REQUEST_ID_PATTERN
                if not pattern.fullmatch(request_id):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request"})
                    return
                if is_direct:
                    enabled = os.environ.get("ABALO_DIRECT_READING_V2_ENABLED", "").strip().lower() == "true"
                    if not enabled:
                        self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "direct_reading_disabled"})
                        return
                    if payload.get("contract_version") != DIRECT_READING_CONTRACT_VERSION:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_contract"})
                        return
                digest = hashlib.sha256(
                    json.dumps(
                        {
                            "payload": payload,
                            "prompt_version": DIRECT_READING_PROMPT_VERSION if is_direct else "legacy-v1",
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                jobs = self.hosted_server.direct_reading_jobs if is_direct else self.hosted_server.owner_preview_jobs
                jobs_lock = (
                    self.hosted_server.direct_reading_jobs_lock
                    if is_direct
                    else self.hosted_server.owner_preview_jobs_lock
                )
                with jobs_lock:
                    self._cleanup_jobs_locked(jobs)
                    job = jobs.get(request_id)
                    if job is not None and job["digest"] != digest:
                        self._send_json(HTTPStatus.CONFLICT, {"status": "request_id_conflict"})
                        return
                    if job is None:
                        active_jobs = sum(
                            1
                            for existing_job in jobs.values()
                            if existing_job.get("response") is None
                        )
                        if active_jobs >= OWNER_PREVIEW_MAX_ACTIVE_JOBS:
                            self._send_json(
                                HTTPStatus.TOO_MANY_REQUESTS,
                                {
                                    "contract_version": (
                                        "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1"
                                        if is_direct
                                        else "SITES_OWNER_PREVIEW_CONTRACT_V1"
                                    ),
                                    "request_id": request_id,
                                    "status": "PREVIEW_BUSY",
                                    "error": "当前已有解读正在生成，请稍后再试。",
                                },
                            )
                            return
                        job = {
                            "digest": digest,
                            "status": "RUNNING",
                            "stage": "CASTING" if is_direct else "GENERATING_AND_VALIDATING",
                            "response": None,
                            "started_at": time.monotonic(),
                            "updated_at": time.monotonic(),
                        }
                        jobs[request_id] = job
                        threading.Thread(
                            target=(self._run_direct_reading_job if is_direct else self._run_owner_preview_job),
                            args=(request_id, payload),
                            daemon=True,
                            name=f"{'direct-reading' if is_direct else 'owner-preview'}-{request_id[:24]}",
                        ).start()
                    response = job.get("response")
                    status = str(job["status"])
                if response is not None:
                    self._send_json(HTTPStatus.OK, response)
                else:
                    elapsed_ms = max(0, round((time.monotonic() - float(job["started_at"])) * 1000))
                    self._send_json(
                        HTTPStatus.ACCEPTED,
                        {
                            "contract_version": (
                                "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1"
                                if is_direct
                                else "SITES_OWNER_PREVIEW_CONTRACT_V1"
                            ),
                            "request_id": request_id,
                            "status": status,
                            "preview_meta": {
                                "stage": str(job.get("stage", "GENERATING")),
                                **({} if is_direct else {"elapsed_ms": elapsed_ms}),
                            },
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


def create_server(
    host: str,
    port: int,
    engine_key: str,
    *,
    direct_reading_diagnostic_sink: Callable[[dict[str, Any]], None] | None = None,
    direct_reading_internal_audit_sink: Callable[[dict[str, Any]], None] | None = None,
    direct_reading_synthetic_diagnostic_confirmed: bool = False,
) -> HostedApiServer:
    if not host or port < 0 or port > 65535:
        raise ValueError("invalid hosted API address")
    if (
        (direct_reading_diagnostic_sink is not None or direct_reading_internal_audit_sink is not None)
        and not direct_reading_synthetic_diagnostic_confirmed
    ):
        raise ValueError("direct-reading private sinks require a confirmed synthetic server")
    server = HostedApiServer((host, port), HostedApiHandler)
    server.engine_key = validate_engine_key(engine_key)
    server.owner_preview_jobs = {}
    server.owner_preview_jobs_lock = threading.Lock()
    server.direct_reading_jobs = {}
    server.direct_reading_jobs_lock = threading.Lock()
    server.conditional_intake_sessions = {}
    server.conditional_intake_sessions_lock = threading.Lock()
    server.direct_reading_diagnostic_sink = direct_reading_diagnostic_sink
    server.direct_reading_internal_audit_sink = direct_reading_internal_audit_sink
    server.direct_reading_synthetic_diagnostic_confirmed = (
        direct_reading_synthetic_diagnostic_confirmed
    )
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
