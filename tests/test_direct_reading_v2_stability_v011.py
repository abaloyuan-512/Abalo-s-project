from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.meihua.direct_reading_v2_stability_v011 import run_stability_batch as runner


ROOT = Path(__file__).parents[1]
V010_MANIFEST_SHA = "9AC57B5C7CD873C23AA8F2833D115616813F4C3F763BDBB713FADF8641405D0E"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _authorization(path: Path, manifest_sha: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "stage_id": runner.STAGE_ID,
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
    return path


def _row(case: Any, status: str) -> dict[str, Any]:
    return {
        "slot": case.slot,
        "case_id": case.case_id,
        "input_sha256": case.input_sha256,
        "status": status,
        "consumed": True,
        "deterministic_cast_count": 1,
        "fixed_high_attempts": 1,
        "provider_attempts": 1,
        "router_attempts": 0,
        "automatic_retries": 0,
        "validation_errors": [] if status == "SUCCESS" else [status],
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        "latency_ms": 1,
        "reading_utf8_sha256": "A" * 64 if status == "SUCCESS" else None,
        "released_direct_reading": {"text": "fixture"} if status == "SUCCESS" else None,
        "mechanical_mapping": {"fixture": True} if status == "SUCCESS" else None,
    }


def _run_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[str],
) -> tuple[dict[str, Any], list[str], list[str], Path]:
    manifest_sha = "v011-fixture-manifest"
    authorization = _authorization(tmp_path / "authorization.json", manifest_sha)
    result_path = tmp_path / "result.json"
    provider_cases: list[str] = []
    execute_cases: list[str] = []
    monkeypatch.setattr(runner, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(runner, "file_sha", lambda _: manifest_sha)

    class Provider:
        pass

    def provider_factory() -> Provider:
        provider = Provider()
        provider_cases.append("instantiated")
        return provider

    def execute_case(case: Any, _provider: Provider) -> dict[str, Any]:
        execute_cases.append(case.case_id)
        return _row(case, statuses[len(execute_cases) - 1])

    monkeypatch.setattr(runner, "execute_case", execute_case)
    ledger = runner.run(
        authorization,
        provider_factory=provider_factory,
        result_path=result_path,
    )
    return ledger, provider_cases, execute_cases, result_path


def _assert_identity_and_conservation(ledger: dict[str, Any]) -> None:
    frozen = _json(runner.CASES)
    expected = [
        (row["slot"], row["case_id"], row["input_sha256"])
        for row in frozen["cases"]
    ]
    actual = [
        (row["slot"], row["case_id"], row["input_sha256"])
        for row in ledger["cases"]
    ]
    assert actual == expected
    attempts = sum(row["provider_attempts"] for row in ledger["cases"])
    consumed = sum(row["consumed"] is True for row in ledger["cases"])
    unexecuted = sum(row["status"] == runner.NOT_EXECUTED for row in ledger["cases"])
    success = sum(row["status"] == "SUCCESS" for row in ledger["cases"])
    assert len(ledger["cases"]) == ledger["authorized_fixed_high_attempts"] == 2
    assert ledger["actual_fixed_high_attempts"] == attempts == consumed
    assert ledger["remaining_fixed_high_attempts"] == 2 - attempts == unexecuted
    assert ledger["success_denominator"] == 2
    assert ledger["success_count"] == success
    assert ledger["technical_success_rate"] == success / 2


def test_first_failure_writes_second_case_not_executed_without_provider_or_cast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, providers, executed, result_path = _run_fixture(
        tmp_path, monkeypatch, ["INCOMPLETE"]
    )

    assert providers == ["instantiated"]
    assert executed == ["V010-01"]
    assert ledger["status"] == "FAIL_STOP"
    assert [row["status"] for row in ledger["cases"]] == [
        "INCOMPLETE",
        runner.NOT_EXECUTED,
    ]
    skipped = ledger["cases"][1]
    assert skipped["consumed"] is False
    assert skipped["deterministic_cast_count"] == 0
    assert skipped["fixed_high_attempts"] == 0
    assert skipped["provider_attempts"] == 0
    assert skipped["router_attempts"] == skipped["automatic_retries"] == 0
    assert skipped["validation_errors"] == []
    assert skipped["usage"] is skipped["latency_ms"] is None
    assert skipped["reading_utf8_sha256"] is None
    assert skipped["released_direct_reading"] is skipped["mechanical_mapping"] is None
    assert skipped["prior_failure_case_id"] == "V010-01"
    assert skipped["prior_failure_status"] == "INCOMPLETE"
    assert skipped["not_executed_reason"] == "PRIOR_FAILURE:V010-01:INCOMPLETE"
    _assert_identity_and_conservation(ledger)
    assert _json(result_path) == ledger


def test_first_success_second_failure_has_two_attempts_and_no_placeholder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, providers, executed, result_path = _run_fixture(
        tmp_path, monkeypatch, ["SUCCESS", "MAPPING_FAILED"]
    )

    assert len(providers) == 2
    assert executed == ["V010-01", "V010-02"]
    assert [row["status"] for row in ledger["cases"]] == ["SUCCESS", "MAPPING_FAILED"]
    assert ledger["status"] == "FAIL_STOP"
    assert ledger["not_executed_count"] == 0
    _assert_identity_and_conservation(ledger)
    assert _json(result_path) == ledger


def test_all_success_has_two_attempts_and_no_placeholder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, providers, executed, result_path = _run_fixture(
        tmp_path, monkeypatch, ["SUCCESS", "SUCCESS"]
    )

    assert len(providers) == 2
    assert executed == ["V010-01", "V010-02"]
    assert [row["status"] for row in ledger["cases"]] == ["SUCCESS", "SUCCESS"]
    assert ledger["status"] == "COMPLETE"
    assert ledger["not_executed_count"] == 0
    _assert_identity_and_conservation(ledger)
    assert _json(result_path) == ledger


def test_zero_authority_is_rejected_before_provider_instantiation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization = tmp_path / "authorization.json"
    authorization.write_text("{}", encoding="utf-8")
    calls = 0
    monkeypatch.setattr(runner, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(runner, "file_sha", lambda _: "manifest")

    def provider_factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    with pytest.raises(RuntimeError, match="EXACT_NUMERIC_AUTHORIZATION_REQUIRED"):
        runner.run(
            authorization,
            provider_factory=provider_factory,
            result_path=tmp_path / "result.json",
        )
    assert calls == 0
    assert not (tmp_path / "result.json").exists()


def test_provider_factory_failure_becomes_one_terminal_attempt_then_placeholder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_sha = "v011-fixture-manifest"
    authorization = _authorization(tmp_path / "authorization.json", manifest_sha)
    result_path = tmp_path / "result.json"
    factory_calls = 0
    executed: list[str] = []
    monkeypatch.setattr(runner, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(runner, "file_sha", lambda _: manifest_sha)

    def provider_factory() -> object:
        nonlocal factory_calls
        factory_calls += 1
        raise RuntimeError("synthetic construction failure")

    def execute_case(case: Any, provider: object) -> dict[str, Any]:
        executed.append(case.case_id)
        with pytest.raises(RuntimeError, match="synthetic construction failure"):
            provider.generate()
        return _row(case, "UNAVAILABLE")

    monkeypatch.setattr(runner, "execute_case", execute_case)
    ledger = runner.run(
        authorization,
        provider_factory=provider_factory,
        result_path=result_path,
    )

    assert factory_calls == 1
    assert executed == ["V010-01"]
    assert [row["status"] for row in ledger["cases"]] == [
        "UNAVAILABLE",
        runner.NOT_EXECUTED,
    ]
    assert ledger["actual_fixed_high_attempts"] == 1
    assert ledger["remaining_fixed_high_attempts"] == 1
    _assert_identity_and_conservation(ledger)
    assert _json(result_path) == ledger


def test_unexpected_executor_exception_is_terminal_and_completes_case_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_sha = "v011-fixture-manifest"
    authorization = _authorization(tmp_path / "authorization.json", manifest_sha)
    result_path = tmp_path / "result.json"
    provider_calls = 0
    execute_calls = 0
    monkeypatch.setattr(runner, "verify_candidate_manifest", lambda: {})
    monkeypatch.setattr(runner, "file_sha", lambda _: manifest_sha)

    def provider_factory() -> object:
        nonlocal provider_calls
        provider_calls += 1
        return object()

    def execute_case(_case: Any, _provider: object) -> dict[str, Any]:
        nonlocal execute_calls
        execute_calls += 1
        raise RuntimeError("synthetic executor failure after dispatch")

    monkeypatch.setattr(runner, "execute_case", execute_case)
    ledger = runner.run(
        authorization,
        provider_factory=provider_factory,
        result_path=result_path,
    )

    assert provider_calls == execute_calls == 1
    assert [row["status"] for row in ledger["cases"]] == [
        "EXECUTOR_FAILED",
        runner.NOT_EXECUTED,
    ]
    assert ledger["cases"][0]["provider_attempts"] == 1
    assert ledger["cases"][1]["provider_attempts"] == 0
    _assert_identity_and_conservation(ledger)
    assert _json(result_path) == ledger


def test_v010_frozen_failure_and_manifest_are_unchanged() -> None:
    assert runner.file_sha(
        ROOT / "evals/meihua/direct_reading_v2_stability_v010/candidate_manifest.json"
    ) == V010_MANIFEST_SHA
    outcome = _json(ROOT / "evals/meihua/direct_reading_v2_stability_v010/final_outcome.json")
    acceptance = _json(
        ROOT / "evals/meihua/direct_reading_v2_stability_v010/independent_acceptance_result.json"
    )
    assert outcome["verdict"] == "OFFLINE_CANDIDATE_FAIL_STOP"
    assert acceptance["verdict"] == "FAIL"


def test_v011_offline_ledger_has_zero_authority_and_no_provider() -> None:
    ledger = _json(ROOT / "outputs/v011_stability_call_ledger.json")
    assert ledger["authorized_fixed_high_attempts"] == 0
    assert ledger["actual_fixed_high_attempts"] == 0
    assert ledger["provider_instantiated"] is False
    assert ledger["cases"] == []
    assert ledger["router_attempts"] == ledger["automatic_retries"] == 0
    assert ledger["deployment"] is ledger["production"] is False
