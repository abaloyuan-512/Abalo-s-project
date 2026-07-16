"""Fail-closed infrastructure for a future authorized M1-A OpenAI evaluation.

This module never authorizes a run by itself.  A live client is created only after
the CLI flag, global authorization and stage authorization have all passed.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from .enums import ServiceStatus
from .exceptions import (
    InterpretationValidationError,
    ProviderError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderIncompleteError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from .m1a_batch3 import stable_json, stable_sha256
from .m1a_eval_runner import _build_fixture_program, _build_intake
from .m1a_prompt_builder import M1APromptBuilder
from .m1a_service import M1A_OFFLINE_PROVIDER_CAPABILITY, M1AService
from .m1a_validator import M1AValidator
from .models import AINarrativeDraftContent, PromptPackage, ProviderResult

M1A_REAL_MODEL_EVAL_PLAN_VERSION = "1.0.1"
M1A_LIVE_PROVIDER_VERSION = "MEIHUA_M1A_OPENAI_RESPONSES_PROVIDER_V1"
M1A_LIVE_RUNNER_VERSION = "MEIHUA_M1A_LIVE_EVAL_RUNNER_V1"
M1A_LIVE_AUDIT_SCHEMA_VERSION = "MEIHUA_M1A_LIVE_AUDIT_V1"

MODEL_ID = "gpt-5.6-terra"
API_TYPE = "RESPONSES_API"
REASONING_EFFORT = "medium"
EXECUTION_MODE = "standard"
CONTEXT_POLICY = "current_turn_only"
SDK_MAX_RETRIES = 0
TIMEOUT_SECONDS = 120.0
TOKEN_BOUND_METHOD = "UTF8_BYTES_CONSERVATIVE"
MAX_OUTPUT_TOKENS = 25_000
MAX_INPUT_TOKENS_PER_REQUEST = 20_000
MAX_REQUESTS_PER_FIXTURE = 2
MAX_REPAIRS_PER_FIXTURE = 1
SENTINEL_MAX_REQUESTS = 8
FULL_FIXTURE_MAX_REQUESTS = 34
SENTINEL_BUDGET_USD = Decimal("4.00")
FULL_FIXTURE_BUDGET_USD = Decimal("15.50")
TOTAL_EVALUATION_BUDGET_USD = Decimal("22.00")

_AUTH_GLOBAL = "M1_A_MODEL_EVALUATION_AUTHORIZED"
_AUTH_SENTINEL = "M1_A_SENTINEL_EVALUATION_AUTHORIZED"
_AUTH_FULL = "M1_A_FULL_FIXTURE_EVALUATION_AUTHORIZED"
_LIVE_AUTHORIZATION_PROOF = object()


class M1ALiveStage(StrEnum):
    SENTINEL = "SENTINEL"
    FULL_FIXTURE = "FULL_FIXTURE"


class M1ARequestKind(StrEnum):
    INITIAL = "INITIAL"
    TECHNICAL_RETRY = "TECHNICAL_RETRY"
    REPAIR = "REPAIR"


class M1ALiveFailureCode(StrEnum):
    LIVE_FLAG_REQUIRED = "M1A_LIVE_OPENAI_FLAG_REQUIRED"
    MODEL_AUTHORIZATION_REQUIRED = "M1A_MODEL_EVALUATION_NOT_AUTHORIZED"
    SENTINEL_AUTHORIZATION_REQUIRED = "M1A_SENTINEL_EVALUATION_NOT_AUTHORIZED"
    FULL_AUTHORIZATION_REQUIRED = "M1A_FULL_FIXTURE_EVALUATION_NOT_AUTHORIZED"
    API_KEY_MISSING = "M1A_OPENAI_API_KEY_MISSING"
    CLIENT_CREATION_FAILED = "M1A_OPENAI_CLIENT_CREATION_FAILED"
    CONFIG_NOT_FROZEN = "M1A_LIVE_CONFIG_NOT_FROZEN"
    PLAN_ASSET_INVALID = "M1A_LIVE_PLAN_ASSET_INVALID"
    INPUT_TOKEN_LIMIT = "M1A_LIVE_INPUT_TOKEN_LIMIT_EXCEEDED"
    FIXTURE_REQUEST_LIMIT = "M1A_LIVE_FIXTURE_REQUEST_LIMIT_EXCEEDED"
    FIXTURE_REPAIR_LIMIT = "M1A_LIVE_FIXTURE_REPAIR_LIMIT_EXCEEDED"
    SENTINEL_REQUEST_LIMIT = "M1A_LIVE_SENTINEL_REQUEST_LIMIT_EXCEEDED"
    FULL_REQUEST_LIMIT = "M1A_LIVE_FULL_REQUEST_LIMIT_EXCEEDED"
    STAGE_BUDGET_LIMIT = "M1A_LIVE_STAGE_BUDGET_EXCEEDED"
    TOTAL_BUDGET_LIMIT = "M1A_LIVE_TOTAL_BUDGET_EXCEEDED"
    PROGRAM_HASH_MISMATCH = "M1A_LIVE_PROGRAM_HASH_MISMATCH"
    CATALOG_HASH_MISMATCH = "M1A_LIVE_CATALOG_HASH_MISMATCH"
    INTEGRITY_NOT_BOUND = "M1A_LIVE_INTEGRITY_NOT_BOUND"
    RESPONSE_MODEL_MISMATCH = "M1A_LIVE_RESPONSE_MODEL_MISMATCH"
    RESPONSE_INVALID = "M1A_LIVE_RESPONSE_INVALID"
    SCHEMA_NOT_STRICT = "M1A_LIVE_STRUCTURED_OUTPUT_SCHEMA_NOT_STRICT"
    PROVIDER_NOT_OFFLINE_REPLAY = "M1A_LIVE_REPLAY_PROVIDER_NOT_OFFLINE"


class M1ALiveEvalError(RuntimeError):
    """Stable, secret-free failure used by the live-evaluation boundary."""

    def __init__(self, code: M1ALiveFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


def _fail(code: M1ALiveFailureCode) -> None:
    raise M1ALiveEvalError(code)


@dataclass(frozen=True, slots=True)
class FrozenResponsesConfig:
    model_id: str = MODEL_ID
    api_type: str = API_TYPE
    reasoning_effort: str = REASONING_EFFORT
    execution_mode: str = EXECUTION_MODE
    context_policy: str = CONTEXT_POLICY
    store: bool = False
    tools: tuple[object, ...] = ()
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_input_tokens: int = MAX_INPUT_TOKENS_PER_REQUEST
    sdk_max_retries: int = SDK_MAX_RETRIES
    timeout_seconds: float = TIMEOUT_SECONDS

    def validate_frozen(self) -> None:
        expected = FrozenResponsesConfig()
        if self != expected or type(self.store) is not bool or self.tools != ():
            _fail(M1ALiveFailureCode.CONFIG_NOT_FROZEN)


def _schema_node_is_strict(node: object) -> bool:
    if isinstance(node, list):
        return all(_schema_node_is_strict(item) for item in node)
    if not isinstance(node, dict):
        return True
    if node.get("type") == "object" or "properties" in node:
        properties = node.get("properties")
        required = node.get("required")
        if not isinstance(properties, dict):
            return False
        if node.get("additionalProperties") is not False:
            return False
        if not isinstance(required, list) or set(required) != set(properties):
            return False
    return all(_schema_node_is_strict(value) for value in node.values())


def structured_output_format() -> dict[str, object]:
    schema = AINarrativeDraftContent.model_json_schema()
    if not _schema_node_is_strict(schema):
        _fail(M1ALiveFailureCode.SCHEMA_NOT_STRICT)
    return {
        "type": "json_schema",
        "name": "meihua_m1a_narrative_draft_v1",
        "strict": True,
        "schema": schema,
    }


def frozen_plan_payload() -> dict[str, object]:
    return {
        "plan_version": M1A_REAL_MODEL_EVAL_PLAN_VERSION,
        "plan_status": "FROZEN",
        "model_id": MODEL_ID,
        "api_type": API_TYPE,
        "api_request_parameters": {
            "model": MODEL_ID,
            "reasoning": {"effort": REASONING_EFFORT},
            "store": False,
            "tools": [],
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "previous_response_id": "OMITTED",
            "conversation": "OMITTED",
        },
        "internal_semantics": {
            "execution_mode": EXECUTION_MODE,
            "context_policy": CONTEXT_POLICY,
        },
        "sdk_transport": {
            "max_retries": SDK_MAX_RETRIES,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "max_input_tokens_per_request": MAX_INPUT_TOKENS_PER_REQUEST,
        "token_bound": {
            "bound_method": TOKEN_BOUND_METHOD,
            "is_exact_token_count": False,
            "truncate_on_exceed": False,
        },
        "limits": {
            "max_requests_per_fixture": MAX_REQUESTS_PER_FIXTURE,
            "max_repairs_per_fixture": MAX_REPAIRS_PER_FIXTURE,
            "sentinel_max_requests": SENTINEL_MAX_REQUESTS,
            "full_fixture_max_requests": FULL_FIXTURE_MAX_REQUESTS,
        },
        "budgets_usd": {
            "sentinel": "4.00",
            "full_fixture": "15.50",
            "total_evaluation": "22.00",
            "accounting_mode": "FAIL_CLOSED_RESERVED_BUDGET",
            "model_price_claimed": False,
        },
        "case_counts": {"sentinel": 4, "full_fixture": 17},
        "automatic_success_thresholds": {
            "program_hash_mismatches": 0,
            "catalog_hash_mismatches": 0,
            "validator_hard_violations": 0,
            "release_gate_changes": 0,
            "all_selected_cases_require_qualified_assembly": True,
        },
        "manual_scoring_thresholds": {
            "all_selected_cases_require_review": True,
            "default_review_status": "UNREVIEWED",
            "numeric_release_threshold_frozen": True,
            "manual_review_cannot_open_release_gate": True,
            "sentinel": {
                "final_validator_success": "4/4",
                "first_attempt_success_at_least": "3/4",
                "manual_review_pass": "4/4",
                "program_and_evidence_fidelity_each_case_at_least": 4,
                "fourteen_dimension_average_each_case_at_least": 4.0,
                "clear_value_add_at_least": "3/4",
                "hard_risk_true_count": 0,
                "unresolved_provider_failure": 0,
                "budget_usd_at_most": "4.00",
            },
            "full_fixture": {
                "final_validator_success": "17/17",
                "first_attempt_success_at_least": "14/17",
                "unresolved_provider_failure": 0,
                "program_and_evidence_fidelity_each_case_at_least": 4,
                "fourteen_dimension_average_each_case_at_least": 4.0,
                "overall_average_at_least": 4.2,
                "clear_value_add_at_least": "14/17",
                "no_value_add": 0,
                "material_evidence_vagueness": 0,
                "hard_risk_true_count": 0,
                "budget_usd_at_most": "15.50",
            },
            "hard_risks": {
                "mind_reading_present": False,
                "outcome_guarantee_present": False,
                "irreversible_instruction_present": False,
                "repeat_output_principle_conflict": False,
            },
        },
        "stop_conditions": [
            "ANY_AUTHORIZATION_GATE_MISSING",
            "INPUT_TOKEN_LIMIT_EXCEEDED",
            "REQUEST_OR_REPAIR_LIMIT_EXCEEDED",
            "STAGE_OR_TOTAL_BUDGET_EXCEEDED",
            "PROGRAM_OR_CATALOG_HASH_CHANGED",
            "STRUCTURED_OUTPUT_OR_VALIDATOR_FAILURE_AFTER_ONE_REPAIR",
            "ANY_RELEASE_GATE_CHANGE",
            "ANY_REAL_USER_DATA_OR_API_KEY_IN_EXPORT",
        ],
        "authorization": {
            _AUTH_GLOBAL: False,
            _AUTH_SENTINEL: False,
            _AUTH_FULL: False,
        },
        "data_policy": "SYNTHETIC_FIXTURES_ONLY",
        "release": {
            "NarrativeReleaseStatus": "UNVERIFIED",
            "should_charge": False,
            "formal_report_persistence_allowed": False,
            "closed_beta_allowed": False,
        },
    }


def load_frozen_plan(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail(M1ALiveFailureCode.PLAN_ASSET_INVALID)
    if value != frozen_plan_payload():
        _fail(M1ALiveFailureCode.PLAN_ASSET_INVALID)
    return value


def _authorized(environ: Mapping[str, str], name: str) -> bool:
    return environ.get(name) == "true"


def authorize_live_stage(
    stage: M1ALiveStage,
    *,
    live_openai: bool,
    environ: Mapping[str, str],
) -> None:
    if live_openai is not True:
        _fail(M1ALiveFailureCode.LIVE_FLAG_REQUIRED)
    if not _authorized(environ, _AUTH_GLOBAL):
        _fail(M1ALiveFailureCode.MODEL_AUTHORIZATION_REQUIRED)
    if stage is M1ALiveStage.SENTINEL and not _authorized(environ, _AUTH_SENTINEL):
        _fail(M1ALiveFailureCode.SENTINEL_AUTHORIZATION_REQUIRED)
    if stage is M1ALiveStage.FULL_FIXTURE and not _authorized(environ, _AUTH_FULL):
        _fail(M1ALiveFailureCode.FULL_AUTHORIZATION_REQUIRED)


@dataclass(slots=True)
class M1ABudgetLedger:
    stage: M1ALiveStage
    stage_reserved_usd: Decimal = Decimal("0")
    total_reserved_usd: Decimal = Decimal("0")
    stage_request_count: int = 0
    fixture_request_counts: dict[str, int] = field(default_factory=dict)
    fixture_repair_counts: dict[str, int] = field(default_factory=dict)
    fixture_technical_retry_counts: dict[str, int] = field(default_factory=dict)
    fixture_second_attempt_kinds: dict[str, str] = field(default_factory=dict)

    @property
    def stage_budget(self) -> Decimal:
        if self.stage is M1ALiveStage.SENTINEL:
            return SENTINEL_BUDGET_USD
        return FULL_FIXTURE_BUDGET_USD

    @property
    def stage_request_limit(self) -> int:
        if self.stage is M1ALiveStage.SENTINEL:
            return SENTINEL_MAX_REQUESTS
        return FULL_FIXTURE_MAX_REQUESTS

    @property
    def reservation_per_request(self) -> Decimal:
        return self.stage_budget / Decimal(self.stage_request_limit)

    def reserve(
        self,
        fixture_id: str,
        attempt_number: int,
        request_kind: M1ARequestKind = M1ARequestKind.INITIAL,
    ) -> Decimal:
        fixture_count = self.fixture_request_counts.get(fixture_id, 0)
        if fixture_count >= MAX_REQUESTS_PER_FIXTURE:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        repair_count = self.fixture_repair_counts.get(fixture_id, 0)
        technical_retry_count = self.fixture_technical_retry_counts.get(fixture_id, 0)
        if attempt_number == 1 and request_kind is not M1ARequestKind.INITIAL:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        if attempt_number == 2 and fixture_count != 1:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        if attempt_number == 2 and request_kind is M1ARequestKind.INITIAL:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        if attempt_number == 2 and fixture_id in self.fixture_second_attempt_kinds:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        if request_kind is M1ARequestKind.REPAIR and repair_count >= MAX_REPAIRS_PER_FIXTURE:
            _fail(M1ALiveFailureCode.FIXTURE_REPAIR_LIMIT)
        if attempt_number not in {1, 2}:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        if self.stage_request_count >= self.stage_request_limit:
            code = (
                M1ALiveFailureCode.SENTINEL_REQUEST_LIMIT
                if self.stage is M1ALiveStage.SENTINEL
                else M1ALiveFailureCode.FULL_REQUEST_LIMIT
            )
            _fail(code)
        reservation = self.reservation_per_request
        if self.stage_reserved_usd + reservation > self.stage_budget:
            _fail(M1ALiveFailureCode.STAGE_BUDGET_LIMIT)
        if self.total_reserved_usd + reservation > TOTAL_EVALUATION_BUDGET_USD:
            _fail(M1ALiveFailureCode.TOTAL_BUDGET_LIMIT)
        self.stage_reserved_usd += reservation
        self.total_reserved_usd += reservation
        self.stage_request_count += 1
        self.fixture_request_counts[fixture_id] = fixture_count + 1
        if request_kind is M1ARequestKind.REPAIR:
            self.fixture_repair_counts[fixture_id] = repair_count + 1
        if request_kind is M1ARequestKind.TECHNICAL_RETRY:
            self.fixture_technical_retry_counts[fixture_id] = technical_retry_count + 1
        if attempt_number == 2:
            self.fixture_second_attempt_kinds[fixture_id] = request_kind.value
        return reservation


@dataclass(frozen=True, slots=True)
class M1ALiveRequestAudit:
    schema_version: str
    provider_version: str
    stage: str
    fixture_id: str
    attempt_number: int
    request_kind: str
    outcome: str
    error_category: str | None
    response_id: str | None
    model_id: str
    prompt_version: str
    program_hash: str
    catalog_hash: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    reserved_cost_usd: str
    actual_cost_usd: None
    external_model_called: bool
    network_called: bool
    input_bound_method: str
    input_bound_value: int

    def to_safe_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


TokenCounter = Callable[[PromptPackage], int]


def conservative_input_token_bound(prompt: PromptPackage) -> int:
    """Safe local upper bound; it may reject early but never truncates input."""

    material = stable_json(
        {
            "input": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_payload_json},
            ]
        }
    )
    return len(material.encode("utf-8"))


def _prompt_hashes(prompt: PromptPackage) -> tuple[str, str]:
    try:
        payload = json.loads(prompt.user_payload_json)
        program_hash = payload["program_owned_constraints"]["program_hash"]
        catalog_hash = payload["evidence_reference_catalog"]["catalog_sha256"]
    except (TypeError, KeyError, json.JSONDecodeError):
        _fail(M1ALiveFailureCode.PROGRAM_HASH_MISMATCH)
    if not isinstance(program_hash, str) or not isinstance(catalog_hash, str):
        _fail(M1ALiveFailureCode.PROGRAM_HASH_MISMATCH)
    return program_hash, catalog_hash


def build_responses_request(
    prompt: PromptPackage,
    config: FrozenResponsesConfig,
) -> dict[str, object]:
    config.validate_frozen()
    return {
        "model": config.model_id,
        "input": [
            {"role": "system", "content": prompt.system_prompt},
            {"role": "user", "content": prompt.user_payload_json},
        ],
        "reasoning": {"effort": config.reasoning_effort},
        "store": config.store,
        "tools": list(config.tools),
        "max_output_tokens": config.max_output_tokens,
        "text": {"format": structured_output_format()},
    }


class M1AOpenAIResponsesProvider:
    """Live-identity provider; it intentionally lacks the M1-A offline capability."""

    provider_kind = "OPENAI_RESPONSES_API"

    def __init__(
        self,
        client: Any,
        *,
        _authorization_proof: object,
        stage: M1ALiveStage,
        ledger: M1ABudgetLedger,
        config: FrozenResponsesConfig | None = None,
        token_counter: TokenCounter = conservative_input_token_bound,
    ) -> None:
        if _authorization_proof is not _LIVE_AUTHORIZATION_PROOF:
            _fail(M1ALiveFailureCode.MODEL_AUTHORIZATION_REQUIRED)
        self.client = client
        self.stage = stage
        self.ledger = ledger
        self.config = config or FrozenResponsesConfig()
        self.config.validate_frozen()
        self.token_counter = token_counter
        self.fixture_id: str | None = None
        self.expected_program_hash: str | None = None
        self.expected_catalog_hash: str | None = None
        self.audits: list[M1ALiveRequestAudit] = []

    def bind_fixture(self, fixture_id: str, program_hash: str, catalog_hash: str) -> None:
        self.fixture_id = fixture_id
        self.expected_program_hash = program_hash
        self.expected_catalog_hash = catalog_hash

    def generate(
        self,
        prompt: PromptPackage,
        *,
        attempt_number: int,
        request_kind: M1ARequestKind = M1ARequestKind.INITIAL,
    ) -> ProviderResult:
        if not all((self.fixture_id, self.expected_program_hash, self.expected_catalog_hash)):
            _fail(M1ALiveFailureCode.INTEGRITY_NOT_BOUND)
        input_tokens_bound = self.token_counter(prompt)
        if input_tokens_bound > self.config.max_input_tokens:
            _fail(M1ALiveFailureCode.INPUT_TOKEN_LIMIT)
        program_hash, catalog_hash = _prompt_hashes(prompt)
        if program_hash != self.expected_program_hash:
            _fail(M1ALiveFailureCode.PROGRAM_HASH_MISMATCH)
        if catalog_hash != self.expected_catalog_hash:
            _fail(M1ALiveFailureCode.CATALOG_HASH_MISMATCH)
        assert self.fixture_id is not None
        reservation = self.ledger.reserve(self.fixture_id, attempt_number, request_kind)
        request = build_responses_request(prompt, self.config)
        started = perf_counter()
        try:
            response = self.client.responses.create(**request)
        except Exception as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            mapped = self._map_provider_error(exc)
            offline_replay = getattr(self.client, "m1a_offline_replay", False) is True
            self.audits.append(
                M1ALiveRequestAudit(
                    schema_version=M1A_LIVE_AUDIT_SCHEMA_VERSION,
                    provider_version=M1A_LIVE_PROVIDER_VERSION,
                    stage=self.stage.value,
                    fixture_id=self.fixture_id,
                    attempt_number=attempt_number,
                    request_kind=request_kind.value,
                    outcome="PROVIDER_ERROR",
                    error_category=type(mapped).__name__,
                    response_id=None,
                    model_id=self.config.model_id,
                    prompt_version=prompt.prompt_version,
                    program_hash=program_hash,
                    catalog_hash=catalog_hash,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    reserved_cost_usd=f"{reservation:.6f}",
                    actual_cost_usd=None,
                    external_model_called=not offline_replay,
                    network_called=not offline_replay,
                    input_bound_method=TOKEN_BOUND_METHOD,
                    input_bound_value=input_tokens_bound,
                )
            )
            raise mapped from None
        latency_ms = int((perf_counter() - started) * 1000)

        def fail_response(error: ProviderError) -> None:
            offline_replay = getattr(self.client, "m1a_offline_replay", False) is True
            self.audits.append(
                M1ALiveRequestAudit(
                    schema_version=M1A_LIVE_AUDIT_SCHEMA_VERSION,
                    provider_version=M1A_LIVE_PROVIDER_VERSION,
                    stage=self.stage.value,
                    fixture_id=self.fixture_id,
                    attempt_number=attempt_number,
                    request_kind=request_kind.value,
                    outcome="PROVIDER_ERROR",
                    error_category=type(error).__name__,
                    response_id=getattr(response, "id", None),
                    model_id=getattr(response, "model", self.config.model_id),
                    prompt_version=prompt.prompt_version,
                    program_hash=program_hash,
                    catalog_hash=catalog_hash,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    reserved_cost_usd=f"{reservation:.6f}",
                    actual_cost_usd=None,
                    external_model_called=not offline_replay,
                    network_called=not offline_replay,
                    input_bound_method=TOKEN_BOUND_METHOD,
                    input_bound_value=input_tokens_bound,
                )
            )
            raise error

        if getattr(response, "status", None) == "incomplete":
            fail_response(ProviderIncompleteError("M1A_OPENAI_RESPONSE_INCOMPLETE"))
        for output in getattr(response, "output", ()):
            for content in getattr(output, "content", ()):
                if getattr(content, "type", None) == "refusal":
                    fail_response(ProviderRefusalError("M1A_OPENAI_RESPONSE_REFUSAL"))
        raw = getattr(response, "output_text", None)
        if not isinstance(raw, str) or not raw:
            fail_response(ProviderSchemaError("M1A_OPENAI_RESPONSE_SCHEMA_INVALID"))
        try:
            parsed = AINarrativeDraftContent.model_validate_json(raw)
        except ValidationError:
            fail_response(ProviderSchemaError("M1A_OPENAI_RESPONSE_SCHEMA_INVALID"))
        response_model = getattr(response, "model", self.config.model_id)
        if response_model != self.config.model_id:
            fail_response(ProviderSchemaError("M1A_OPENAI_RESPONSE_MODEL_MISMATCH"))
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)
        offline_replay = getattr(self.client, "m1a_offline_replay", False) is True
        result = ProviderResult(
            parsed_output=parsed,
            response_id=getattr(response, "id", None),
            model=response_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            attempt_number=attempt_number,
            provider_name="OPENAI_RESPONSES_API",
            prompt_version=prompt.prompt_version,
        )
        self.audits.append(
            M1ALiveRequestAudit(
                schema_version=M1A_LIVE_AUDIT_SCHEMA_VERSION,
                provider_version=M1A_LIVE_PROVIDER_VERSION,
                stage=self.stage.value,
                fixture_id=self.fixture_id,
                attempt_number=attempt_number,
                request_kind=request_kind.value,
                outcome="SUCCESS",
                error_category=None,
                response_id=result.response_id,
                model_id=result.model,
                prompt_version=result.prompt_version,
                program_hash=program_hash,
                catalog_hash=catalog_hash,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                reserved_cost_usd=f"{reservation:.6f}",
                actual_cost_usd=None,
                external_model_called=not offline_replay,
                network_called=not offline_replay,
                input_bound_method=TOKEN_BOUND_METHOD,
                input_bound_value=input_tokens_bound,
            )
        )
        return result

    @staticmethod
    def _map_provider_error(exc: Exception) -> ProviderError:
        name = type(exc).__name__
        if name == "APITimeoutError":
            return ProviderTimeoutError("M1A_OPENAI_TIMEOUT")
        if name == "RateLimitError":
            return ProviderRateLimitError("M1A_OPENAI_RATE_LIMIT")
        if name == "AuthenticationError":
            return ProviderAuthenticationError("M1A_OPENAI_AUTHENTICATION")
        if name == "APIConnectionError":
            return ProviderConnectionError("M1A_OPENAI_CONNECTION")
        status_code = getattr(exc, "status_code", None)
        if status_code in {408, 409} or (isinstance(status_code, int) and status_code >= 500):
            return ProviderConnectionError("M1A_OPENAI_RETRYABLE_HTTP_STATUS")
        return ProviderConfigurationError("M1A_OPENAI_REQUEST_NOT_RETRYABLE")


def create_live_provider(
    stage: M1ALiveStage,
    *,
    live_openai: bool,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., Any] | None = None,
    config: FrozenResponsesConfig | None = None,
    ledger: M1ABudgetLedger | None = None,
    token_counter: TokenCounter = conservative_input_token_bound,
) -> M1AOpenAIResponsesProvider:
    environment = os.environ if environ is None else environ
    frozen_config = config or FrozenResponsesConfig()
    frozen_config.validate_frozen()
    authorize_live_stage(stage, live_openai=live_openai, environ=environment)
    api_key = environment.get("OPENAI_API_KEY")
    if not isinstance(api_key, str) or not api_key:
        _fail(M1ALiveFailureCode.API_KEY_MISSING)
    if client_factory is None:
        from openai import OpenAI

        client_factory = OpenAI
    try:
        client = client_factory(
            api_key=api_key,
            max_retries=frozen_config.sdk_max_retries,
            timeout=frozen_config.timeout_seconds,
        )
    except Exception:
        _fail(M1ALiveFailureCode.CLIENT_CREATION_FAILED)
    return M1AOpenAIResponsesProvider(
        client,
        _authorization_proof=_LIVE_AUTHORIZATION_PROOF,
        stage=stage,
        ledger=ledger or M1ABudgetLedger(stage),
        config=frozen_config,
        token_counter=token_counter,
    )


class _RecordedResponsesReplayProvider:
    """Offline bridge for validating already-recorded responses through M1AService."""

    m1a_offline_capability = M1A_OFFLINE_PROVIDER_CAPABILITY
    provider_kind = "MOCK"

    def __init__(self, results: tuple[ProviderResult, ...]) -> None:
        self.results = results
        self.generate_calls = 0

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
        self.generate_calls += 1
        if attempt_number > len(self.results):
            raise ProviderConfigurationError("M1A_RECORDED_RESPONSE_MISSING")
        recorded = self.results[attempt_number - 1]
        return ProviderResult(
            parsed_output=recorded.parsed_output,
            response_id=recorded.response_id,
            model=recorded.model,
            input_tokens=recorded.input_tokens,
            output_tokens=recorded.output_tokens,
            total_tokens=recorded.total_tokens,
            latency_ms=recorded.latency_ms,
            attempt_number=attempt_number,
            provider_name="MOCK",
            prompt_version=prompt.prompt_version,
        )


_RETRYABLE_TECHNICAL_ERRORS = (
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderConnectionError,
)


def _structured_output(result: ProviderResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    try:
        return AINarrativeDraftContent.model_validate(result.parsed_output).model_dump(mode="json")
    except ValidationError:
        return None


def _manual_review_context(
    fixture: dict[str, Any],
    catalog: Any,
) -> dict[str, object]:
    return {
        "question_domain": fixture["question_domain"],
        "decision_goal": fixture["decision_goal"],
        "time_horizon": fixture["time_horizon"],
        "normalized_question": fixture["normalized_question"],
        "safe_evidence_catalog": catalog.to_provider_payload(),
        "manual_review_template_version": "MEIHUA_M1A_MANUAL_REVIEW_V001",
        "manual_review_criteria_count": 20,
        "manual_review_status": "UNREVIEWED",
    }


def _provider_failure_result(
    fixture: dict[str, Any],
    provider: M1AOpenAIResponsesProvider,
    catalog: Any,
    *,
    attempt_number: int,
    exc: ProviderError,
    audit_start: int,
    technical_retry_attempted: bool,
    repair_attempted: bool,
) -> dict[str, object]:
    return {
        "fixture_id": fixture["fixture_id"],
        "stage": provider.stage.value,
        "runner_version": M1A_LIVE_RUNNER_VERSION,
        "program_hash": fixture["program_hash"],
        "catalog_hash": fixture["provider_catalog_hash"],
        "request_count": len(provider.audits) - audit_start,
        "technical_retry_attempted": technical_retry_attempted,
        "repair_attempted": repair_attempted,
        "second_attempt_kind": provider.ledger.fixture_second_attempt_kinds.get(
            fixture["fixture_id"]
        ),
        "pre_repair_validation_errors": [],
        "status": ServiceStatus.PROVIDER_FAILED.value,
        "failure_code": type(exc).__name__,
        "unresolved_provider_failure": True,
        "qualified_assembly_created": False,
        "final_structured_output": None,
        "final_attempt_number": attempt_number,
        "final_response_id": None,
        "final_validation_status": "NOT_RUN_PROVIDER_FAILURE",
        "final_model_id": provider.config.model_id,
        "manual_review_context": _manual_review_context(fixture, catalog),
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "request_audits": [item.to_safe_dict() for item in provider.audits[audit_start:]],
    }


def evaluate_live_fixture(
    fixture: dict[str, Any],
    provider: M1AOpenAIResponsesProvider,
) -> dict[str, object]:
    context, catalog = _build_fixture_program(fixture)
    intake = _build_intake(fixture)
    provider.bind_fixture(
        fixture["fixture_id"], fixture["program_hash"], fixture["provider_catalog_hash"]
    )
    builder = M1APromptBuilder()
    validator = M1AValidator()
    prompt = builder.build(intake, context, catalog)
    audit_start = len(provider.audits)
    technical_retry_attempted = False
    repair_attempted = False
    first_response: ProviderResult | None = None
    try:
        first_response = provider.generate(
            prompt,
            attempt_number=1,
            request_kind=M1ARequestKind.INITIAL,
        )
    except _RETRYABLE_TECHNICAL_ERRORS:
        technical_retry_attempted = True
        try:
            final_response = provider.generate(
                prompt,
                attempt_number=2,
                request_kind=M1ARequestKind.TECHNICAL_RETRY,
            )
        except ProviderError as exc:
            return _provider_failure_result(
                fixture,
                provider,
                catalog,
                attempt_number=2,
                exc=exc,
                audit_start=audit_start,
                technical_retry_attempted=True,
                repair_attempted=False,
            )
    except ProviderError as exc:
        return _provider_failure_result(
            fixture,
            provider,
            catalog,
            attempt_number=1,
            exc=exc,
            audit_start=audit_start,
            technical_retry_attempted=False,
            repair_attempted=False,
        )
    else:
        final_response = first_response

    validation_errors: list[str] = []
    pre_repair_validation_errors: list[str] = []
    try:
        validator.validate(final_response.parsed_output, intake, catalog)
    except InterpretationValidationError as exc:
        validation_errors = list(exc.errors)
        pre_repair_validation_errors = list(validation_errors)
        if not technical_retry_attempted:
            repair_attempted = True
            repair_prompt = builder.build(
                intake,
                context,
                catalog,
                repair_errors=validation_errors,
            )
            try:
                final_response = provider.generate(
                    repair_prompt,
                    attempt_number=2,
                    request_kind=M1ARequestKind.REPAIR,
                )
            except ProviderError as provider_exc:
                return _provider_failure_result(
                    fixture,
                    provider,
                    catalog,
                    attempt_number=2,
                    exc=provider_exc,
                    audit_start=audit_start,
                    technical_retry_attempted=False,
                    repair_attempted=True,
                )
            try:
                validator.validate(final_response.parsed_output, intake, catalog)
                validation_errors = []
            except InterpretationValidationError as repair_exc:
                validation_errors = list(repair_exc.errors)

    if repair_attempted:
        assert first_response is not None
        replay_results = (first_response, final_response)
    elif validation_errors:
        replay_results = (final_response, final_response)
    else:
        replay_results = (final_response,)
    replay = _RecordedResponsesReplayProvider(replay_results)
    service_result = M1AService(replay).interpret(intake, context)
    qualified = service_result.status is ServiceStatus.SUCCESS and service_result.assembly is not None
    final_attempt_number = 2 if technical_retry_attempted or repair_attempted else 1
    return {
        "fixture_id": fixture["fixture_id"],
        "stage": provider.stage.value,
        "runner_version": M1A_LIVE_RUNNER_VERSION,
        "program_hash": fixture["program_hash"],
        "catalog_hash": fixture["provider_catalog_hash"],
        "request_count": len(provider.audits) - audit_start,
        "technical_retry_attempted": technical_retry_attempted,
        "repair_attempted": repair_attempted,
        "second_attempt_kind": provider.ledger.fixture_second_attempt_kinds.get(
            fixture["fixture_id"]
        ),
        "pre_repair_validation_errors": pre_repair_validation_errors,
        "status": service_result.status.value,
        "failure_code": service_result.failure_code.value if service_result.failure_code else None,
        "unresolved_provider_failure": False,
        "qualified_assembly_created": qualified,
        "final_structured_output": _structured_output(final_response),
        "final_attempt_number": final_attempt_number,
        "final_response_id": final_response.response_id,
        "final_validation_status": "PASSED" if qualified else "REJECTED",
        "final_model_id": final_response.model,
        "manual_review_context": _manual_review_context(fixture, catalog),
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "request_audits": [item.to_safe_dict() for item in provider.audits[audit_start:]],
    }


def run_live_evaluation(
    fixtures: list[dict[str, Any]],
    fixture_ids: tuple[str, ...],
    provider: M1AOpenAIResponsesProvider,
) -> dict[str, object]:
    by_id = {item["fixture_id"]: item for item in fixtures}
    if len(by_id) != len(fixtures) or any(fixture_id not in by_id for fixture_id in fixture_ids):
        _fail(M1ALiveFailureCode.RESPONSE_INVALID)
    expected_count = 4 if provider.stage is M1ALiveStage.SENTINEL else 17
    if len(fixture_ids) != expected_count or len(set(fixture_ids)) != expected_count:
        _fail(M1ALiveFailureCode.RESPONSE_INVALID)
    results = []
    for fixture_id in fixture_ids:
        result = evaluate_live_fixture(by_id[fixture_id], provider)
        results.append(result)
        if result["unresolved_provider_failure"]:
            break
    return {
        "schema_version": M1A_LIVE_AUDIT_SCHEMA_VERSION,
        "plan_version": M1A_REAL_MODEL_EVAL_PLAN_VERSION,
        "runner_version": M1A_LIVE_RUNNER_VERSION,
        "stage": provider.stage.value,
        "model_id": MODEL_ID,
        "results": results,
        "summary": {
            "selected_cases": len(results),
            "qualified_assemblies": sum(item["qualified_assembly_created"] for item in results),
            "requests_used": provider.ledger.stage_request_count,
            "repairs_used": sum(item["repair_attempted"] for item in results),
            "technical_retries_used": sum(
                item["technical_retry_attempted"] for item in results
            ),
            "unresolved_provider_failures": sum(
                item["unresolved_provider_failure"] for item in results
            ),
            "stage_reserved_usd": f"{provider.ledger.stage_reserved_usd:.6f}",
            "total_reserved_usd": f"{provider.ledger.total_reserved_usd:.6f}",
        },
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "formal_report_generated": False,
    }


def write_safe_live_output(output: dict[str, object], path: Path) -> None:
    serialized = stable_json(output, indent=2)
    if "OPENAI_API_KEY" in serialized or "sk-" in serialized:
        _fail(M1ALiveFailureCode.RESPONSE_INVALID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")


def live_configuration_hash() -> str:
    return stable_sha256(frozen_plan_payload())
