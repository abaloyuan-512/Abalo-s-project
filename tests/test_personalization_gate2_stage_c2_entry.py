from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest

from scripts.run_personalization_gate2_stage_c2_retest import (
    AUTHORIZED_SPEND_USD,
    EXPECTED_GENERATION_CALLS,
    EXPECTED_OPENAI_SDK_VERSION,
    MINIMUM_DECLARED_BALANCE_USD,
    PAID_RETEST_AUTHORIZED,
    REQUIRED_RESERVE_USD,
    ROOT,
    validate_paid_retest_preflight,
    write_root_evidence_manifest,
)
from scripts import run_personalization_gate2_stage_c2_retest as stage_c2_entry


def _validate(output_root: Path, **updates: object) -> Path:
    values = {
        "confirmed": True,
        "generation_calls": EXPECTED_GENERATION_CALLS,
        "usable_budget_usd": AUTHORIZED_SPEND_USD,
        "declared_balance_usd": MINIMUM_DECLARED_BALANCE_USD,
        "required_reserve_usd": REQUIRED_RESERVE_USD,
        "openai_sdk_version": EXPECTED_OPENAI_SDK_VERSION,
        "api_key_present": True,
        "authorized": True,
        "authorization_consumed": False,
    }
    values.update(updates)
    return validate_paid_retest_preflight(output_root=output_root, **values)


def test_c2_paid_retest_authorization_is_consumed_and_locked(tmp_path: Path) -> None:
    assert PAID_RETEST_AUTHORIZED is True
    assert stage_c2_entry.PAID_RETEST_AUTHORIZATION_CONSUMED is True
    with pytest.raises(SystemExit, match="AUTHORIZATION_ALREADY_CONSUMED"):
        _validate(
            tmp_path / "new-stage-c2-evidence",
            authorized=PAID_RETEST_AUTHORIZED,
            authorization_consumed=True,
        )


def test_c2_consumed_main_stops_before_api_key_presence_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingEnvironment(dict[str, str]):
        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment inspected after consumption: {key}")

    monkeypatch.setattr(stage_c2_entry.os, "environ", _ExplodingEnvironment())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_personalization_gate2_stage_c2_retest.py",
            "--output-dir",
            str(tmp_path / "new-stage-c2-evidence"),
        ],
    )
    with pytest.raises(SystemExit, match="AUTHORIZATION_ALREADY_CONSUMED"):
        stage_c2_entry.main()


def test_c2_preflight_accepts_only_the_proposed_envelope(tmp_path: Path) -> None:
    output_root = tmp_path / "new-stage-c2-evidence"
    assert _validate(output_root) == output_root.resolve()
    assert not output_root.exists()
    assert AUTHORIZED_SPEND_USD == Decimal("0.50")
    assert MINIMUM_DECLARED_BALANCE_USD == Decimal("7.50")


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"confirmed": False}, "EXPLICIT_CONFIRMATION_REQUIRED"),
        ({"generation_calls": 0}, "GENERATION_CALL_LIMIT"),
        ({"generation_calls": 2}, "GENERATION_CALL_LIMIT"),
        ({"usable_budget_usd": Decimal("0.49")}, "USABLE_BUDGET"),
        ({"usable_budget_usd": Decimal("0.51")}, "USABLE_BUDGET"),
        (
            {"declared_balance_usd": Decimal("7.49")},
            "DECLARED_BALANCE_BELOW_REQUIRED_MINIMUM",
        ),
        ({"required_reserve_usd": Decimal("6.99")}, "REQUIRED_RESERVE"),
        ({"openai_sdk_version": "2.45.0"}, "OPENAI_SDK_VERSION_MISMATCH"),
        ({"api_key_present": False}, "OPENAI_API_KEY_NOT_CONFIGURED"),
        ({"authorization_consumed": True}, "AUTHORIZATION_ALREADY_CONSUMED"),
    ],
)
def test_c2_preflight_rejects_any_changed_confirmation(
    tmp_path: Path,
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(SystemExit, match=message):
        _validate(tmp_path / "new-stage-c2-evidence", **updates)


def test_c2_preflight_rejects_existing_or_repository_output(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="尚不存在"):
        _validate(existing)
    with pytest.raises(ValueError, match="仓库之外"):
        _validate(ROOT / "forbidden-stage-c2-evidence")


def test_c2_root_evidence_manifest_hashes_every_existing_file(tmp_path: Path) -> None:
    output_root = tmp_path / "evidence"
    nested = output_root / "nested"
    nested.mkdir(parents=True)
    (output_root / "summary.json").write_text("{}\n", encoding="utf-8")
    (nested / "checkpoint.json").write_text("{\"ok\":true}\n", encoding="utf-8")

    manifest_path = write_root_evidence_manifest(output_root)
    manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))

    assert set(manifest["files"]) == {
        "nested/checkpoint.json",
        "summary.json",
    }
    assert all(len(item["sha256"]) == 64 for item in manifest["files"].values())
