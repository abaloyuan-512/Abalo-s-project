from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evals.meihua.direct_reading_v2_implementation_v002 import run_v002_experiment as runner
from evals.meihua.direct_reading_v2_implementation_v002 import build_medium_blind_pack as blind_builder


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_v002_case_plan_is_nine_questions_with_three_latency_cases() -> None:
    indexed = runner.case_index()
    assert len(indexed) == 9
    assert runner.MEDIUM_CASE_IDS == ("DR-01-Q1", "DR-03-Q2", "DR-04-Q2")
    assert {indexed[case_id]["question_text"] for case_id in runner.MEDIUM_CASE_IDS} == {
        "我要不要考虑换工作这件事？",
        "对方多次延期后，我还要继续追加预算吗？",
        "我们反复争执后，我还要继续维持吗？",
    }


def test_execution_freeze_checks_archive_and_every_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    snapshot = tmp_path / "execution.zip"
    source = tmp_path / "source.py"
    snapshot.write_bytes(b"snapshot")
    source.write_bytes(b"source")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    manifest = {
        "execution_snapshot": {"path": "execution.zip", "sha256": _sha(snapshot)},
        "execution_files": {"source.py": _sha(source)},
        "execution_trees": {},
        "automatic_retry_limit": 0,
        "live_model_call_limit": 5,
    }
    runner.verify_execution_freeze(manifest)
    source.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="EXECUTION_FILE_MISMATCH"):
        runner.verify_execution_freeze(manifest)


def test_execution_freeze_detects_built_sites_tree_drift(monkeypatch, tmp_path: Path) -> None:
    snapshot = tmp_path / "execution.zip"
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.js").write_text("frozen", encoding="utf-8")
    snapshot.write_bytes(b"snapshot")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    manifest = {
        "execution_snapshot": {"path": "execution.zip", "sha256": _sha(snapshot)},
        "execution_files": {},
        "execution_trees": {"dist": runner.sha_tree(dist)},
        "automatic_retry_limit": 0,
        "live_model_call_limit": 5,
    }
    runner.verify_execution_freeze(manifest)
    (dist / "chunk.js").write_text("drift", encoding="utf-8")
    with pytest.raises(RuntimeError, match="EXECUTION_TREE_MISMATCH"):
        runner.verify_execution_freeze(manifest)


def test_exclusive_marker_is_single_use(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "RUNS", tmp_path)
    runner.exclusive_marker("only-once")
    with pytest.raises(FileExistsError):
        runner.exclusive_marker("only-once")


def test_live_preflight_fails_before_a_marker_when_configuration_is_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(runner, "RUNS", tmp_path)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY_MISSING"):
        runner.verify_live_preflight()
    assert list(tmp_path.iterdir()) == []


def test_final_budget_gate_separates_actual_calls_from_consumed_slots() -> None:
    runner.verify_final_budget_state({
        "live_model_calls_completed": 3,
        "authorized_budget_slots_consumed": 4,
    })
    with pytest.raises(RuntimeError, match="ACTUAL_CALL_STATE"):
        runner.verify_final_budget_state({
            "live_model_calls_completed": 4,
            "authorized_budget_slots_consumed": 4,
        })
    with pytest.raises(RuntimeError, match="SLOT_STATE"):
        runner.verify_final_budget_state({
            "live_model_calls_completed": 3,
            "authorized_budget_slots_consumed": 3,
        })


def test_synthetic_request_ids_are_stable_and_do_not_contain_case_text() -> None:
    first = runner.synthetic_request_id("DR-01-Q1", "high")
    assert first == runner.synthetic_request_id("DR-01-Q1", "high")
    assert first != runner.synthetic_request_id("DR-01-Q1", "medium")
    assert first.startswith("drv2-") and len(first) == 37
    assert "DR-01" not in first


def test_medium_blind_pack_is_complete_and_mapping_is_separate(monkeypatch, tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    runs = stage / "runs"
    research = tmp_path / "research"
    runs.mkdir(parents=True)
    research.mkdir()
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps({
        "cases": [{
            "questions": [
                {"question_id": case_id, "question_text": f"question-{case_id}"}
                for case_id in blind_builder.CASE_IDS
            ]
        }]
    }), encoding="utf-8")
    (runs / "high_canary.json").write_text(json.dumps({
        "result": {"response": {"direct_reading": {"text": "fresh-high"}, "audit": {"latency_ms": 100}}}
    }), encoding="utf-8")
    (runs / "medium_batch.json").write_text(json.dumps({
        "results": [
            {"case_id": case_id, "status": "SUCCESS", "response": {"direct_reading": {"text": f"medium-{case_id}"}, "audit": {"latency_ms": 50}}}
            for case_id in blind_builder.CASE_IDS
        ]
    }), encoding="utf-8")
    (research / "remaining_run.json").write_text(json.dumps({
        "calls": [
            {"case_id": case_id, "arm": "CANDIDATE", "output_text": f"old-high-{case_id}", "latency_ms": 100}
            for case_id in blind_builder.CASE_IDS[1:]
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(blind_builder, "STAGE", stage)
    monkeypatch.setattr(blind_builder, "RUNS", runs)
    monkeypatch.setattr(blind_builder, "RESEARCH", research)
    monkeypatch.setattr(blind_builder, "CASES", cases)
    pack_path, mapping_path = blind_builder.build()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert len(pack["cases"]) == 3
    assert all("MEDIUM" not in item["answer_a"] and "HIGH" not in item["answer_b"] for item in pack["cases"])
    assert len(mapping["cases"]) == 3
    assert mapping["pack_sha256"] == _sha(pack_path)
