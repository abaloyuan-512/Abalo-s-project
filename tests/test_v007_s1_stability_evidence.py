from __future__ import annotations

import hashlib
import json
from pathlib import Path

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingChartFacts,
    validate_direct_reading_text,
)


ROOT = Path(__file__).parents[1]
OUTPUTS = ROOT / "outputs"


def _json(name: str) -> dict:
    return json.loads((OUTPUTS / name).read_text(encoding="utf-8"))


def test_s1_freeze_and_ledger_account_for_all_three_slots() -> None:
    freeze_path = OUTPUTS / "v007_s1_case_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    ledger = _json("v007_s1_call_ledger.json")

    assert hashlib.sha256(freeze_path.read_bytes()).hexdigest().upper() == ledger["freeze_sha256"]
    assert freeze["case_order"] == ["S1-01", "S1-02", "S1-03"]
    assert ledger["authorized_high_attempts"] == 3
    assert ledger["actual_high_attempts"] == 3
    assert ledger["remaining_high_attempts"] == 0
    assert ledger["automatic_retries"] == 0
    assert [row["case_id"] for row in ledger["cases"]] == freeze["case_order"]
    assert [row["status"] for row in ledger["cases"]] == ["SUCCESS", "BLOCKED_OUTPUT", "SUCCESS"]
    assert all(row["provider_attempts"] == 1 for row in ledger["cases"])
    assert all(row["deterministic_cast_count"] == 1 for row in ledger["cases"])


def test_successful_s1_outputs_reconstruct_exactly() -> None:
    for case in ("01", "03"):
        result = _json(f"v007_s1_{case}_real_result.json")
        provenance = _json(f"v007_s1_{case}_provenance.json")
        source = result["direct_reading"]["text"]
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest().upper()

        assert result["status"] == "SUCCESS"
        assert result["validation_errors"] == []
        assert source_sha == result["reading_utf8_sha256"]
        assert provenance["reconstructed_equals_source"] is True
        assert provenance["reconstructed_reading_utf8_sha256"] == source_sha
        assert provenance["model_calls_for_render"] == 0
        assert provenance["program_strength"]["additional_casts"] == 0


def test_release_gate_currently_blocks_restatement_of_explicit_user_background() -> None:
    source = _json("v007_s1_01_real_result.json")
    facts = DirectReadingChartFacts.model_validate(source["chart_facts"])
    explicit_question = "我和伴侣已经形成共同方案；我们应该现在落实，还是推迟？"
    faithfully_attributed = (
        source["direct_reading"]["text"]
        + "\n\n根据你在问题中明确提供的背景，你们已经形成共同方案。"
    )

    errors = validate_direct_reading_text(
        faithfully_attributed,
        question_text=explicit_question,
        facts=facts,
    )

    assert "UNSUPPORTED_REALITY_FACT" in errors


def test_release_gate_also_blocks_invented_reality_so_detector_cannot_be_removed() -> None:
    source = _json("v007_s1_01_real_result.json")
    facts = DirectReadingChartFacts.model_validate(source["chart_facts"])
    invented = source["direct_reading"]["text"] + "\n\n你们已经完成全部资金准备和家庭沟通。"

    errors = validate_direct_reading_text(
        invented,
        question_text="我应该接受新工作吗？",
        facts=facts,
    )

    assert "UNSUPPORTED_REALITY_FACT" in errors

