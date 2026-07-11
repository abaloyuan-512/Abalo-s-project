"""Build a frozen primary transcription pending full human recension review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CANONICAL_VERSION = "MEIHUA_CANONICAL_TEXTS_V1"
SOURCE_NAME = "王弼《周易注》底本公开镜像（冻结主文本，待逐条人工版本核对）"
SOURCE_REFERENCE = (
    "https://gist.githubusercontent.com/sui1491/52e8214c8e5f4a189b94f5ea2b8bdb05/raw/"
    "d628f824a90d7b41b5149199e0fa0767e030b3af/%E6%98%93%E7%BB%8F%E5%85%A8%E6%96%87"
)
SOURCE_ACCESSED_AT = "2026-07-11"
CTEXT_REFERENCE = "https://ctext.org/book-of-changes/yi-jing/zh"
WIKISOURCE_REFERENCE = "https://zh.wikisource.org/zh-hans/%E6%98%93%E7%B6%93"

_HEXAGRAM_RE = re.compile(r"^(?P<number>[1-9]|[1-5][0-9]|6[0-4])\.?\s*(?P<name>[^，,。\s]+)[，,](?P<text>.+)$")
_LINE_RE = re.compile(r"^(?P<label>初[六九]|[六九][二三四五]|上[六九])[，,](?P<text>.+)$")
_LINE_NAME = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}


def _normalize(text: str) -> str:
    return text.strip().replace("無", "无")


def build(source: Path, phase1_hexagrams: Path, corrections_path: Path | None = None) -> dict[str, object]:
    source_bytes = source.read_bytes()
    source_text = source_bytes.decode("utf-8-sig")
    phase1 = json.loads(phase1_hexagrams.read_text(encoding="utf-8"))["hexagrams"]
    names = {item["king_wen_number"]: item["name_zh"] for item in phase1}

    records: dict[int, dict[str, object]] = {}
    current: dict[str, object] | None = None
    for raw_line in source_text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^8\.\s+比吉。", "8. 比，吉。", line)
        match = _HEXAGRAM_RE.match(line)
        if match:
            number = int(match.group("number"))
            if number not in records:
                current = {
                    "king_wen_number": number,
                    "hexagram_name": names[number],
                    "canonical_judgment_text": _normalize(match.group("text")),
                    "source_name": SOURCE_NAME,
                    "source_reference": SOURCE_REFERENCE,
                    "source_accessed_at": SOURCE_ACCESSED_AT,
                    "canonical_data_version": CANONICAL_VERSION,
                    "lines": [],
                }
                records[number] = current
                continue
        if current is None or len(current["lines"]) >= 6:
            continue
        line_match = _LINE_RE.match(line)
        if not line_match:
            continue
        position = len(current["lines"]) + 1
        current["lines"].append(
            {
                "king_wen_number": current["king_wen_number"],
                "hexagram_name": current["hexagram_name"],
                "line_position": position,
                "line_name": _LINE_NAME[position],
                "canonical_line_text": _normalize(line_match.group("text")),
                "source_name": SOURCE_NAME,
                "source_reference": SOURCE_REFERENCE,
                "canonical_data_version": CANONICAL_VERSION,
            }
        )

    missing = [number for number in range(1, 65) if number not in records]
    malformed = [number for number, item in records.items() if len(item["lines"]) != 6]
    if missing or malformed:
        raise ValueError(f"Canonical extraction incomplete: missing={missing}, malformed={malformed}")
    corrections: list[dict[str, object]] = []
    if corrections_path is not None:
        correction_payload = json.loads(corrections_path.read_text(encoding="utf-8"))
        corrections = correction_payload["corrections"]
        for correction in corrections:
            number = int(correction["king_wen_number"])
            field = str(correction["field"])
            if field != "canonical_judgment_text":
                raise ValueError(f"Unsupported canonical correction field: {field}")
            records[number][field] = correction["replacement"]
    return {
        "canonical_data_version": CANONICAL_VERSION,
        "text_scope": "Received Zhouyi judgment and six line statements only; excludes Tuan, Xiang, Wenyan and Qian/Kun use statements.",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "primary_source": SOURCE_REFERENCE,
        "cross_check_sources": [CTEXT_REFERENCE, WIKISOURCE_REFERENCE],
        "cross_check_status": "PENDING_HUMAN_LINE_BY_LINE_REVIEW",
        "normalization_rules": [
            "trim whitespace",
            "無 → 无",
            "punctuation normalization",
            "special source formatting repair for hexagram 8",
        ],
        "variant_policy": "Frozen primary transcription pending full human recension comparison; source URLs are review targets, not proof of completed line-by-line comparison.",
        "correction_version": correction_payload["correction_version"] if corrections_path is not None else None,
        "applied_corrections": corrections,
        "hexagrams": [records[number] for number in range(1, 65)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("phase1_hexagrams", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--corrections", type=Path)
    args = parser.parse_args()
    payload = build(args.source, args.phase1_hexagrams, args.corrections)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CANONICAL_HEXAGRAMS={len(payload['hexagrams'])}")
    print(f"CANONICAL_LINES={sum(len(item['lines']) for item in payload['hexagrams'])}")


if __name__ == "__main__":
    main()
