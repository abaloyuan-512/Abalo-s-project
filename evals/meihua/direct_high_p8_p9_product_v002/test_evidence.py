from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_high_p8_p9_product_v002"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_builder():
    path = STAGE / "build_offline_evidence.py"
    spec = importlib.util.spec_from_file_location("direct_high_p8_p9_v002_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_ledger_rebuilds_byte_for_byte(tmp_path: Path) -> None:
    rebuilt = tmp_path / "v002-offline-ledger.json"
    assert load_builder().main(rebuilt) == 0
    assert rebuilt.read_bytes() == (STAGE / "offline_ledger.json").read_bytes()


def test_denominator_negative_matrix_and_atomic_release_are_complete() -> None:
    ledger = json.loads((STAGE / "offline_ledger.json").read_text(encoding="utf-8"))
    contract = json.loads((STAGE / "acceptance_contract.json").read_text(encoding="utf-8"))
    rows = ledger["rows"]
    assert ledger["case_denominator"] == len(rows) == 15
    assert ledger["success_count"] == ledger["released_count"] == 3
    assert ledger["failed_count"] == ledger["blocked_count"] == 12
    assert set(contract["required_negative_kinds"]).issubset(ledger["negative_kind_counts"])
    assert set(contract["additional_boundary_rows"]).issubset(ledger["negative_kind_counts"])
    assert sum(ledger["negative_kind_counts"].values()) == ledger["failed_count"]
    assert all(row["prepare_attempts"] == row["deterministic_cast_count"] == row["provider_attempts"] == row["fixed_high_attempts"] == 1 for row in rows)
    assert ledger["prepare_attempts"] == ledger["deterministic_cast_count"] == ledger["provider_attempts"] == ledger["fixed_high_attempts"] == len(rows)
    assert all(row["released"] or (row["direct_reading_null"] and row["presentation_null"] and row["direct_high_null"]) for row in rows)
    assert ledger["router_attempts"] == ledger["router_live_calls"] == ledger["router_model_calls"] == 0
    assert ledger["automatic_retries"] == ledger["mapping_model_calls"] == ledger["mapping_additional_casts"] == 0


def test_v001_candidate_and_product_sources_remain_byte_locked() -> None:
    manifest_path = ROOT / "evals/meihua/direct_high_p8_p9_product_v001/candidate_manifest.json"
    assert sha(manifest_path) == "3A8B644C2D685F208EA815DE60A15E3785B1EB07C8F10FC4FCD42DE8DE498B4D"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["candidate_files"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"]
    final = json.loads((ROOT / "evals/meihua/direct_high_p8_p9_product_v001/final_outcome.json").read_text(encoding="utf-8"))
    assert final["verdict"] == "OFFLINE_CANDIDATE_FAIL_STOP"


def test_v002_evidence_code_has_no_runtime_router_or_live_provider_imports() -> None:
    source = (STAGE / "build_offline_evidence.py").read_text(encoding="utf-8")
    imports = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any("router" in name.lower() for name in imports)
    assert "OpenAI" not in source
    assert "API_KEY" not in source
