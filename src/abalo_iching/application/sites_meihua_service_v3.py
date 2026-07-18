"""Sites V3: concrete user question plus non-calculative decision context."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from .sites_clarity_report_v3 import build_clarity_report
from .sites_meihua_service import INVALID_REQUEST_ID_FALLBACK, _safe_audit_id, _valid_client_timestamp, validate_and_normalize_request_id
from .sites_meihua_service_v2 import process_sites_meihua_v2_request
from .sites_question_context_v1 import CONTEXT_VERSION, normalize_question_text, parse_question_context
from .sites_structured_question_v1 import generate_structured_question, parse_structured_fields

CONTRACT_VERSION_V3 = "SITES_MEIHUA_API_CONTRACT_V3"

_ALLOWED_FIELDS = {
    "contract_version", "request_id", "question_text", "question_domain", "decision_goal",
    "time_horizon", "decision_stage", "key_uncertainty", "numbers", "locale",
    "client_timestamp", "user_acknowledgements",
}


def _error(request_id: str, code: str, message: str, generated_at: datetime) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION_V3,
        "request_id": request_id,
        "status": "VALIDATION_ERROR",
        "deterministic_result": None,
        "narrative": {"status": "UNVERIFIED", "available": False, "content": None, "blocked_reason": "AI narrative has not passed live validation.", "live_validation_status": "BLOCKED_BY_EXECUTION_POLICY"},
        "release_gate": {"should_charge": False, "formal_report_persistence_allowed": False, "closed_beta_allowed": False, "narrative_release_status": "UNVERIFIED"},
        "audit": {"engine_version": None, "contract_version": CONTRACT_VERSION_V3, "calculation_source": "PYTHON_AUTHORITATIVE_ENGINE", "generated_at": generated_at.isoformat(), "synthetic_or_real_input": "UNSPECIFIED", "request_hash": None, "audit_id": _safe_audit_id(request_id), "question_context_version": None, "question_text_used_for_calculation": False},
        "errors": [{"error_code": code, "message": message, "request_id": request_id, "audit_id": _safe_audit_id(request_id)}],
    }


def process_sites_meihua_v3_request(
    request_payload: Any,
    *,
    clock: Callable[[], datetime] | None = None,
    input_provenance: Literal["SYNTHETIC", "REAL"] = "SYNTHETIC",
) -> dict[str, Any]:
    now = clock or (lambda: datetime.now().astimezone())
    generated_at = now()
    if generated_at.tzinfo is None:
        raise ValueError("clock must return an aware datetime")
    request_id = validate_and_normalize_request_id(request_payload.get("request_id") if isinstance(request_payload, dict) else None) or INVALID_REQUEST_ID_FALLBACK
    if not isinstance(request_payload, dict):
        return _error(request_id, "INVALID_REQUEST", "请求必须是 JSON 对象。", generated_at)
    if set(request_payload) - _ALLOWED_FIELDS:
        return _error(request_id, "INVALID_REQUEST", "请求包含不支持的字段。", generated_at)
    if request_payload.get("contract_version") != CONTRACT_VERSION_V3:
        return _error(request_id, "INVALID_REQUEST", f"contract_version 必须为 {CONTRACT_VERSION_V3}。", generated_at)
    if validate_and_normalize_request_id(request_payload.get("request_id")) is None:
        return _error(request_id, "INVALID_REQUEST", "request_id 格式不正确。", generated_at)
    try:
        question_text = normalize_question_text(request_payload.get("question_text"))
        domain, goal, horizon = parse_structured_fields(request_payload.get("question_domain"), request_payload.get("decision_goal"), request_payload.get("time_horizon"))
        generate_structured_question(domain, goal, horizon)
        stage, uncertainty = parse_question_context(request_payload.get("decision_stage"), request_payload.get("key_uncertainty"))
    except ValueError:
        return _error(request_id, "INVALID_REQUEST", "问题或结构化选择不完整，请检查后重试。", generated_at)
    if request_payload.get("locale") != "zh-CN" or not _valid_client_timestamp(request_payload.get("client_timestamp")):
        return _error(request_id, "INVALID_REQUEST", "语言或客户端时间格式不正确。", generated_at)
    expected_ack = {"deterministic_only": True, "narrative_unverified": True, "question_text_not_evidence": True}
    if request_payload.get("user_acknowledgements") != expected_ack:
        return _error(request_id, "INVALID_REQUEST", "必须确认排盘与问题文本的使用边界。", generated_at)
    v2_payload = {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V2",
        "request_id": request_id,
        "question_domain": domain.value,
        "decision_goal": goal.value,
        "time_horizon": horizon.value,
        "numbers": request_payload.get("numbers"),
        "locale": "zh-CN",
        "client_timestamp": request_payload.get("client_timestamp"),
        "user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True, "structured_question_confirmed": True},
    }
    response = process_sites_meihua_v2_request(
        v2_payload,
        clock=lambda: generated_at,
        input_provenance=input_provenance,
        include_cultural_reading=True,
    )
    response["contract_version"] = CONTRACT_VERSION_V3
    response["audit"]["contract_version"] = CONTRACT_VERSION_V3
    response["audit"].pop("question_template_version", None)
    response["audit"]["question_context_version"] = CONTEXT_VERSION
    response["audit"]["question_text_used_for_calculation"] = False
    if response["status"] != "SUCCESS":
        return response
    validated_for_hash = {**request_payload, "question_text": question_text}
    response["audit"]["request_hash"] = hashlib.sha256(json.dumps(validated_for_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    response["structured_intake"].update({"decision_stage": stage.value, "key_uncertainty": uncertainty.value})
    response["user_question"] = question_text
    response["normalized_question"] = question_text
    response["question_context_version"] = CONTEXT_VERSION
    response["deterministic_result"]["clarity_report"] = build_clarity_report(
        response["deterministic_result"], domain, goal, horizon, stage, uncertainty
    )
    return response
