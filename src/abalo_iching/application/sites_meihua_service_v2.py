"""Contract V2 application service for finite structured intake."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.meihua import MeihuaInput, cast_meihua
from abalo_iching.meihua.exceptions import InputValidationError

from .sites_meihua_service import (
    INVALID_REQUEST_ID_FALLBACK,
    _gate,
    _hexagram,
    _narrative,
    _now,
    _safe_audit_id,
    _valid_client_timestamp,
    validate_and_normalize_request_id,
)
from .sites_mentor_report_v1 import build_mentor_report
from .sites_structured_question_v1 import (
    DecisionGoal,
    TimeHorizon,
    generate_structured_question,
    parse_structured_fields,
)

CONTRACT_VERSION_V2 = "SITES_MEIHUA_API_CONTRACT_V2"

_ALLOWED_FIELDS = {
    "contract_version",
    "request_id",
    "question_domain",
    "decision_goal",
    "time_horizon",
    "numbers",
    "locale",
    "client_timestamp",
    "user_acknowledgements",
}

_FORBIDDEN_CLIENT_FIELDS = {
    "question_text",
    "normalized_question",
    "question_context",
    "base_hexagram",
    "mutual_hexagram",
    "changed_hexagram",
    "moving_line",
    "body_use",
    "five_elements",
    "seasonal_strength",
    "deterministic_result",
    "deterministic_conclusion",
    "conclusion",
    "evidence",
    "evidence_ids",
    "evidence_refs",
    "evidence_summary",
}


def _error_response_v2(
    request_id: str,
    code: str,
    message: str,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION_V2,
        "request_id": request_id,
        "status": "ENGINE_ERROR" if code == "ENGINE_ERROR" else "VALIDATION_ERROR",
        "deterministic_result": None,
        "narrative": _narrative(),
        "release_gate": _gate(),
        "audit": {
            "engine_version": None,
            "contract_version": CONTRACT_VERSION_V2,
            "calculation_source": "PYTHON_AUTHORITATIVE_ENGINE",
            "generated_at": generated_at.isoformat(),
            "synthetic_or_real_input": "UNSPECIFIED",
            "request_hash": None,
            "audit_id": _safe_audit_id(request_id),
            "question_template_version": None,
        },
        "errors": [{
            "error_code": code,
            "message": message,
            "request_id": request_id,
            "audit_id": _safe_audit_id(request_id),
        }],
    }


def _validate_v2(payload: Any) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    if not isinstance(payload, dict):
        return None, ("INVALID_REQUEST", "请求必须是JSON对象。")
    request_id = validate_and_normalize_request_id(payload.get("request_id"))
    if request_id is None:
        return None, ("INVALID_REQUEST", "request_id必须是非空字符串且不超过128字符。")
    extras = set(payload) - _ALLOWED_FIELDS
    if extras & _FORBIDDEN_CLIENT_FIELDS:
        return None, ("CLIENT_INPUT_NOT_ACCEPTED", "不得提交问题文本、卦象、Evidence或客户端派生结果。")
    if extras:
        return None, ("INVALID_REQUEST", "请求包含不支持的字段。")
    if payload.get("contract_version") != CONTRACT_VERSION_V2:
        return None, ("INVALID_REQUEST", f"contract_version必须为{CONTRACT_VERSION_V2}。")
    try:
        domain, goal, horizon = parse_structured_fields(
            payload.get("question_domain"),
            payload.get("decision_goal"),
            payload.get("time_horizon"),
        )
        normalized_question, template_version = generate_structured_question(domain, goal, horizon)
    except ValueError:
        return None, ("INVALID_REQUEST", "结构化字段未知或领域与目标组合不受支持。")
    numbers = payload.get("numbers")
    if not isinstance(numbers, list) or len(numbers) != 3:
        return None, ("INVALID_NUMBER_COUNT", "numbers必须恰好包含三个数字。")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in numbers):
        return None, ("INVALID_NUMBER_TYPE", "三个数字必须是整数且不能是布尔值。")
    if any(value < 1 or value > 999 for value in numbers):
        return None, ("INVALID_NUMBER_TYPE", "每个数字必须在1到999之间。")
    if payload.get("locale") != "zh-CN":
        return None, ("INVALID_REQUEST", "当前仅支持zh-CN。")
    timestamp = payload.get("client_timestamp")
    if not _valid_client_timestamp(timestamp):
        return None, ("INVALID_REQUEST", "client_timestamp必须是带时区的ISO 8601时间，仅供审计参考。")
    expected_ack = {
        "deterministic_only": True,
        "narrative_unverified": True,
        "structured_question_confirmed": True,
    }
    if payload.get("user_acknowledgements") != expected_ack:
        return None, ("INVALID_REQUEST", "必须确认结构化问题、确定性结果边界和Narrative未验证状态。")
    return {
        "contract_version": CONTRACT_VERSION_V2,
        "request_id": request_id,
        "question_domain": domain.value,
        "decision_goal": goal.value,
        "time_horizon": horizon.value,
        "normalized_question": normalized_question,
        "question_template_version": template_version,
        "numbers": numbers,
        "locale": "zh-CN",
        "client_timestamp": timestamp,
        "user_acknowledgements": expected_ack,
    }, None


def process_sites_meihua_v2_request(
    request_payload: Any,
    *,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Validate Contract V2 before making exactly one authoritative cast."""
    generated_at = (clock or _now)()
    if generated_at.tzinfo is None:
        raise ValueError("clock must return an aware datetime")
    request_id = validate_and_normalize_request_id(
        request_payload.get("request_id") if isinstance(request_payload, dict) else None
    ) or INVALID_REQUEST_ID_FALLBACK
    validated, error = _validate_v2(request_payload)
    if error:
        return _error_response_v2(request_id, error[0], error[1], generated_at)
    assert validated is not None
    request_hash = hashlib.sha256(
        json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    try:
        chart = cast_meihua(MeihuaInput(
            *validated["numbers"], generated_at, "Asia/Shanghai", validated["request_id"]
        ))
        knowledge = select_knowledge(chart, policy=KnowledgeAccessPolicy())
        synthesis = ConclusionSynthesizer().synthesize(chart, knowledge)
    except (InputValidationError, RuntimeError, ValueError, KeyError):
        return _error_response_v2(
            validated["request_id"], "ENGINE_ERROR", "确定性引擎暂时无法完成计算。", generated_at
        )
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
        "mentor_report": build_mentor_report(
            chart,
            synthesis,
            DecisionGoal(validated["decision_goal"]),
            TimeHorizon(validated["time_horizon"]),
        ),
        "evidence_summary": {
            "count": len(chart.evidence),
            "evidence_types": evidence_types,
            "knowledge_mode": knowledge.access_mode,
            "approved_knowledge_items_used": len(knowledge.knowledge_evidence),
        },
    }
    return {
        "contract_version": CONTRACT_VERSION_V2,
        "request_id": validated["request_id"],
        "status": "SUCCESS",
        "structured_intake": {
            "question_domain": validated["question_domain"],
            "decision_goal": validated["decision_goal"],
            "time_horizon": validated["time_horizon"],
        },
        "normalized_question": validated["normalized_question"],
        "question_template_version": validated["question_template_version"],
        "deterministic_result": result,
        "narrative": _narrative(),
        "release_gate": _gate(),
        "audit": {
            "engine_version": chart.versions.engine_version,
            "contract_version": CONTRACT_VERSION_V2,
            "calculation_source": "PYTHON_AUTHORITATIVE_ENGINE",
            "generated_at": generated_at.isoformat(),
            "client_timestamp": validated["client_timestamp"],
            "client_timestamp_used_for_calculation": False,
            "synthetic_or_real_input": "SYNTHETIC",
            "request_hash": request_hash,
            "audit_id": _safe_audit_id(validated["request_id"]),
            "question_template_version": validated["question_template_version"],
        },
        "errors": [],
    }
