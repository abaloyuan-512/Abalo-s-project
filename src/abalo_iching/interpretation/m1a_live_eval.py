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

M1A_REAL_MODEL_EVAL_PLAN_VERSION = "1.0"
M1A_LIVE_PROVIDER_VERSION = "MEIHUA_M1A_OPENAI_RESPONSES_PROVIDER_V1"
M1A_LIVE_RUNNER_VERSION = "MEIHUA_M1A_LIVE_EVAL_RUNNER_V1"
M1A_LIVE_AUDIT_SCHEMA_VERSION = "MEIHUA_M1A_LIVE_AUDIT_V1"

MODEL_ID = "gpt-5.6-terra"
API_TYPE = "RESPONSES_API"
REASONING_MODE = "standard"
REASONING_EFFORT = "medium"
REASONING_CONTEXT = "current_turn"
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
    reasoning_mode: str = REASONING_MODE
    reasoning_effort: str = REASONING_EFFORT
    reasoning_context: str = REASONING_CONTEXT
    store: bool = False
    tools: tuple[object, ...] = ()
    previous_response_id: None = None
    conversation: None = None
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_input_tokens: int = MAX_INPUT_TOKENS_PER_REQUEST

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
        "reasoning": {
            "mode": REASONING_MODE,
            "effort": REASONING_EFFORT,
            "context": REASONING_CONTEXT,
        },
        "store": False,
        "tools": [],
        "previous_response_id": None,
        "conversation": None,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_input_tokens_per_request": MAX_INPUT_TOKENS_PER_REQUEST,
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
            "numeric_release_threshold_frozen": False,
            "anchor_examples_required_before_numeric_release_threshold": True,
            "manual_review_cannot_open_release_gate": True,
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

    def reserve(self, fixture_id: str, attempt_number: int) -> Decimal:
        fixture_count = self.fixture_request_counts.get(fixture_id, 0)
        if fixture_count >= MAX_REQUESTS_PER_FIXTURE:
            _fail(M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT)
        repair_count = self.fixture_repair_counts.get(fixture_id, 0)
        if attempt_number == 2 and repair_count >= MAX_REPAIRS_PER_FIXTURE:
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
        if attempt_number == 2:
            self.fixture_repair_counts[fixture_id] = repair_count + 1
        return reservation


@dataclass(frozen=True, slots=True)
class M1ALiveRequestAudit:
    schema_version: str
    provider_version: str
    stage: str
    fixture_id: str
    attempt_number: int
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
        "reasoning": {
            "mode": config.reasoning_mode,
            "effort": config.reasoning_effort,
            "context": config.reasoning_context,
        },
        "store": config.store,
        "tools": list(config.tools),
        "previous_response_id": config.previous_response_id,
        "conversation": config.conversation,
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

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
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
        reservation = self.ledger.reserve(self.fixture_id, attempt_number)
        request = build_responses_request(prompt, self.config)
        started = perf_counter()
        try:
            response = self.client.responses.create(**request)
        except Exception as exc:
            self._raise_provider_error(exc)
        latency_ms = int((perf_counter() - started) * 1000)
        if getattr(response, "status", None) == "incomplete":
            raise ProviderIncompleteError("M1A_OPENAI_RESPONSE_INCOMPLETE")
        for output in getattr(response, "output", ()):
            for content in getattr(output, "content", ()):
                if getattr(content, "type", None) == "refusal":
                    raise ProviderRefusalError("M1A_OPENAI_RESPONSE_REFUSAL")
        raw = getattr(response, "output_text", None)
        if not isinstance(raw, str) or not raw:
            raise ProviderSchemaError("M1A_OPENAI_RESPONSE_SCHEMA_INVALID")
        try:
            parsed = AINarrativeDraftContent.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderSchemaError("M1A_OPENAI_RESPONSE_SCHEMA_INVALID") from exc
        response_model = getattr(response, "model", self.config.model_id)
        if response_model != self.config.model_id:
            _fail(M1ALiveFailureCode.RESPONSE_MODEL_MISMATCH)
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
            )
        )
        return result

    @staticmethod
    def _raise_provider_error(exc: Exception) -> None:
        name = type(exc).__name__
        if name == "APITimeoutError":
            raise ProviderTimeoutError("M1A_OPENAI_TIMEOUT") from None
        if name == "RateLimitError":
            raise ProviderRateLimitError("M1A_OPENAI_RATE_LIMIT") from None
        if name == "AuthenticationError":
            raise ProviderAuthenticationError("M1A_OPENAI_AUTHENTICATION") from None
        if name == "APIConnectionError":
            raise ProviderConnectionError("M1A_OPENAI_CONNECTION") from None
        raise ProviderConnectionError("M1A_OPENAI_REQUEST_FAILED") from None


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
        client = client_factory(api_key=api_key)
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
    responses = [provider.generate(prompt, attempt_number=1)]
    validation_errors: list[str] = []
    try:
        validator.validate(responses[0].parsed_output, intake, catalog)
    except InterpretationValidationError as exc:
        validation_errors = list(exc.errors)
        repair_prompt = builder.build(
            intake,
            context,
            catalog,
            repair_errors=validation_errors,
        )
        responses.append(provider.generate(repair_prompt, attempt_number=2))
    replay = _RecordedResponsesReplayProvider(tuple(responses))
    service_result = M1AService(replay).interpret(intake, context)
    qualified = service_result.status is ServiceStatus.SUCCESS and service_result.assembly is not None
    return {
        "fixture_id": fixture["fixture_id"],
        "stage": provider.stage.value,
        "runner_version": M1A_LIVE_RUNNER_VERSION,
        "program_hash": fixture["program_hash"],
        "catalog_hash": fixture["provider_catalog_hash"],
        "request_count": len(responses),
        "repair_attempted": len(responses) == 2,
        "pre_repair_validation_errors": validation_errors,
        "status": service_result.status.value,
        "failure_code": service_result.failure_code.value if service_result.failure_code else None,
        "qualified_assembly_created": qualified,
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "request_audits": [item.to_safe_dict() for item in provider.audits[-len(responses) :]],
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
    results = [evaluate_live_fixture(by_id[fixture_id], provider) for fixture_id in fixture_ids]
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
