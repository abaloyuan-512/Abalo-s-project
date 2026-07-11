"""Read-only validation for the Phase 2B Batch 001 review workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "review_data/meihua/batch_001"
DOCS_DIR = ROOT / "docs/knowledge_reviews/batch_001"
FORMAL_KNOWLEDGE_PATH = ROOT / "src/abalo_iching/data/meihua/interpretation_knowledge_v1.json"
BATCH_ID = "MEIHUA-KNOWLEDGE-BATCH-001"

FutureImportReadiness = Literal[
    "NOT_READY",
    "READY_FOR_HUMAN_DECISION",
    "HUMAN_REVIEW_COMPLETE_BUT_NOT_APPROVED",
]

REQUIRED_COMPLETED_FIELDS = (
    "judgment_paraphrase",
    "core_theme",
    "situation_pattern",
    "favorable_conditions",
    "risk_conditions",
    "action_tendency",
    "relationship_boundaries",
    "career_boundaries",
    "cooperation_boundaries",
    "evidence_direction",
    "evidence_strength",
    "review_decision",
)


class KnowledgeImportNotEnabledError(RuntimeError):
    """Raised whenever any caller attempts to import workbench data."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_review_record_for_future_import(record: dict[str, Any]) -> FutureImportReadiness:
    """Classify readiness without approving, importing, promoting, or writing anything."""

    status = record.get("workbench_status")
    fields = record.get("review_fields") or {}
    completed = all(isinstance(fields.get(name), str) and fields[name].strip() for name in REQUIRED_COMPLETED_FIELDS)
    if status == "HUMAN_REVIEW_COMPLETE" and completed and record.get("human_signoff"):
        return "HUMAN_REVIEW_COMPLETE_BUT_NOT_APPROVED"
    if status == "READY_FOR_CONTENT_REVIEW" and completed:
        return "READY_FOR_HUMAN_DECISION"
    return "NOT_READY"


def attempt_formal_import(*, dry_run: bool = True) -> None:
    """A permanently disabled import boundary; dry-run is the only exposed default."""

    mode = "dry-run" if dry_run else "write"
    raise KnowledgeImportNotEnabledError(
        f"Formal knowledge import is not enabled for Phase 2B Batch 001 ({mode}); "
        "a separate second-stage human signature is required."
    )


def validate_batch() -> dict[str, int | str]:
    drafts = _read_json(DATA_DIR / "batch_001_review_drafts.json")
    schema = _read_json(DATA_DIR / "batch_001_review_schema.json")
    snapshot = _read_json(DATA_DIR / "batch_001_source_snapshot.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(drafts), key=lambda item: list(item.absolute_path))
    if errors:
        messages = [f"{list(error.absolute_path)}: {error.message}" for error in errors]
        raise ValueError("Schema validation failed:\n" + "\n".join(messages))

    records = drafts["records"]
    if drafts["batch_id"] != BATCH_ID or snapshot["batch_id"] != BATCH_ID:
        raise ValueError("Batch ID mismatch")
    if len(records) != 16 or len(snapshot["records"]) != 16:
        raise ValueError("Batch must contain exactly 16 records")
    if sum(item["item_type"] == "HEXAGRAM" for item in records) != 8:
        raise ValueError("Batch must contain exactly 8 hexagram records")
    if sum(item["item_type"] == "LINE" for item in records) != 8:
        raise ValueError("Batch must contain exactly 8 line records")
    if len({item["item_id"] for item in records}) != 16:
        raise ValueError("Duplicate item_id")
    if any(item["current_knowledge_status"] != "DRAFT" for item in records):
        raise ValueError("Workbench records must reflect formal DRAFT status")
    if any(item["workbench_status"] != "READY_FOR_CONTENT_REVIEW" for item in records):
        raise ValueError("Editorial workbench status is invalid")
    if any(item["knowledge_evidence"] for item in records):
        raise ValueError("KnowledgeEvidence is prohibited in the review workbench")
    if any(item["human_signoff"] is not None for item in records):
        raise ValueError("Initial records must not contain human signoff")
    for item in records:
        required = ("core_theme", "favorable_conditions", "risk_conditions", "action_tendency")
        if any(not item["review_fields"].get(field) for field in required):
            raise ValueError(f"Editorial DRAFT fields incomplete: {item['item_id']}")
        comparison = item["source_comparison"]
        if (comparison["ctext_text"] is None or comparison["wikisource_text"] is None) and not comparison["human_review_required"]:
            raise ValueError("Missing source must require human review")
        card = DOCS_DIR / item["review_card_path"]
        if not card.is_file():
            raise ValueError(f"Missing review card: {card}")
        card_text = card.read_text(encoding="utf-8")
        for identity in (item["batch_id"], item["item_id"], item["hexagram_name"], item["canonical_text_from_project"]):
            if str(identity) not in card_text:
                raise ValueError(f"Review card identity mismatch: {item['item_id']}")

    formal_hash = _sha256(FORMAL_KNOWLEDGE_PATH)
    if snapshot["formal_knowledge_sha256"] != formal_hash:
        raise ValueError("Snapshot formal knowledge hash mismatch")

    return {
        "records": len(records),
        "hexagrams": sum(item["item_type"] == "HEXAGRAM" for item in records),
        "lines": sum(item["item_type"] == "LINE" for item in records),
        "ctext_success": sum(item["source_comparison"]["ctext_text"] is not None for item in records),
        "wikisource_success": sum(item["source_comparison"]["wikisource_text"] is not None for item in records),
        "punctuation_differences": sum(item["source_comparison"]["punctuation_only_difference"] for item in records),
        "normalization_differences": sum(item["source_comparison"]["simplified_traditional_difference"] for item in records),
        "substantive_variants": sum(item["source_comparison"]["substantive_variant_detected"] for item in records),
        "human_review_required": sum(item["source_comparison"]["human_review_required"] for item in records),
        "formal_knowledge_sha256": formal_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--attempt-import", action="store_true")
    args = parser.parse_args()
    summary = validate_batch()
    if args.attempt_import:
        attempt_formal_import(dry_run=args.dry_run)
    for key, value in summary.items():
        print(f"{key.upper()}={value}")
    print("FORMAL_IMPORT_ENABLED=false")
    print("BATCH_VALIDATION=PASS")


if __name__ == "__main__":
    main()
