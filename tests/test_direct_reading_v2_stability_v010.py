from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingProviderFailure,
    DirectReadingProviderResult,
    DirectReadingUsage,
)
from evals.meihua.direct_reading_v2_stability_v010.stability_executor import (
    FrozenStabilityCase,
    execute_case,
    load_frozen_cases,
    mechanical_mapping,
    run_sequential_batch,
)
from evals.meihua.direct_reading_v2_stability_v010 import run_stability_batch


ROOT = Path(__file__).parents[1]


def _json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


V009 = _json("outputs/v009_canary_real_result.json")
V009_TEXT = V009["direct_reading"]["text"]
V009_INPUT = V009["input"]
V009_CASE = FrozenStabilityCase(
    slot=1,
    case_id="FIXTURE-V009",
    domain="FIXTURE",
    input_type="FROZEN_AUTHORITY_REPLAY_WITHOUT_MODEL_CALL",
    question_text=V009_INPUT["question_text"],
    numbers=tuple(V009_INPUT["numbers"]),
    input_sha256=V009["input_sha256"],
)


class FixtureProvider:
    def __init__(
        self,
        text: str,
        *,
        status: str = "completed",
        incomplete_details: object | None = None,
        output_tokens: int = 3755,
    ) -> None:
        self.text = text
        self.status = status
        self.incomplete_details = incomplete_details
        self.output_tokens = output_tokens
        self.calls = 0

    def generate(self, **_: Any) -> DirectReadingProviderResult:
        self.calls += 1
        return DirectReadingProviderResult(
            output_text=self.text,
            api_status=self.status,
            incomplete_details=self.incomplete_details,
            response_id="fixture-response",
            model="gpt-5.6-sol",
            usage=DirectReadingUsage(
                input_tokens=687,
                output_tokens=self.output_tokens,
                total_tokens=687 + self.output_tokens,
            ),
            latency_ms=71066,
        )


def test_frozen_two_case_inputs_are_hash_locked_before_any_cast() -> None:
    document = _json("evals/meihua/direct_reading_v2_stability_v010/frozen_cases.json")

    cases = load_frozen_cases(document)

    assert [case.case_id for case in cases] == ["V010-01", "V010-02"]
    assert document["status"] == "FROZEN_BEFORE_ANY_V010_CAST_OR_PROVIDER_CALL"


def test_v009_authority_baseline_is_exact_and_historical_failures_are_unchanged() -> None:
    outcome = _json("evals/meihua/direct_reading_v2_stability_v009/final_outcome.json")
    v008 = _json("evals/meihua/direct_reading_v2_stability_v008/canary_outcome.json")
    s1 = _json("outputs/v007_s1_stage_summary.json")

    assert outcome["status"] == "SUCCESS"
    assert outcome["provider"]["reading_utf8_sha256"] == (
        "40376C23B51D91A36049242A3DCE24C2FD97C14AC57EBB17B0AD56AC3FF0CAAD"
    )
    assert outcome["provider"]["input_tokens"] == 687
    assert outcome["provider"]["output_tokens"] == 3755
    assert outcome["provider"]["total_tokens"] == 4442
    assert outcome["provider"]["latency_ms"] == 71066
    assert outcome["call_accounting"] == {
        "authorized_high_attempts": 1,
        "actual_high_attempts": 1,
        "remaining_high_attempts": 0,
        "router_attempts": 0,
        "automatic_retries": 0,
        "deterministic_cast_count": 1,
    }
    assert v008["verdict"] == "V008_CANARY_FAIL_STOP"
    assert v008["terminal_status"] == "INCOMPLETE"
    assert s1["verdict_before_independent_acceptance"] == "S1_FAIL_STOP"
    assert s1["aggregate"]["technical_and_release_success"] == "2/3"


def test_success_fixture_has_one_cast_one_provider_zero_retry_and_exact_mapping() -> None:
    provider = FixtureProvider(V009_TEXT)

    row = execute_case(V009_CASE, provider)

    assert provider.calls == 1
    assert row["status"] == "SUCCESS"
    assert row["deterministic_cast_count"] == 1
    assert row["provider_attempts"] == row["fixed_high_attempts"] == 1
    assert row["router_attempts"] == row["automatic_retries"] == 0
    assert row["validation_errors"] == []
    mapping = row["mechanical_mapping"]
    assert mapping["reconstructed_equals_source"] is True
    assert mapping["source_sha256"] == mapping["reconstructed_sha256"]
    assert mapping["model_calls_for_render"] == mapping["additional_casts"] == 0
    assert len(mapping["page8_model_sections"]) == 4
    assert mapping["page8_program_strength"]["source"] == (
        "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH"
    )
    assert len(mapping["page9_model_sections"]) == 5


def test_incomplete_fixture_is_not_released_and_still_consumes_the_slot() -> None:
    provider = FixtureProvider(
        V009_TEXT,
        status="incomplete",
        incomplete_details={"reason": "max_output_tokens"},
        output_tokens=12000,
    )

    row = execute_case(V009_CASE, provider)

    assert provider.calls == 1
    assert row["status"] == "INCOMPLETE"
    assert row["consumed"] is True
    assert row["released_direct_reading"] is None
    assert row["reading_utf8_sha256"] is None
    assert row["mechanical_mapping"] is None


def test_validation_block_fixture_is_not_released_and_still_consumes_the_slot() -> None:
    provider = FixtureProvider(V009_TEXT + "\n\n<script>alert(1)</script>")

    row = execute_case(V009_CASE, provider)

    assert provider.calls == 1
    assert row["status"] == "BLOCKED_OUTPUT"
    assert "DANGEROUS_MARKUP" in row["validation_errors"]
    assert row["consumed"] is True
    assert row["released_direct_reading"] is None
    assert row["mechanical_mapping"] is None


def test_provider_exception_is_counted_once_without_retry_or_release() -> None:
    class FailedProvider:
        calls = 0

        def generate(self, **_: Any) -> DirectReadingProviderResult:
            self.calls += 1
            raise DirectReadingProviderFailure("RATE_LIMIT")

    provider = FailedProvider()

    row = execute_case(V009_CASE, provider)

    assert provider.calls == 1
    assert row["status"] == "UNAVAILABLE"
    assert row["provider_attempts"] == 1
    assert row["automatic_retries"] == 0
    assert row["released_direct_reading"] is None


def test_first_failure_stops_second_provider_but_denominator_remains_two() -> None:
    first = FixtureProvider(V009_TEXT, status="incomplete", incomplete_details={"reason": "x"})
    second = FixtureProvider(V009_TEXT)
    cases = (V009_CASE, FrozenStabilityCase(**{**V009_CASE.__dict__, "slot": 2, "case_id": "FIXTURE-2"}))

    batch = run_sequential_batch(cases, lambda case: first if case.slot == 1 else second)

    assert first.calls == 1
    assert second.calls == 0
    assert batch["actual_provider_attempts"] == 1
    assert batch["remaining_unexecuted"] == 1
    assert batch["success_count"] == 0
    assert batch["success_denominator"] == 2
    assert batch["technical_success_rate"] == 0
    assert batch["stopped_on_first_failure"] is True


def test_mapping_failure_is_a_terminal_row_and_remains_in_full_denominator(monkeypatch) -> None:
    malformed = FixtureProvider(V009_TEXT)
    second = FixtureProvider(V009_TEXT)
    cases = (V009_CASE, FrozenStabilityCase(**{**V009_CASE.__dict__, "slot": 2, "case_id": "FIXTURE-2"}))
    from evals.meihua.direct_reading_v2_stability_v010 import stability_executor

    monkeypatch.setattr(
        stability_executor,
        "mechanical_mapping",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("synthetic mapping")),
    )

    batch = run_sequential_batch(cases, lambda case: malformed if case.slot == 1 else second)

    assert malformed.calls == 1
    assert second.calls == 0
    assert batch["cases"][0]["status"] == "MAPPING_FAILED"
    assert batch["cases"][0]["provider_attempts"] == 1
    assert batch["cases"][0]["released_direct_reading"] is None
    assert batch["success_denominator"] == 2
    assert batch["technical_success_rate"] == 0


def test_unexpected_executor_exception_is_recorded_and_stops_the_batch() -> None:
    class BrokenFactory:
        def __call__(self, _: FrozenStabilityCase) -> FixtureProvider:
            raise RuntimeError("synthetic")

    batch = run_sequential_batch((V009_CASE,), BrokenFactory())

    assert batch["cases"][0]["status"] == "EXECUTOR_FAILED"
    assert batch["cases"][0]["validation_errors"] == ["EXECUTOR:RuntimeError"]
    assert batch["success_denominator"] == 1


def test_runner_refuses_zero_authority_before_provider_instantiation(tmp_path: Path, monkeypatch) -> None:
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(
            {
                "stage_id": "DIRECT_READING_V2_STABILITY_V010",
                "candidate_manifest_sha256": "not-the-manifest",
                "explicit_user_authorization": False,
                "authorized_fixed_high_attempts": 0,
                "router_attempts": 0,
                "automatic_retries": 0,
                "replacement_cases_allowed": False,
                "stop_on_first_failure": True,
            }
        ),
        encoding="utf-8",
    )
    calls = 0

    def provider_factory() -> FixtureProvider:
        nonlocal calls
        calls += 1
        return FixtureProvider(V009_TEXT)

    monkeypatch.setattr(run_stability_batch, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(run_stability_batch, "file_sha", lambda _: "frozen-manifest")

    with pytest.raises(RuntimeError, match="EXACT_NUMERIC_AUTHORIZATION_REQUIRED"):
        run_stability_batch.run(
            authorization,
            provider_factory=provider_factory,
            result_path=tmp_path / "result.json",
        )

    assert calls == 0
    assert not (tmp_path / "result.json").exists()


def test_persistent_runner_records_started_before_call_and_mapping_failure_as_one_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    result_path = tmp_path / "result.json"
    manifest_sha = "frozen-manifest"
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(
            {
                "stage_id": "DIRECT_READING_V2_STABILITY_V010",
                "candidate_manifest_sha256": manifest_sha,
                "explicit_user_authorization": True,
                "authorized_fixed_high_attempts": 2,
                "router_attempts": 0,
                "automatic_retries": 0,
                "replacement_cases_allowed": False,
                "stop_on_first_failure": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_stability_batch, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(run_stability_batch, "file_sha", lambda _: manifest_sha)
    monkeypatch.setattr(
        run_stability_batch,
        "CASES",
        ROOT / "evals/meihua/direct_reading_v2_stability_v010/frozen_cases.json",
    )
    provider_calls = 0

    def provider_factory() -> object:
        nonlocal provider_calls
        snapshot = json.loads(result_path.read_text(encoding="utf-8"))
        assert snapshot["provider_instantiated"] is True
        assert snapshot["cases"][-1]["status"] == "STARTED"
        assert snapshot["cases"][-1]["provider_attempts"] is None
        provider_calls += 1
        return object()

    def mapping_failure(case: FrozenStabilityCase, _provider: object) -> dict[str, Any]:
        return {
            "slot": case.slot,
            "case_id": case.case_id,
            "input_sha256": case.input_sha256,
            "status": "MAPPING_FAILED",
            "consumed": True,
            "deterministic_cast_count": 1,
            "fixed_high_attempts": 1,
            "provider_attempts": 1,
            "router_attempts": 0,
            "automatic_retries": 0,
            "validation_errors": ["MECHANICAL_MAPPING:ValueError"],
            "usage": {"input_tokens": 687, "output_tokens": 3755, "total_tokens": 4442},
            "latency_ms": 71066,
            "reading_utf8_sha256": None,
            "released_direct_reading": None,
            "mechanical_mapping": None,
        }

    monkeypatch.setattr(run_stability_batch, "execute_case", mapping_failure)

    ledger = run_stability_batch.run(
        authorization,
        provider_factory=provider_factory,
        result_path=result_path,
    )

    assert provider_calls == 1
    assert ledger["status"] == "FAIL_STOP"
    assert ledger["actual_fixed_high_attempts"] == 1
    assert ledger["remaining_fixed_high_attempts"] == 1
    assert ledger["cases"][0]["status"] == "MAPPING_FAILED"
    assert ledger["cases"][0]["provider_attempts"] == 1
    assert ledger["success_denominator"] == 2
    assert ledger["technical_success_rate"] == 0


@pytest.mark.parametrize("mutation", ["text", "p8_p9_swap"])
def test_any_text_mutation_or_page_role_swap_fails_mechanical_mapping(mutation: str) -> None:
    facts = V009["chart_facts"]
    program = {"source": "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH"}
    text = V009_TEXT
    if mutation == "text":
        text += "改"
    else:
        sections = [part for part in text.split("\n\n")]
        sections[0], sections[-1] = sections[-1], sections[0]
        text = "\n\n".join(sections)

    with pytest.raises(ValueError):
        mechanical_mapping(text, facts, program, V009["reading_utf8_sha256"])


def test_offline_ledger_has_zero_authority_and_never_instantiated_provider() -> None:
    ledger = _json("outputs/v010_stability_call_ledger.json")

    assert ledger["proposed_fixed_high_attempts"] == 2
    assert ledger["authorized_fixed_high_attempts"] == 0
    assert ledger["actual_fixed_high_attempts"] == 0
    assert ledger["router_attempts"] == ledger["automatic_retries"] == 0
    assert ledger["provider_instantiated"] is False
    assert ledger["cases"] == []
    assert ledger["deployment"] is ledger["production"] is False
