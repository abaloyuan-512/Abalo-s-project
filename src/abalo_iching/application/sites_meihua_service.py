"""Sites Phase 3A adapter over the authoritative deterministic Python engine."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.release import narrative_release_snapshot
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.meihua import MeihuaInput, cast_meihua
from abalo_iching.meihua.exceptions import InputValidationError

CONTRACT_VERSION = "SITES_MEIHUA_API_CONTRACT_V1"
LIVE_VALIDATION_STATUS = "BLOCKED_BY_EXECUTION_POLICY"
_ALLOWED_FIELDS = {
    "contract_version", "request_id", "question_text", "numbers", "locale",
    "client_timestamp", "user_acknowledgements",
}
_CLIENT_DERIVED_FIELDS = {
    "base_hexagram", "mutual_hexagram", "changed_hexagram", "moving_line",
    "body_use", "five_elements", "seasonal_strength", "deterministic_conclusion",
}
_CLIENT_EVIDENCE_FIELDS = {"evidence", "evidence_ids", "evidence_refs", "evidence_summary"}


def _now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def _safe_audit_id(request_id: str) -> str:
    return "audit-" + hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:16]


def safe_request_id(value: Any) -> str:
    """Return only a bounded, printable request ID suitable for public errors."""
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        return "invalid-request"
    if any(unicodedata.category(character).startswith("C") for character in value):
        return "invalid-request"
    return value


def _gate() -> dict[str, Any]:
    release = narrative_release_snapshot()
    return {
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "narrative_release_status": release.narrative_release_status.value,
    }


def _narrative() -> dict[str, Any]:
    return {
        "status": "UNVERIFIED",
        "available": False,
        "content": None,
        "blocked_reason": "解释功能尚未完成真实路径验证",
        "live_validation_status": LIVE_VALIDATION_STATUS,
    }


def _error_response(request_id: str, code: str, message: str, generated_at: datetime) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": request_id,
        "status": "VALIDATION_ERROR" if code != "ENGINE_ERROR" else "ENGINE_ERROR",
        "deterministic_result": None,
        "narrative": _narrative(),
        "release_gate": _gate(),
        "audit": {
            "engine_version": None,
            "contract_version": CONTRACT_VERSION,
            "calculation_source": "PYTHON_AUTHORITATIVE_ENGINE",
            "generated_at": generated_at.isoformat(),
            "synthetic_or_real_input": "UNSPECIFIED",
            "request_hash": None,
            "audit_id": _safe_audit_id(request_id),
        },
        "errors": [{"error_code": code, "message": message, "request_id": request_id, "audit_id": _safe_audit_id(request_id)}],
    }


def _validate(payload: Any) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    if not isinstance(payload, dict):
        return None, ("INVALID_REQUEST", "请求必须是JSON对象。")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or safe_request_id(request_id) == "invalid-request":
        return None, ("INVALID_REQUEST", "request_id必须是非空字符串且不超过128字符。")
    extras = set(payload) - _ALLOWED_FIELDS
    if extras & _CLIENT_DERIVED_FIELDS:
        return None, ("CLIENT_CALCULATION_NOT_ACCEPTED", "不得提交客户端计算的卦象或程序结论。")
    if extras & _CLIENT_EVIDENCE_FIELDS:
        return None, ("CLIENT_CALCULATION_NOT_ACCEPTED", "不得提交客户端Evidence。")
    if extras:
        return None, ("INVALID_REQUEST", "请求包含不支持的字段。")
    if payload.get("contract_version") != CONTRACT_VERSION:
        return None, ("INVALID_REQUEST", f"contract_version必须为{CONTRACT_VERSION}。")
    question = payload.get("question_text")
    if not isinstance(question, str) or not question.strip():
        return None, ("EMPTY_QUESTION", "问题不能为空。")
    if len(question.strip()) > 500:
        return None, ("INVALID_REQUEST", "问题不得超过500字符。")
    if len(re.findall(r"[?？]", question)) > 1:
        return None, ("MULTIPLE_QUESTIONS_NOT_ALLOWED", "一次请求只能包含一个问题。")
    numbers = payload.get("numbers")
    if not isinstance(numbers, list) or len(numbers) != 3:
        return None, ("INVALID_NUMBER_COUNT", "numbers必须恰好包含三个数字。")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in numbers):
        return None, ("INVALID_NUMBER_TYPE", "三个数字必须是整数且不能是布尔值。")
    if any(value < 1 or value > 999 for value in numbers):
        return None, ("INVALID_NUMBER_TYPE", "每个数字必须在1到999之间。")
    if payload.get("locale") != "zh-CN":
        return None, ("INVALID_REQUEST", "Phase 3A仅支持zh-CN。")
    timestamp = payload.get("client_timestamp")
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else None
    except ValueError:
        parsed_timestamp = None
    if parsed_timestamp is None or parsed_timestamp.tzinfo is None:
        return None, ("INVALID_REQUEST", "client_timestamp必须是带时区的ISO 8601时间，仅供审计参考。")
    acknowledgements = payload.get("user_acknowledgements")
    expected_ack = {"deterministic_only": True, "narrative_unverified": True}
    if acknowledgements != expected_ack:
        return None, ("INVALID_REQUEST", "必须确认确定性结果边界和Narrative未验证状态。")
    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": request_id.strip(),
        "question_text": question.strip(),
        "numbers": numbers,
        "locale": "zh-CN",
        "client_timestamp": timestamp,
        "user_acknowledgements": expected_ack,
    }, None


def _hexagram(value: Any) -> dict[str, Any]:
    return {"king_wen_number": value.king_wen_number, "name": value.full_name_zh, "symbol": value.unicode_symbol}


def process_sites_meihua_request(
    request_payload: Any,
    *,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Validate Contract V1 and return a frontend-safe deterministic response."""
    generated_at = (clock or _now)()
    if generated_at.tzinfo is None:
        raise ValueError("clock must return an aware datetime")
    request_id = safe_request_id(request_payload.get("request_id") if isinstance(request_payload, dict) else None)
    validated, error = _validate(request_payload)
    if error:
        return _error_response(request_id, error[0], error[1], generated_at)
    assert validated is not None
    request_hash = hashlib.sha256(json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    try:
        chart = cast_meihua(MeihuaInput(*validated["numbers"], generated_at, "Asia/Shanghai", validated["request_id"]))
        knowledge = select_knowledge(chart, policy=KnowledgeAccessPolicy())
        synthesis = ConclusionSynthesizer().synthesize(chart, knowledge)
    except (InputValidationError, RuntimeError, ValueError, KeyError) as exc:
        del exc
        return _error_response(validated["request_id"], "ENGINE_ERROR", "确定性引擎暂时无法完成计算。", generated_at)
    evidence_types = sorted({item.evidence_type.value for item in chart.evidence})
    result = {
        "input_numbers": validated["numbers"],
        "base_hexagram": _hexagram(chart.base_hexagram),
        "mutual_hexagram": _hexagram(chart.mutual_hexagram),
        "changed_hexagram": _hexagram(chart.changed_hexagram),
        "moving_line": chart.moving_line,
        "body_use": {
            "body_trigram": chart.body_trigram.name_zh,
            "initial_use_trigram": chart.initial_use_trigram.name_zh,
            "changed_use_trigram": chart.changed_use_trigram.name_zh,
            "initial_relation": chart.initial_body_use_relation.value,
            "changed_relation": chart.changed_body_use_relation.value,
        },
        "five_elements": {
            "body": chart.body_trigram.element.value,
            "initial_use": chart.initial_use_trigram.element.value,
            "changed_use": chart.changed_use_trigram.element.value,
        },
        "seasonal_strength": {
            "body": chart.season_context.body_strength.value,
            "initial_use": chart.season_context.initial_use_strength.value,
            "changed_use": chart.season_context.changed_use_strength.value,
            "solar_term": chart.season_context.current_solar_term,
            "month_branch": chart.season_context.month_branch,
        },
        "deterministic_conclusion": synthesis.model_dump(mode="json"),
        "evidence_summary": {"count": len(chart.evidence), "evidence_types": evidence_types, "knowledge_mode": knowledge.access_mode, "approved_knowledge_items_used": len(knowledge.knowledge_evidence)},
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": validated["request_id"],
        "status": "SUCCESS",
        "question_text": validated["question_text"],
        "deterministic_result": result,
        "narrative": _narrative(),
        "release_gate": _gate(),
        "audit": {
            "engine_version": chart.versions.engine_version,
            "contract_version": CONTRACT_VERSION,
            "calculation_source": "PYTHON_AUTHORITATIVE_ENGINE",
            "generated_at": generated_at.isoformat(),
            "client_timestamp": validated["client_timestamp"],
            "client_timestamp_used_for_calculation": False,
            "synthetic_or_real_input": "SYNTHETIC",
            "request_hash": request_hash,
            "audit_id": _safe_audit_id(validated["request_id"]),
        },
        "errors": [],
    }
