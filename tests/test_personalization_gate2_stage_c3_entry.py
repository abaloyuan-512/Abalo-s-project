from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from abalo_iching.personalization_gate2.models import (
    DryRunStatus,
    Gate2Usage,
    Gate2ValidationReport,
)
from scripts import run_personalization_gate2_stage_c3_visible_chart_arms as stage_c3


def _validate(output_root: Path, **updates: object) -> Path:
    values = {
        "confirmed": True,
        "generation_calls": stage_c3.EXPECTED_GENERATION_CALLS,
        "usable_budget_usd": stage_c3.AUTHORIZED_SPEND_USD,
        "declared_balance_usd": stage_c3.MINIMUM_DECLARED_BALANCE_USD,
        "required_reserve_usd": stage_c3.REQUIRED_RESERVE_USD,
        "openai_sdk_version": stage_c3.EXPECTED_OPENAI_SDK_VERSION,
        "api_key_present": True,
        "authorized": True,
        "authorization_consumed": False,
    }
    values.update(updates)
    return stage_c3.validate_paid_preflight(output_root=output_root, **values)


def test_c3_paid_entry_is_default_closed() -> None:
    assert stage_c3.PAID_VISIBLE_CHART_ARMS_AUTHORIZED is False
    assert stage_c3.PAID_VISIBLE_CHART_ARMS_AUTHORIZATION_CONSUMED is False


def test_c3_main_stops_before_api_key_presence_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingEnvironment(dict[str, str]):
        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment inspected before authorization: {key}")

    monkeypatch.setattr(stage_c3.os, "environ", _ExplodingEnvironment())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_personalization_gate2_stage_c3_visible_chart_arms.py",
            "--output-dir",
            str(tmp_path / "new-stage-c3-evidence"),
        ],
    )
    with pytest.raises(SystemExit, match="NOT_AUTHORIZED"):
        stage_c3.main()


def test_c3_explicit_confirmation_stops_before_api_key_presence_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingEnvironment(dict[str, str]):
        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment inspected before confirmation: {key}")

    monkeypatch.setattr(stage_c3, "PAID_VISIBLE_CHART_ARMS_AUTHORIZED", True)
    monkeypatch.setattr(stage_c3.os, "environ", _ExplodingEnvironment())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_personalization_gate2_stage_c3_visible_chart_arms.py",
            "--output-dir",
            str(tmp_path / "new-stage-c3-evidence"),
        ],
    )
    with pytest.raises(SystemExit, match="EXPLICIT_CONFIRMATION_REQUIRED"):
        stage_c3.main()


def test_c3_preflight_accepts_only_the_proposed_envelope(tmp_path: Path) -> None:
    output_root = tmp_path / "new-stage-c3-evidence"
    assert _validate(output_root) == output_root.resolve()
    assert not output_root.exists()
    assert stage_c3.AUTHORIZED_SPEND_USD == Decimal("1.00")
    assert stage_c3.MINIMUM_DECLARED_BALANCE_USD == Decimal("8.00")


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"confirmed": False}, "EXPLICIT_CONFIRMATION_REQUIRED"),
        ({"generation_calls": 1}, "GENERATION_CALL_LIMIT"),
        ({"generation_calls": 3}, "GENERATION_CALL_LIMIT"),
        ({"usable_budget_usd": Decimal("0.99")}, "USABLE_BUDGET"),
        ({"usable_budget_usd": Decimal("1.01")}, "USABLE_BUDGET"),
        (
            {"declared_balance_usd": Decimal("7.99")},
            "DECLARED_BALANCE_BELOW_REQUIRED_MINIMUM",
        ),
        ({"required_reserve_usd": Decimal("6.99")}, "REQUIRED_RESERVE"),
        ({"openai_sdk_version": "2.45.0"}, "OPENAI_SDK_VERSION_MISMATCH"),
        ({"api_key_present": False}, "OPENAI_API_KEY_NOT_CONFIGURED"),
        ({"authorized": False}, "NOT_AUTHORIZED"),
        ({"authorization_consumed": True}, "AUTHORIZATION_ALREADY_CONSUMED"),
    ],
)
def test_c3_preflight_rejects_any_changed_confirmation(
    tmp_path: Path,
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(SystemExit, match=message):
        _validate(tmp_path / "new-stage-c3-evidence", **updates)


def test_c3_preflight_rejects_existing_or_repository_output(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="尚不存在"):
        _validate(existing)
    with pytest.raises(ValueError, match="仓库之外"):
        _validate(stage_c3.ROOT / "forbidden-stage-c3-evidence")


class _FakeProvider:
    reasoning_effort = "medium"
    max_output_tokens = 10_000

    def __init__(self) -> None:
        self.call_count = 0
        self.poll_count = 0


def _provider_factory(**kwargs: object) -> _FakeProvider:
    return _FakeProvider()


def _runner_factory(
    statuses: dict[str, DryRunStatus],
):
    class _FakeRunner:
        def __init__(self, *, repository_root: Path, budget_guard: object) -> None:
            self.budget_guard = budget_guard

        def run(self, request: object, *, provider: _FakeProvider, evidence_root: Path):
            arm = request.metadata.arm.value
            provider.call_count = 1
            provider.poll_count = 1
            self.budget_guard.record_actual_cost(Decimal("0.10"))
            status = statuses[arm]
            validation = Gate2ValidationReport()
            if status is not DryRunStatus.VALIDATED:
                validation = Gate2ValidationReport(
                    quality_failures=[
                        {
                            "code": "offline_forced_failure",
                            "message": "forced failure for orchestration test",
                        }
                    ]
                )
            return SimpleNamespace(
                status=status,
                validation=validation,
                evidence_record=SimpleNamespace(
                    response_id=f"resp-{arm}",
                    api_status="completed",
                    incomplete_reason=None,
                    usage=Gate2Usage(
                        input_tokens=100,
                        output_tokens=100,
                        total_tokens=200,
                    ),
                    cost_usd=0.10,
                    first_raw_output={"arm": arm},
                ),
                evidence_directory=str(evidence_root / "G2CAL-001" / arm),
            )

    return _FakeRunner


def test_c3_offline_orchestration_runs_c_then_d_and_writes_manifest(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "stage-c3-evidence"
    summary = stage_c3.run(
        output_root,
        declared_balance_usd=Decimal("8.00"),
        provider_factory=_provider_factory,
        runner_factory=_runner_factory(
            {
                "C": DryRunStatus.VALIDATED,
                "D": DryRunStatus.VALIDATED,
            }
        ),
    )

    assert summary["status"] == "READY_FOR_BLIND_REVIEW"
    assert summary["arms_attempted"] == ["C", "D"]
    assert summary["generation_calls"] == 2
    assert summary["actual_cost_usd"] == "0.20"
    assert (output_root / "visible_calibration_input_C.json").is_file()
    assert (output_root / "visible_calibration_input_D.json").is_file()
    assert (output_root / "evidence_manifest.json").is_file()


def test_c3_offline_orchestration_stops_before_d_when_c_fails(
    tmp_path: Path,
) -> None:
    summary = stage_c3.run(
        tmp_path / "stage-c3-evidence",
        declared_balance_usd=Decimal("8.00"),
        provider_factory=_provider_factory,
        runner_factory=_runner_factory(
            {
                "C": DryRunStatus.FAILED_VALIDATION,
                "D": DryRunStatus.VALIDATED,
            }
        ),
    )

    assert summary["status"] == "HARD_STOP_C_FAILED_VALIDATION"
    assert summary["arms_attempted"] == ["C"]
    assert summary["generation_calls"] == 1
    assert summary["actual_cost_usd"] == "0.10"
