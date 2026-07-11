"""Create the conservative Phase 2 knowledge skeleton without inventing interpretations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

KNOWLEDGE_VERSION = "MEIHUA_INTERPRETATION_KNOWLEDGE_V1"
def build(canonical_path: Path) -> dict[str, object]:
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
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
    args = parser.parse_args()
    payload = build(args.canonical)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CANONICAL_ONLY_HEXAGRAMS={len(payload['hexagrams'])}")
    print(f"CANONICAL_ONLY_LINES={len(payload['lines'])}")


if __name__ == "__main__":
    main()
