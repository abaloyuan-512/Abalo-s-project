"""Validate Batch 001 AI proposal and create auditable DRAFT writeback artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_interpretation_knowledge import build as build_knowledge

ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "MEIHUA-KNOWLEDGE-BATCH-001"
PROPOSAL_TYPE = "AI_EDITORIAL_PROPOSAL_NOT_HUMAN_SIGNOFF"
DATA_DIR = ROOT / "review_data/meihua/batch_001"
DOCS_DIR = ROOT / "docs/knowledge_reviews/batch_001"
CANONICAL = ROOT / "src/abalo_iching/data/meihua/hexagram_canonical_texts_v1.json"
KNOWLEDGE = ROOT / "src/abalo_iching/data/meihua/interpretation_knowledge_v1.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_proposal(path: Path) -> None:
    proposal = _read(path)
    records = proposal.get("records", [])
    if proposal.get("batch_id") != BATCH_ID or proposal.get("proposal_type") != PROPOSAL_TYPE:
        raise ValueError("Proposal identity mismatch")
    if len(records) != 16 or sum(r["item_type"] == "HEXAGRAM" for r in records) != 8:
        raise ValueError("Proposal must contain exactly 8 hexagram and 8 line records")
    if any(r.get("formal_target_status") != "DRAFT" or r.get("human_signoff") is not None for r in records):
        raise ValueError("Proposal may only target unsigned DRAFT records")

    canonical = _read(CANONICAL)
    h12 = canonical["hexagrams"][11]
    h12["canonical_judgment_text"] = "否之匪人，不利君子貞，大往小來。"
    corrections = _read(ROOT / "docs/specs/meihua_canonical_corrections_v1.json")
    canonical["correction_version"] = corrections["correction_version"]
    canonical["applied_corrections"] = corrections["corrections"]
    _write(CANONICAL, canonical)

    derived_records = []
    proposal_by_id = {r["item_id"]: r for r in records}
    drafts = _read(DATA_DIR / "batch_001_review_drafts.json")
    snapshot = _read(DATA_DIR / "batch_001_source_snapshot.json")
    canonical_by_number = {h["king_wen_number"]: h for h in canonical["hexagrams"]}
    for record in drafts["records"]:
        source = proposal_by_id[record["item_id"]]
        fields = source["proposal_review_fields"]
        record["review_fields"] = {key: fields.get(key) for key in record["review_fields"]}
        record["workbench_status"] = "READY_FOR_CONTENT_REVIEW"
        record["current_knowledge_status"] = "DRAFT"
        record["human_signoff"] = None
        if record["item_id"] == "H12":
            text = canonical_by_number[12]["canonical_judgment_text"]
            record["canonical_text_from_project"] = text
            record["canonical_source_hash"] = hashlib.sha256(text.encode()).hexdigest()
            record["source_comparison"]["project_text"] = text
            record["source_comparison"]["substantive_variant_detected"] = False
            record["source_comparison"]["variant_notes"] = (
                "已按 MEIHUA_CANONICAL_CORRECTIONS_V1 补回‘否之匪人’；仍需人工复核来源版本。"
            )
        derived_records.append({
            "item_id": record["item_id"], "item_type": record["item_type"],
            "king_wen_number": record["king_wen_number"], "line_position": record["line_position"],
            "review_fields": record["review_fields"], "formal_target_status": "DRAFT",
            "review_notes": "AI editorial proposal; not human-reviewed",
        })
    drafts["workbench_type"] = "AI_EDITORIAL_DRAFT_PENDING_HUMAN_REVIEW"
    _write(DATA_DIR / "batch_001_review_drafts.json", drafts)
    snapshot["records"] = drafts["records"]
    snapshot["canonical_data_sha256"] = _sha(CANONICAL)
    _write(DATA_DIR / "batch_001_source_snapshot.json", snapshot)
    _write(DATA_DIR / "batch_001_editorial_drafts.json", {
        "batch_id": BATCH_ID, "proposal_type": PROPOSAL_TYPE,
        "source_proposal_sha256": _sha(path), "records": derived_records,
    })
    _write(KNOWLEDGE, build_knowledge(CANONICAL, DATA_DIR / "batch_001_editorial_drafts.json"))
    formal_hash = _sha(KNOWLEDGE)
    snapshot["formal_knowledge_sha256"] = formal_hash
    _write(DATA_DIR / "batch_001_source_snapshot.json", snapshot)
    fixture_path = ROOT / "tests/fixtures/knowledge_review_batch_001_expected.json"
    fixture = _read(fixture_path)
    fixture["formal_knowledge_sha256"] = formal_hash
    _write(fixture_path, fixture)
    manifest_path = DOCS_DIR / "BATCH_MANIFEST.json"
    manifest = _read(manifest_path)
    manifest["formal_knowledge_sha256"] = formal_hash
    manifest["canonical_data_sha256"] = _sha(CANONICAL)
    manifest["formal_status_counts"] = {"CANONICAL_ONLY": 432, "DRAFT": 16, "REVIEWED": 0, "APPROVED": 0}
    for name in ("H12_CANONICAL_CORRECTION_AUDIT.md",):
        if name not in manifest["generated_outputs"]:
            manifest["generated_outputs"].append(name)
    _write(manifest_path, manifest)

    schema = _read(DATA_DIR / "batch_001_review_schema.json")
    schema["properties"]["workbench_type"] = {"const": "AI_EDITORIAL_DRAFT_PENDING_HUMAN_REVIEW"}
    record_schema = schema["$defs"]["reviewRecord"]["properties"]
    record_schema["current_knowledge_status"] = {"const": "DRAFT"}
    record_schema["workbench_status"] = {"const": "READY_FOR_CONTENT_REVIEW"}
    _write(DATA_DIR / "batch_001_review_schema.json", schema)

    for record in drafts["records"]:
        fields = record["review_fields"]
        lines = [f"# {record['item_id']}｜{record['hexagram_name']}审核卡", "", "> AI 编辑提案草稿；未经人工审核或批准。", "",
                 f"- Batch ID：`{BATCH_ID}`", f"- Item ID：`{record['item_id']}`",
                 f"- 知识状态：`DRAFT`", f"- 工作台状态：`READY_FOR_CONTENT_REVIEW`",
                 f"- 人工签名：`null`", "", "## Canonical 原文", "", f"> {record['canonical_text_from_project']}",
                 "", "## DRAFT 现代解释", ""]
        for key, value in fields.items():
            shown = "；".join(value) if isinstance(value, list) else (value or "")
            lines.extend([f"### {key}", "", str(shown), ""])
        lines.extend(["## 来源复核说明", "", record["source_comparison"]["variant_notes"], "",
                      "本卡不构成人工签核，不允许标记为 REVIEWED 或 APPROVED。", ""])
        (DOCS_DIR / record["review_card_path"]).write_text("\n".join(lines), encoding="utf-8")

    (DOCS_DIR / "H12_CANONICAL_CORRECTION_AUDIT.md").write_text(
        "# H12 canonical 原文修正审计\n\n"
        "- 修正规则：`MEIHUA_CANONICAL_CORRECTIONS_V1`\n"
        "- 修正后卦辞：`否之匪人，不利君子貞，大往小來。`\n"
        "- CText：https://ctext.org/book-of-changes/pi\n"
        "- Wikisource：https://zh.wikisource.org/zh-hant/%E5%91%A8%E6%98%93/%E5%90%A6\n"
        "- 结论：缺失短语已补回；来源版本仍需人工复核；现代解释仍是未签名 DRAFT。\n",
        encoding="utf-8",
    )
    print(f"PROPOSAL_SHA256={_sha(path)}")
    print("DRAFT_RECORDS=16")
    print("H12_CANONICAL_CORRECTION=PASS")
    print(f"FORMAL_KNOWLEDGE_SHA256={formal_hash}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposal", type=Path)
    args = parser.parse_args()
    import_proposal(args.proposal)


if __name__ == "__main__":
    main()
