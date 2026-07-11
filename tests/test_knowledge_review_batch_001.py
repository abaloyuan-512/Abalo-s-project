from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from scripts.build_meihua_review_batch import BATCH_ID, compare_sources

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "review_data/meihua/batch_001"
DOCS_DIR = ROOT / "docs/knowledge_reviews/batch_001"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


DRAFTS = _read_json(DATA_DIR / "batch_001_review_drafts.json")
SNAPSHOT = _read_json(DATA_DIR / "batch_001_source_snapshot.json")
SCHEMA = _read_json(DATA_DIR / "batch_001_review_schema.json")
EXPECTED = _read_json(ROOT / "tests/fixtures/knowledge_review_batch_001_expected.json")
CANONICAL = _read_json(ROOT / "src/abalo_iching/data/meihua/hexagram_canonical_texts_v1.json")
RECORDS = DRAFTS["records"]


def test_batch_identity_and_fixed_count():
    assert DRAFTS["batch_id"] == SNAPSHOT["batch_id"] == EXPECTED["batch_id"] == BATCH_ID
    assert len(RECORDS) == 16


def test_batch_has_eight_hexagram_records():
    assert sum(item["item_type"] == "HEXAGRAM" for item in RECORDS) == 8


def test_batch_has_eight_line_records():
    assert sum(item["item_type"] == "LINE" for item in RECORDS) == 8


def test_fixed_hexagram_selection():
    assert [item["king_wen_number"] for item in RECORDS if item["item_type"] == "HEXAGRAM"] == EXPECTED["hexagrams"]


def test_fixed_line_selection():
    actual = [
        {"king_wen_number": item["king_wen_number"], "line_position": item["line_position"]}
        for item in RECORDS
        if item["item_type"] == "LINE"
    ]
    assert actual == EXPECTED["lines"]


def test_item_ids_are_unique_and_fixed():
    item_ids = [item["item_id"] for item in RECORDS]
    assert len(item_ids) == len(set(item_ids)) == 16
    assert item_ids == EXPECTED["item_ids"]


@pytest.mark.parametrize("record", RECORDS, ids=lambda item: item["item_id"])
def test_project_text_is_extracted_from_frozen_canonical(record):
    canonical_by_number = {item["king_wen_number"]: item for item in CANONICAL["hexagrams"]}
    hexagram = canonical_by_number[record["king_wen_number"]]
    if record["item_type"] == "HEXAGRAM":
        expected_text = hexagram["canonical_judgment_text"]
    else:
        line = hexagram["lines"][record["line_position"] - 1]
        assert line["line_position"] == record["line_position"]
        assert line["line_name"] == record["line_name"]
        expected_text = line["canonical_line_text"]
    assert record["hexagram_name"] == hexagram["hexagram_name"]
    assert record["canonical_text_from_project"] == expected_text
    assert expected_text.strip()


def test_no_duplicate_hexagram_or_line_identity():
    hexagrams = [(item["king_wen_number"], item["item_type"]) for item in RECORDS if item["item_type"] == "HEXAGRAM"]
    lines = [(item["king_wen_number"], item["line_position"]) for item in RECORDS if item["item_type"] == "LINE"]
    assert len(hexagrams) == len(set(hexagrams)) == 8
    assert len(lines) == len(set(lines)) == 8


@pytest.mark.parametrize("record", RECORDS, ids=lambda item: item["item_id"])
def test_public_source_texts_and_metadata_are_present(record):
    comparison = record["source_comparison"]
    assert comparison["ctext_text"]
    assert comparison["wikisource_text"]
    assert comparison["ctext_url"].startswith("https://ctext.org/book-of-changes/")
    assert comparison["wikisource_url"].startswith("https://zh.wikisource.org/")
    assert comparison["source_accessed_at"] == "2026-07-11"
    assert comparison["human_review_required"] is True


def test_missing_source_is_never_fabricated_or_auto_cleared():
    comparison = compare_sources("元亨。", None, "元亨。")
    assert comparison["ctext_text"] is None
    assert comparison["human_review_required"] is True
    assert comparison["substantive_variant_detected"] is True


def test_punctuation_difference_does_not_auto_approve():
    comparison = compare_sources("元亨利貞。", "元亨，利貞。", "元亨。利貞。")
    assert comparison["punctuation_only_difference"] is True
    assert comparison["substantive_variant_detected"] is False
    assert comparison["human_review_required"] is True


def test_substantive_variant_routes_to_source_review():
    item = next(record for record in RECORDS if record["item_id"] == "H12")
    assert item["source_comparison"]["substantive_variant_detected"] is False
    assert item["workbench_status"] == "READY_FOR_CONTENT_REVIEW"
    assert "否之匪人" in item["canonical_text_from_project"]


@pytest.mark.parametrize("record", RECORDS, ids=lambda item: item["item_id"])
def test_all_editorial_draft_fields_are_populated_without_signoff(record):
    assert record["review_fields"]["core_theme"]
    assert record["review_fields"]["favorable_conditions"]
    assert record["review_fields"]["risk_conditions"]
    assert record["human_signoff"] is None


def test_workbench_reflects_draft_without_knowledge_evidence():
    assert all(item["current_knowledge_status"] == "DRAFT" for item in RECORDS)
    assert all(item["workbench_status"] == "READY_FOR_CONTENT_REVIEW" for item in RECORDS)
    assert all(item["knowledge_evidence"] == [] for item in RECORDS)


@pytest.mark.parametrize("record", RECORDS, ids=lambda item: item["item_id"])
def test_all_markdown_review_cards_exist(record):
    assert (DOCS_DIR / record["review_card_path"]).is_file()


@pytest.mark.parametrize("record", RECORDS, ids=lambda item: item["item_id"])
def test_markdown_card_identity_matches_json(record):
    text = (DOCS_DIR / record["review_card_path"]).read_text(encoding="utf-8")
    assert record["batch_id"] in text
    assert record["item_id"] in text
    assert record["hexagram_name"] in text
    assert record["canonical_text_from_project"] in text
    assert "READY_FOR_CONTENT_REVIEW" in text


def test_schema_validates_pending_workbench_records():
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    assert list(validator.iter_errors(DRAFTS)) == []


def test_schema_rejects_direct_approved_status():
    invalid = copy.deepcopy(DRAFTS)
    invalid["records"][0]["workbench_status"] = "APPROVED"
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    assert list(validator.iter_errors(invalid))


def test_schema_rejects_empty_shell_human_review_complete():
    invalid = copy.deepcopy(DRAFTS)
    invalid["records"][0]["workbench_status"] = "HUMAN_REVIEW_COMPLETE"
    invalid["records"][0]["human_signoff"] = {
        "person": "人工审核人",
        "completed_at": "2026-07-11T12:00:00+08:00",
        "decision": "CONTENT_REVIEW_COMPLETE_NOT_APPROVED",
    }
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    assert list(validator.iter_errors(invalid))
