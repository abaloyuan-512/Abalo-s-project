from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from scripts.run_personalization_gate2_stage_c1_retest import (
    AUTHORIZED_SPEND_USD,
    DECLARED_BALANCE_USD,
    EXPECTED_GENERATION_CALLS,
    REQUIRED_RESERVE_USD,
    ROOT,
    validate_paid_retest_preflight,
)


def _validate(output_root: Path, **updates: object) -> Path:
    values = {
        "confirmed": True,
        "generation_calls": EXPECTED_GENERATION_CALLS,
        "usable_budget_usd": AUTHORIZED_SPEND_USD,
        "declared_balance_usd": DECLARED_BALANCE_USD,
        "required_reserve_usd": REQUIRED_RESERVE_USD,
        "api_key_present": True,
        "authorization_consumed": False,
    }
    values.update(updates)
    return validate_paid_retest_preflight(output_root=output_root, **values)


def test_paid_retest_preflight_accepts_only_the_exact_authorized_envelope(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "new-stage-c1-evidence"
    assert _validate(output_root) == output_root.resolve()
    assert not output_root.exists()
    assert DECLARED_BALANCE_USD - REQUIRED_RESERVE_USD >= AUTHORIZED_SPEND_USD


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"confirmed": False}, "EXPLICIT_CONFIRMATION_REQUIRED"),
        ({"generation_calls": 0}, "GENERATION_CALL_LIMIT"),
        ({"generation_calls": 2}, "GENERATION_CALL_LIMIT"),
        ({"usable_budget_usd": Decimal("0.44")}, "USABLE_BUDGET"),
        ({"usable_budget_usd": Decimal("0.46")}, "USABLE_BUDGET"),
        ({"declared_balance_usd": Decimal("8.84")}, "DECLARED_BALANCE"),
        ({"required_reserve_usd": Decimal("6.99")}, "REQUIRED_RESERVE"),
        ({"api_key_present": False}, "OPENAI_API_KEY_NOT_CONFIGURED"),
    ],
)
def test_paid_retest_preflight_rejects_any_changed_confirmation(
    tmp_path: Path,
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(SystemExit, match=message):
        _validate(tmp_path / "new-stage-c1-evidence", **updates)


def test_paid_retest_preflight_rejects_existing_or_repository_output(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="尚不存在"):
        _validate(existing)
    with pytest.raises(ValueError, match="仓库之外"):
        _validate(ROOT / "forbidden-stage-c1-evidence")


def test_paid_retest_preflight_blocks_any_second_execution(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="AUTHORIZATION_ALREADY_CONSUMED"):
        _validate(
            tmp_path / "different-new-output-does-not-bypass-the-lock",
            authorization_consumed=True,
        )
