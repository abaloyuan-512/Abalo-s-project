"""Create the conservative Phase 2 knowledge skeleton without inventing interpretations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

KNOWLEDGE_VERSION = "MEIHUA_INTERPRETATION_KNOWLEDGE_V1"
def _split(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item.strip()]
    return [item.strip() for item in value.replace(";", "；").split("；") if item.strip()]


def build(canonical_path: Path, drafts_path: Path | None = None) -> dict[str, object]:
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    drafts_by_id: dict[str, dict[str, object]] = {}
    if drafts_path is not None:
        proposal = json.loads(drafts_path.read_text(encoding="utf-8"))
        drafts_by_id = {item["item_id"]: item for item in proposal["records"]}
    hexagrams: list[dict[str, object]] = []
    lines: list[dict[str, object]] = []
    for item in canonical["hexagrams"]:
        common = {
            "king_wen_number": item["king_wen_number"],
            "review_status": "CANONICAL_ONLY",
            "reviewer": None,
            "reviewed_at": None,
            "approved_by": None,
            "approved_at": None,
            "review_notes": None,
            "approval_notes": None,
            "knowledge_version": KNOWLEDGE_VERSION,
        }
        hexagrams.append(
            {
                **common,
                "core_theme": None,
                "situation_pattern": None,
                "favorable_conditions": [],
                "risk_conditions": [],
                "action_tendency": None,
                "prohibited_inferences": [],
                "evidence_direction": None,
                "evidence_strength": None,
            }
        )
        hex_draft = drafts_by_id.get(f"H{item['king_wen_number']:02d}")
        if hex_draft:
            fields = hex_draft["review_fields"]
            hexagrams[-1].update({
                "review_status": "DRAFT", "review_notes": "AI editorial proposal; not human-reviewed",
                "core_theme": fields["core_theme"], "situation_pattern": fields["situation_pattern"],
                "favorable_conditions": _split(fields["favorable_conditions"]),
                "risk_conditions": _split(fields["risk_conditions"]), "action_tendency": fields["action_tendency"],
                "prohibited_inferences": fields["prohibited_inferences"],
                "evidence_direction": fields["evidence_direction"], "evidence_strength": fields["evidence_strength"],
            })
        for line in item["lines"]:
            lines.append(
                {
                    **common,
                    "line_position": line["line_position"],
                    "literal_paraphrase": None,
                    "core_theme": None,
                    "favorable_conditions": [],
                    "risk_conditions": [],
                    "action_tendency": None,
                    "relationship_boundaries": [],
                    "career_boundaries": [],
                    "cooperation_boundaries": [],
                    "prohibited_inferences": [],
                    "evidence_direction": None,
                    "evidence_strength": None,
                }
            )
            line_draft = drafts_by_id.get(f"H{item['king_wen_number']:02d}-L{line['line_position']}")
            if line_draft:
                fields = line_draft["review_fields"]
                lines[-1].update({
                    "review_status": "DRAFT", "review_notes": "AI editorial proposal; not human-reviewed",
                    "literal_paraphrase": fields["literal_paraphrase"], "core_theme": fields["core_theme"],
                    "favorable_conditions": _split(fields["favorable_conditions"]),
                    "risk_conditions": _split(fields["risk_conditions"]), "action_tendency": fields["action_tendency"],
                    "relationship_boundaries": _split(fields["relationship_boundaries"]),
                    "career_boundaries": _split(fields["career_boundaries"]),
                    "cooperation_boundaries": _split(fields["cooperation_boundaries"]),
                    "prohibited_inferences": fields["prohibited_inferences"],
                    "evidence_direction": fields["evidence_direction"], "evidence_strength": fields["evidence_strength"],
                })
    return {
        "knowledge_version": KNOWLEDGE_VERSION,
        "default_access_mode": "PRODUCTION",
        "policy": "All entries start CANONICAL_ONLY. AI/Codex output is never REVIEWED or APPROVED.",
        "hexagrams": hexagrams,
        "lines": lines,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("canonical", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--drafts", type=Path)
    args = parser.parse_args()
    payload = build(args.canonical, args.drafts)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CANONICAL_ONLY_HEXAGRAMS={len(payload['hexagrams'])}")
    print(f"CANONICAL_ONLY_LINES={len(payload['lines'])}")


if __name__ == "__main__":
    main()
