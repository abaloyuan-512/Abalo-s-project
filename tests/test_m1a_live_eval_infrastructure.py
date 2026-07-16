"""Completely offline acceptance tests for future M1-A live-eval infrastructure."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from abalo_iching.interpretation.enums import ServiceStatus
from abalo_iching.interpretation.m1a_eval_runner import (
    FixedReplayProvider,
    _build_fixture_program,
    _build_intake,
)
from abalo_iching.interpretation.m1a_live_eval import (
    FULL_FIXTURE_BUDGET_USD,
    FULL_FIXTURE_MAX_REQUESTS,
    MAX_INPUT_TOKENS_PER_REQUEST,
    MODEL_ID,
    SDK_MAX_RETRIES,
    SENTINEL_BUDGET_USD,
    SENTINEL_MAX_REQUESTS,
    TOTAL_EVALUATION_BUDGET_USD,
    TIMEOUT_SECONDS,
    TOKEN_BOUND_METHOD,
    FrozenResponsesConfig,
    M1ABudgetLedger,
    M1ALiveEvalError,
    M1ALiveFailureCode,
    M1ALiveStage,
    M1ARequestKind,
    M1AOpenAIResponsesProvider,
    authorize_live_stage,
    build_responses_request,
    create_live_provider,
    evaluate_live_fixture,
    frozen_plan_payload,
    load_frozen_plan,
    run_live_evaluation,
    structured_output_format,
    write_safe_live_output,
)
from abalo_iching.interpretation.m1a_prompt_builder import M1APromptBuilder
from abalo_iching.interpretation.m1a_service import M1AFailureCode, M1AService
from abalo_iching.interpretation.models import AINarrativeDraftContent
from abalo_iching.interpretation.exceptions import (
    ProviderAuthenticationError,
    ProviderSchemaError,
)

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "evals" / "meihua" / "m1a_v001"
AUTH_ALL = {
    "M1_A_MODEL_EVALUATION_AUTHORIZED": "true",
    "M1_A_SENTINEL_EVALUATION_AUTHORIZED": "true",
    "M1_A_FULL_FIXTURE_EVALUATION_AUTHORIZED": "true",
    "OPENAI_API_KEY": "test-only-placeholder",
}


class FakeResponses:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        value = self._responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class APITimeoutError(Exception):
    pass


class RateLimitError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class APIStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"fake status {status_code}")


class FakeClient:
    m1a_offline_replay = True

    def __init__(self, responses: list[object]) -> None:
        self.responses = FakeResponses(responses)


class FakeClientFactory:
    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.calls = 0
        self.received_key: str | None = None
        self.received_max_retries: int | None = None
        self.received_timeout: float | None = None

    def __call__(self, *, api_key: str, max_retries: int, timeout: float):
        self.calls += 1
        self.received_key = api_key
        self.received_max_retries = max_retries
        self.received_timeout = timeout
        return self.client


class KeyReadGuard(dict[str, str]):
    def get(self, key: str, default=None):
        if key == "OPENAI_API_KEY":
            raise AssertionError("API key must not be read before authorization")
        return super().get(key, default)


@pytest.fixture(scope="module")
def fixtures() -> list[dict[str, object]]:
    return json.loads((ASSET_ROOT / "fixtures.json").read_text(encoding="utf-8"))


def _prompt_and_valid_draft(fixture):
    context, catalog = _build_fixture_program(fixture)
    intake = _build_intake(fixture)
    prompt = M1APromptBuilder().build(intake, context, catalog)
    draft = FixedReplayProvider().generate(prompt, attempt_number=1).parsed_output
    assert isinstance(draft, AINarrativeDraftContent)
    return prompt, draft


def _response(draft: AINarrativeDraftContent, *, response_id: str = "resp_fake_001"):
    return SimpleNamespace(
        id=response_id,
        model=MODEL_ID,
        status="completed",
        output_text=draft.model_dump_json(),
        output=[],
        usage=SimpleNamespace(input_tokens=100, output_tokens=80, total_tokens=180),
    )


def _provider_for_fixture(fixture, responses, **kwargs):
    client = FakeClient(responses)
    factory = FakeClientFactory(client)
    provider = create_live_provider(
        M1ALiveStage.SENTINEL,
        live_openai=True,
        environ=AUTH_ALL,
        client_factory=factory,
        ledger=kwargs.pop("ledger", M1ABudgetLedger(M1ALiveStage.SENTINEL)),
        token_counter=kwargs.pop("token_counter", lambda prompt: 100),
        config=kwargs.pop("config", None),
    )
    provider.bind_fixture(
        fixture["fixture_id"], fixture["program_hash"], fixture["provider_catalog_hash"]
    )
    return provider, client


def _assert_code(expected: M1ALiveFailureCode, callable_):
    with pytest.raises(M1ALiveEvalError) as caught:
        callable_()
    assert caught.value.code is expected
    assert str(caught.value) == expected.value


def test_frozen_plan_asset_is_exact_and_all_authorizations_are_false():
    plan = load_frozen_plan(ASSET_ROOT / "live_eval_plan_v1.json")
    assert plan == frozen_plan_payload()
    assert set(plan["authorization"].values()) == {False}
    assert plan["model_id"] == MODEL_ID
    assert plan["max_input_tokens_per_request"] == 20_000
    assert plan["api_request_parameters"]["max_output_tokens"] == 25_000
    assert plan["plan_version"] == "1.0.1"
    assert plan["token_bound"]["bound_method"] == TOKEN_BOUND_METHOD


def test_plan_v101_contains_all_frozen_numeric_gates():
    plan = frozen_plan_payload()
    sentinel = plan["manual_scoring_thresholds"]["sentinel"]
    full = plan["manual_scoring_thresholds"]["full_fixture"]
    assert sentinel == {
        "final_validator_success": "4/4",
        "first_attempt_success_at_least": "3/4",
        "manual_review_pass": "4/4",
        "program_and_evidence_fidelity_each_case_at_least": 4,
        "fourteen_dimension_average_each_case_at_least": 4.0,
        "clear_value_add_at_least": "3/4",
        "hard_risk_true_count": 0,
        "unresolved_provider_failure": 0,
        "budget_usd_at_most": "4.00",
    }
    assert full == {
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
    }
    assert plan["manual_scoring_thresholds"]["hard_risks"] == {
        "mind_reading_present": False,
        "outcome_guarantee_present": False,
        "irreversible_instruction_present": False,
        "repeat_output_principle_conflict": False,
    }
    assert plan["manual_scoring_thresholds"]["numeric_release_threshold_frozen"] is True
    assert plan["sdk_transport"] == {"max_retries": 0, "timeout_seconds": 120.0}


def test_missing_live_flag_fails_before_key_read_or_client_creation():
    env = KeyReadGuard(
        {
            "M1_A_MODEL_EVALUATION_AUTHORIZED": "true",
            "M1_A_SENTINEL_EVALUATION_AUTHORIZED": "true",
        }
    )
    factory = FakeClientFactory(FakeClient([]))
    _assert_code(
        M1ALiveFailureCode.LIVE_FLAG_REQUIRED,
        lambda: create_live_provider(
            M1ALiveStage.SENTINEL,
            live_openai=False,
            environ=env,
            client_factory=factory,
        ),
    )
    assert factory.calls == 0


def test_global_authorization_false_fails_before_key_read_or_client_creation():
    env = KeyReadGuard({"M1_A_MODEL_EVALUATION_AUTHORIZED": "false"})
    factory = FakeClientFactory(FakeClient([]))
    _assert_code(
        M1ALiveFailureCode.MODEL_AUTHORIZATION_REQUIRED,
        lambda: create_live_provider(
            M1ALiveStage.SENTINEL,
            live_openai=True,
            environ=env,
            client_factory=factory,
        ),
    )
    assert factory.calls == 0


def test_sentinel_authorization_is_independent_and_fail_closed():
    env = KeyReadGuard(
        {
            "M1_A_MODEL_EVALUATION_AUTHORIZED": "true",
            "M1_A_SENTINEL_EVALUATION_AUTHORIZED": "false",
        }
    )
    _assert_code(
        M1ALiveFailureCode.SENTINEL_AUTHORIZATION_REQUIRED,
        lambda: authorize_live_stage(M1ALiveStage.SENTINEL, live_openai=True, environ=env),
    )


def test_full_authorization_is_independent_and_fail_closed():
    env = KeyReadGuard(
        {
            "M1_A_MODEL_EVALUATION_AUTHORIZED": "true",
            "M1_A_FULL_FIXTURE_EVALUATION_AUTHORIZED": "false",
        }
    )
    _assert_code(
        M1ALiveFailureCode.FULL_AUTHORIZATION_REQUIRED,
        lambda: authorize_live_stage(M1ALiveStage.FULL_FIXTURE, live_openai=True, environ=env),
    )


def test_missing_api_key_is_safe_and_does_not_create_client():
    env = {key: value for key, value in AUTH_ALL.items() if key != "OPENAI_API_KEY"}
    factory = FakeClientFactory(FakeClient([]))
    _assert_code(
        M1ALiveFailureCode.API_KEY_MISSING,
        lambda: create_live_provider(
            M1ALiveStage.SENTINEL,
            live_openai=True,
            environ=env,
            client_factory=factory,
        ),
    )
    assert factory.calls == 0


def test_provider_cannot_be_directly_constructed_without_authorization_proof():
    _assert_code(
        M1ALiveFailureCode.MODEL_AUTHORIZATION_REQUIRED,
        lambda: M1AOpenAIResponsesProvider(
            FakeClient([]),
            _authorization_proof=object(),
            stage=M1ALiveStage.SENTINEL,
            ledger=M1ABudgetLedger(M1ALiveStage.SENTINEL),
        ),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", "different-model"),
        ("api_type", "CHAT_COMPLETIONS"),
        ("reasoning_effort", "low"),
        ("execution_mode", "pro"),
        ("context_policy", "all_turns"),
        ("store", True),
        ("tools", ("tool",)),
        ("max_output_tokens", 24_999),
        ("max_input_tokens", 19_999),
        ("sdk_max_retries", 1),
        ("timeout_seconds", 119.0),
    ],
)
def test_any_frozen_responses_parameter_change_fails_before_client(field, value):
    config = replace(FrozenResponsesConfig(), **{field: value})
    factory = FakeClientFactory(FakeClient([]))
    _assert_code(
        M1ALiveFailureCode.CONFIG_NOT_FROZEN,
        lambda: create_live_provider(
            M1ALiveStage.SENTINEL,
            live_openai=True,
            environ=AUTH_ALL,
            client_factory=factory,
            config=config,
        ),
    )
    assert factory.calls == 0


def test_structured_output_request_is_strict_and_frozen(fixtures):
    prompt, _ = _prompt_and_valid_draft(fixtures[0])
    request = build_responses_request(prompt, FrozenResponsesConfig())
    assert request["model"] == MODEL_ID
    assert request["reasoning"] == {"effort": "medium"}
    assert set(request) == {
        "model",
        "input",
        "reasoning",
        "store",
        "tools",
        "max_output_tokens",
        "text",
    }
    assert "mode" not in request["reasoning"]
    assert "context" not in request["reasoning"]
    assert request["store"] is False
    assert request["tools"] == []
    assert "previous_response_id" not in request
    assert "conversation" not in request
    assert request["max_output_tokens"] == 25_000
    output_format = request["text"]["format"]
    assert output_format["strict"] is True
    assert output_format == structured_output_format()
    assert output_format["schema"]["additionalProperties"] is False


def test_input_over_20000_fails_without_truncation_or_client_call(fixtures):
    prompt, draft = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(
        fixtures[0], [_response(draft)], token_counter=lambda value: MAX_INPUT_TOKENS_PER_REQUEST + 1
    )
    _assert_code(
        M1ALiveFailureCode.INPUT_TOKEN_LIMIT,
        lambda: provider.generate(prompt, attempt_number=1),
    )
    assert client.responses.calls == []


def test_program_and_catalog_hash_changes_fail_before_client(fixtures):
    prompt, draft = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(fixtures[0], [_response(draft)])
    provider.bind_fixture(fixtures[0]["fixture_id"], "0" * 64, fixtures[0]["provider_catalog_hash"])
    _assert_code(
        M1ALiveFailureCode.PROGRAM_HASH_MISMATCH,
        lambda: provider.generate(prompt, attempt_number=1),
    )
    assert client.responses.calls == []
    provider.bind_fixture(fixtures[0]["fixture_id"], fixtures[0]["program_hash"], "0" * 64)
    _assert_code(
        M1ALiveFailureCode.CATALOG_HASH_MISMATCH,
        lambda: provider.generate(prompt, attempt_number=1),
    )
    assert client.responses.calls == []


def test_per_fixture_request_and_repair_limits():
    ledger = M1ABudgetLedger(M1ALiveStage.SENTINEL)
    ledger.reserve("fixture-a", 1)
    ledger.reserve("fixture-a", 2, M1ARequestKind.REPAIR)
    _assert_code(
        M1ALiveFailureCode.FIXTURE_REQUEST_LIMIT,
        lambda: ledger.reserve("fixture-a", 1),
    )
    repair_ledger = M1ABudgetLedger(
        M1ALiveStage.SENTINEL,
        fixture_request_counts={"fixture-b": 1},
        fixture_repair_counts={"fixture-b": 1},
    )
    _assert_code(
        M1ALiveFailureCode.FIXTURE_REPAIR_LIMIT,
        lambda: repair_ledger.reserve("fixture-b", 2, M1ARequestKind.REPAIR),
    )


@pytest.mark.parametrize(
    ("stage", "limit", "code"),
    [
        (M1ALiveStage.SENTINEL, SENTINEL_MAX_REQUESTS, M1ALiveFailureCode.SENTINEL_REQUEST_LIMIT),
        (M1ALiveStage.FULL_FIXTURE, FULL_FIXTURE_MAX_REQUESTS, M1ALiveFailureCode.FULL_REQUEST_LIMIT),
    ],
)
def test_stage_request_limits(stage, limit, code):
    ledger = M1ABudgetLedger(stage)
    for index in range(limit):
        ledger.reserve(f"fixture-{index}", 1)
    _assert_code(code, lambda: ledger.reserve("fixture-over", 1))


def test_stage_and_total_budget_limits_fail_closed():
    stage_ledger = M1ABudgetLedger(
        M1ALiveStage.SENTINEL,
        stage_reserved_usd=SENTINEL_BUDGET_USD,
    )
    _assert_code(
        M1ALiveFailureCode.STAGE_BUDGET_LIMIT,
        lambda: stage_ledger.reserve("fixture", 1),
    )
    total_ledger = M1ABudgetLedger(
        M1ALiveStage.FULL_FIXTURE,
        total_reserved_usd=TOTAL_EVALUATION_BUDGET_USD,
    )
    _assert_code(
        M1ALiveFailureCode.TOTAL_BUDGET_LIMIT,
        lambda: total_ledger.reserve("fixture", 1),
    )
    assert FULL_FIXTURE_BUDGET_USD == Decimal("15.50")


def test_live_provider_never_pretends_to_be_fake_or_mock_and_service_gate_remains(fixtures):
    prompt, draft = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(fixtures[0], [_response(draft)])
    context, _ = _build_fixture_program(fixtures[0])
    intake = _build_intake(fixtures[0])
    result = M1AService(provider).interpret(intake, context)
    assert result.failure_code is M1AFailureCode.PROVIDER_NOT_OFFLINE
    assert client.responses.calls == []
    assert provider.provider_kind == "OPENAI_RESPONSES_API"
    assert not hasattr(provider, "m1a_offline_capability")
    assert prompt.prompt_version


def test_fake_responses_replay_passes_existing_service_and_validator(fixtures):
    _, draft = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(fixtures[0], [_response(draft)])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["status"] == ServiceStatus.SUCCESS.value
    assert result["qualified_assembly_created"] is True
    assert result["request_count"] == 1
    assert len(client.responses.calls) == 1
    assert result["request_audits"][0]["external_model_called"] is False
    assert result["request_audits"][0]["network_called"] is False
    assert result["request_audits"][0]["input_bound_method"] == TOKEN_BOUND_METHOD


def test_safe_result_contains_final_structured_output_for_twenty_item_review(fixtures):
    _, draft = _prompt_and_valid_draft(fixtures[0])
    provider, _ = _provider_for_fixture(fixtures[0], [_response(draft)])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert set(result["final_structured_output"]) == {
        "plain_language_explanation",
        "real_world_advice",
        "conditions_that_change_outcome",
        "review_questions",
    }
    assert result["final_attempt_number"] == 1
    assert result["final_response_id"] == "resp_fake_001"
    assert result["final_validation_status"] == "PASSED"
    assert result["final_model_id"] == MODEL_ID
    review = result["manual_review_context"]
    assert review["manual_review_criteria_count"] == 20
    assert review["manual_review_status"] == "UNREVIEWED"
    assert review["question_domain"] == fixtures[0]["question_domain"]
    assert review["decision_goal"] == fixtures[0]["decision_goal"]
    assert review["time_horizon"] == fixtures[0]["time_horizon"]
    assert review["safe_evidence_catalog"]["catalog_sha256"] == fixtures[0][
        "provider_catalog_hash"
    ]
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "encrypted_reasoning",
        "reasoning_content",
        "authorization_header",
        "api_key",
        "real_world_context",
    ):
        assert forbidden not in serialized


def test_one_repair_is_used_and_invalid_second_response_never_forms_assembly(fixtures):
    _, valid = _prompt_and_valid_draft(fixtures[0])
    invalid_payload = valid.model_dump(mode="json")
    invalid_payload["real_world_advice"][0]["text"] = "你必须辞职，这就是唯一正确的决定。"
    invalid = AINarrativeDraftContent.model_validate(invalid_payload)
    provider, client = _provider_for_fixture(
        fixtures[0], [_response(invalid, response_id="first"), _response(valid, response_id="repair")]
    )
    repaired = evaluate_live_fixture(fixtures[0], provider)
    assert repaired["qualified_assembly_created"] is True
    assert repaired["repair_attempted"] is True
    assert repaired["technical_retry_attempted"] is False
    assert repaired["second_attempt_kind"] == "REPAIR"
    assert repaired["request_count"] == 2
    assert len(client.responses.calls) == 2

    failing_provider, _ = _provider_for_fixture(
        fixtures[0], [_response(invalid, response_id="first"), _response(invalid, response_id="second")]
    )
    failed = evaluate_live_fixture(fixtures[0], failing_provider)
    assert failed["qualified_assembly_created"] is False
    assert failed["status"] == ServiceStatus.FAILED_VALIDATION.value


@pytest.mark.parametrize("technical_error", [APITimeoutError(), RateLimitError(), APIConnectionError()])
def test_explicit_technical_retry_uses_second_request_and_shared_ledger(fixtures, technical_error):
    _, valid = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(fixtures[0], [technical_error, _response(valid)])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["qualified_assembly_created"] is True
    assert result["technical_retry_attempted"] is True
    assert result["repair_attempted"] is False
    assert result["second_attempt_kind"] == "TECHNICAL_RETRY"
    assert result["request_count"] == 2
    assert len(client.responses.calls) == 2
    assert provider.ledger.stage_request_count == 2
    assert provider.ledger.fixture_request_counts[fixtures[0]["fixture_id"]] == 2
    assert [audit["request_kind"] for audit in result["request_audits"]] == [
        "INITIAL",
        "TECHNICAL_RETRY",
    ]


def test_validator_rejection_after_technical_retry_cannot_start_repair(fixtures):
    _, valid = _prompt_and_valid_draft(fixtures[0])
    invalid_payload = valid.model_dump(mode="json")
    invalid_payload["real_world_advice"][0]["text"] = "你必须辞职，这就是唯一正确的决定。"
    invalid = AINarrativeDraftContent.model_validate(invalid_payload)
    provider, client = _provider_for_fixture(
        fixtures[0], [APITimeoutError(), _response(invalid, response_id="retry-invalid")]
    )
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["technical_retry_attempted"] is True
    assert result["repair_attempted"] is False
    assert result["final_attempt_number"] == 2
    assert result["final_validation_status"] == "REJECTED"
    assert result["qualified_assembly_created"] is False
    assert len(client.responses.calls) == 2
    assert provider.ledger.fixture_repair_counts.get(fixtures[0]["fixture_id"], 0) == 0


def test_technical_failure_during_repair_cannot_start_third_request(fixtures):
    _, valid = _prompt_and_valid_draft(fixtures[0])
    invalid_payload = valid.model_dump(mode="json")
    invalid_payload["real_world_advice"][0]["text"] = "你必须辞职，这就是唯一正确的决定。"
    invalid = AINarrativeDraftContent.model_validate(invalid_payload)
    provider, client = _provider_for_fixture(
        fixtures[0], [_response(invalid), APITimeoutError()]
    )
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["technical_retry_attempted"] is False
    assert result["repair_attempted"] is True
    assert result["second_attempt_kind"] == "REPAIR"
    assert result["unresolved_provider_failure"] is True
    assert result["qualified_assembly_created"] is False
    assert result["final_validation_status"] == "NOT_RUN_PROVIDER_FAILURE"
    assert len(client.responses.calls) == 2
    assert provider.ledger.stage_request_count == 2


@pytest.mark.parametrize("status_code", [408, 409, 500, 503])
def test_only_approved_http_statuses_receive_one_technical_retry(fixtures, status_code):
    _, valid = _prompt_and_valid_draft(fixtures[0])
    provider, client = _provider_for_fixture(
        fixtures[0], [APIStatusError(status_code), _response(valid)]
    )
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["technical_retry_attempted"] is True
    assert result["qualified_assembly_created"] is True
    assert len(client.responses.calls) == 2


@pytest.mark.parametrize("non_retryable", [AuthenticationError(), APIStatusError(400)])
def test_non_retryable_transport_or_auth_error_never_retries(fixtures, non_retryable):
    provider, client = _provider_for_fixture(fixtures[0], [non_retryable])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["technical_retry_attempted"] is False
    assert result["repair_attempted"] is False
    assert result["unresolved_provider_failure"] is True
    assert len(client.responses.calls) == 1
    assert provider.ledger.stage_request_count == 1


@pytest.mark.parametrize("response_kind", ["SCHEMA", "REFUSAL"])
def test_schema_and_refusal_failures_never_retry(fixtures, response_kind):
    if response_kind == "SCHEMA":
        response = SimpleNamespace(
            id="schema-invalid",
            model=MODEL_ID,
            status="completed",
            output_text="{}",
            output=[],
            usage=None,
        )
    else:
        response = SimpleNamespace(
            id="refusal",
            model=MODEL_ID,
            status="completed",
            output_text="",
            output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
            usage=None,
        )
    provider, client = _provider_for_fixture(fixtures[0], [response])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["technical_retry_attempted"] is False
    assert result["repair_attempted"] is False
    assert result["unresolved_provider_failure"] is True
    assert len(client.responses.calls) == 1
    assert provider.ledger.stage_request_count == 1


def test_authentication_mapping_is_non_retryable_and_secret_free(fixtures):
    provider, client = _provider_for_fixture(fixtures[0], [AuthenticationError("secret")])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["failure_code"] == ProviderAuthenticationError.__name__
    assert "secret" not in json.dumps(result, ensure_ascii=False)
    assert len(client.responses.calls) == 1


def test_fake_request_snapshot_contains_exact_responses_configuration(fixtures):
    prompt, draft = _prompt_and_valid_draft(fixtures[0])
    client = FakeClient([_response(draft)])
    factory = FakeClientFactory(client)
    provider = create_live_provider(
        M1ALiveStage.SENTINEL,
        live_openai=True,
        environ=AUTH_ALL,
        client_factory=factory,
        token_counter=lambda value: 100,
    )
    provider.bind_fixture(
        fixtures[0]["fixture_id"], fixtures[0]["program_hash"], fixtures[0]["provider_catalog_hash"]
    )
    result = provider.generate(prompt, attempt_number=1)
    assert result.provider_name == "OPENAI_RESPONSES_API"
    assert factory.calls == 1
    assert factory.received_max_retries == SDK_MAX_RETRIES == 0
    assert factory.received_timeout == TIMEOUT_SECONDS == 120.0
    assert len(client.responses.calls) == 1
    assert client.responses.calls[0] == build_responses_request(prompt, FrozenResponsesConfig())


def test_key_never_appears_in_audit_error_or_export(fixtures, tmp_path):
    secret = "sk-" + "offline-secret-must-never-appear"
    env = {**AUTH_ALL, "OPENAI_API_KEY": secret}
    _, draft = _prompt_and_valid_draft(fixtures[0])
    client = FakeClient([_response(draft)])
    factory = FakeClientFactory(client)
    provider = create_live_provider(
        M1ALiveStage.SENTINEL,
        live_openai=True,
        environ=env,
        client_factory=factory,
        token_counter=lambda value: 100,
    )
    result = evaluate_live_fixture(fixtures[0], provider)
    output = {
        "results": [result],
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
    }
    output_path = tmp_path / "safe-output.json"
    write_safe_live_output(output, output_path)
    serialized = output_path.read_text(encoding="utf-8")
    assert secret not in serialized
    assert secret not in stable_error_text(provider)
    assert factory.received_key == secret


def stable_error_text(provider) -> str:
    return json.dumps([item.to_safe_dict() for item in provider.audits], sort_keys=True)


def test_all_release_and_commercial_gates_remain_closed(fixtures):
    _, draft = _prompt_and_valid_draft(fixtures[0])
    provider, _ = _provider_for_fixture(fixtures[0], [_response(draft)])
    result = evaluate_live_fixture(fixtures[0], provider)
    assert result["narrative_release_status"] == "UNVERIFIED"
    assert result["should_charge"] is False
    assert result["formal_report_persistence_allowed"] is False
    assert result["closed_beta_allowed"] is False


def test_four_sentinel_replays_execute_offline_with_zero_network(fixtures):
    sentinel_assets = json.loads((ASSET_ROOT / "sentinels.json").read_text(encoding="utf-8"))
    fixture_ids = tuple(item["fixture_id"] for item in sentinel_assets)
    by_id = {item["fixture_id"]: item for item in fixtures}
    drafts = [_prompt_and_valid_draft(by_id[fixture_id])[1] for fixture_id in fixture_ids]
    client = FakeClient([_response(draft, response_id=f"fake-{index}") for index, draft in enumerate(drafts)])
    provider = create_live_provider(
        M1ALiveStage.SENTINEL,
        live_openai=True,
        environ=AUTH_ALL,
        client_factory=FakeClientFactory(client),
        ledger=M1ABudgetLedger(M1ALiveStage.SENTINEL),
        token_counter=lambda value: 100,
    )
    output = run_live_evaluation(fixtures, fixture_ids, provider)
    assert output["summary"]["selected_cases"] == 4
    assert output["summary"]["qualified_assemblies"] == 4
    assert output["summary"]["requests_used"] == 4
    assert len(client.responses.calls) == 4
    assert all(
        audit["network_called"] is False
        for result in output["results"]
        for audit in result["request_audits"]
    )
    assert output["narrative_release_status"] == "UNVERIFIED"
    assert output["formal_report_generated"] is False


def test_stage_stops_immediately_after_unresolved_second_failure(fixtures):
    sentinel_assets = json.loads((ASSET_ROOT / "sentinels.json").read_text(encoding="utf-8"))
    fixture_ids = tuple(item["fixture_id"] for item in sentinel_assets)
    client = FakeClient([APITimeoutError(), APITimeoutError()])
    provider = create_live_provider(
        M1ALiveStage.SENTINEL,
        live_openai=True,
        environ=AUTH_ALL,
        client_factory=FakeClientFactory(client),
        ledger=M1ABudgetLedger(M1ALiveStage.SENTINEL),
        token_counter=lambda value: 100,
    )
    output = run_live_evaluation(fixtures, fixture_ids, provider)
    assert len(output["results"]) == 1
    assert output["results"][0]["unresolved_provider_failure"] is True
    assert output["summary"]["unresolved_provider_failures"] == 1
    assert output["summary"]["requests_used"] == 2
    assert len(client.responses.calls) == 2


def test_all_seventeen_fixture_replays_execute_offline(fixtures):
    fixture_ids = tuple(sorted(item["fixture_id"] for item in fixtures))
    by_id = {item["fixture_id"]: item for item in fixtures}
    drafts = [_prompt_and_valid_draft(by_id[fixture_id])[1] for fixture_id in fixture_ids]
    client = FakeClient([_response(draft, response_id=f"full-{index}") for index, draft in enumerate(drafts)])
    provider = create_live_provider(
        M1ALiveStage.FULL_FIXTURE,
        live_openai=True,
        environ=AUTH_ALL,
        client_factory=FakeClientFactory(client),
        ledger=M1ABudgetLedger(M1ALiveStage.FULL_FIXTURE),
        token_counter=lambda value: 100,
    )
    output = run_live_evaluation(fixtures, fixture_ids, provider)
    assert output["summary"]["selected_cases"] == 17
    assert output["summary"]["qualified_assemblies"] == 17
    assert output["summary"]["requests_used"] == 17
    assert len(client.responses.calls) == 17
    assert all(
        audit["external_model_called"] is False
        for result in output["results"]
        for audit in result["request_audits"]
    )


def test_malformed_structured_response_cannot_form_assembly(fixtures):
    prompt, _ = _prompt_and_valid_draft(fixtures[0])
    malformed = SimpleNamespace(
        id="malformed",
        model=MODEL_ID,
        status="completed",
        output_text="{}",
        output=[],
        usage=None,
    )
    provider, _ = _provider_for_fixture(fixtures[0], [malformed])
    with pytest.raises(ProviderSchemaError, match="M1A_OPENAI_RESPONSE_SCHEMA_INVALID"):
        provider.generate(prompt, attempt_number=1)
    assert len(provider.audits) == 1
    assert provider.audits[0].error_category == "ProviderSchemaError"


@pytest.mark.parametrize(
    ("extra_args", "expected_code"),
    [
        ((), M1ALiveFailureCode.LIVE_FLAG_REQUIRED),
        (("--live-openai",), M1ALiveFailureCode.MODEL_AUTHORIZATION_REQUIRED),
    ],
)
def test_cli_entrypoint_fails_closed_with_current_false_authorizations(
    tmp_path, extra_args, expected_code
):
    environment = os.environ.copy()
    environment.update(
        {
            "M1_A_MODEL_EVALUATION_AUTHORIZED": "false",
            "M1_A_SENTINEL_EVALUATION_AUTHORIZED": "false",
            "M1_A_FULL_FIXTURE_EVALUATION_AUTHORIZED": "false",
        }
    )
    environment.pop("OPENAI_API_KEY", None)
    output = tmp_path / "must-not-exist.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts" / "run_meihua_m1a_live_eval.py"),
            "--stage",
            "sentinel",
            "--output",
            str(output),
            *extra_args,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert completed.stderr.strip() == expected_code.value
    assert completed.stdout == ""
    assert not output.exists()
