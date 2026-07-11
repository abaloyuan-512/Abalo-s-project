from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from abalo_iching.interpretation.knowledge import load_interpretation_knowledge
from abalo_iching.interpretation.release import narrative_release_snapshot
from scripts.validate_meihua_review_batch import (
    KnowledgeImportNotEnabledError,
    REQUIRED_COMPLETED_FIELDS,
    attempt_formal_import,
    validate_batch,
    validate_review_record_for_future_import,
)

ROOT = Path(__file__).resolve().parents[1]
FORMAL_PATH = ROOT / "src/abalo_iching/data/meihua/interpretation_knowledge_v1.json"
EXPECTED = json.loads((ROOT / "tests/fixtures/knowledge_review_batch_001_expected.json").read_text(encoding="utf-8"))
DRAFTS = json.loads((ROOT / "review_data/meihua/batch_001/batch_001_review_drafts.json").read_text(encoding="utf-8"))


def test_formal_knowledge_hash_is_frozen():
    assert hashlib.sha256(FORMAL_PATH.read_bytes()).hexdigest() == EXPECTED["formal_knowledge_sha256"]


def test_formal_records_contain_only_unsigned_drafts_and_canonical_entries():
    hexagrams, lines = load_interpretation_knowledge()
    records = tuple(hexagrams.values()) + tuple(lines.values())
    assert len(records) == 448
    assert sum(item.review_status.value == "CANONICAL_ONLY" for item in records) == 432
    assert sum(item.review_status.value == "DRAFT" for item in records) == 16
    assert sum(item.review_status.value == "REVIEWED" for item in records) == 0
    assert sum(item.review_status.value == "APPROVED" for item in records) == 0


def test_no_formal_reviewer_or_approver_was_added():
    hexagrams, lines = load_interpretation_knowledge()
    records = tuple(hexagrams.values()) + tuple(lines.values())
    assert all(item.reviewer is None and item.reviewed_at is None for item in records)
    assert all(item.approved_by is None and item.approved_at is None for item in records)


def test_release_gate_remains_unverified():
    assert narrative_release_snapshot().narrative_release_status.value == "UNVERIFIED"


def test_generated_batch_passes_read_only_validation():
    result = validate_batch()
    assert result["records"] == 16
    assert result["formal_knowledge_sha256"] == EXPECTED["formal_knowledge_sha256"]


def test_pending_record_is_not_ready_for_import():
    assert validate_review_record_for_future_import(DRAFTS["records"][0]) == "READY_FOR_HUMAN_DECISION"


def test_completed_fields_only_route_to_human_decision():
    record = copy.deepcopy(DRAFTS["records"][0])
    record["workbench_status"] = "READY_FOR_CONTENT_REVIEW"
    for field in REQUIRED_COMPLETED_FIELDS:
        record["review_fields"][field] = "人工待审核内容"
    assert validate_review_record_for_future_import(record) == "READY_FOR_HUMAN_DECISION"


def test_human_complete_is_still_not_approved():
    record = copy.deepcopy(DRAFTS["records"][0])
    record["workbench_status"] = "HUMAN_REVIEW_COMPLETE"
    for field in REQUIRED_COMPLETED_FIELDS:
        record["review_fields"][field] = "人工已审核内容"
    record["human_signoff"] = {
        "person": "人工审核人",
        "completed_at": "2026-07-11T12:00:00+08:00",
        "decision": "CONTENT_REVIEW_COMPLETE_NOT_APPROVED",
    }
    assert validate_review_record_for_future_import(record) == "HUMAN_REVIEW_COMPLETE_BUT_NOT_APPROVED"


@pytest.mark.parametrize("dry_run", [True, False])
def test_formal_import_is_disabled_in_every_mode(dry_run):
    with pytest.raises(KnowledgeImportNotEnabledError):
        attempt_formal_import(dry_run=dry_run)


@pytest.mark.parametrize("entrypoint", ["streamlit_app.py", "iching_tools.py"])
def test_legacy_entrypoints_match_branch_head(entrypoint):
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", entrypoint],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
