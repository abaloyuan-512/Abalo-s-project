from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_reading_v2_implementation_v002"
RUNS = STAGE / "runs"
RESEARCH = ROOT / "evals/meihua/direct_reading_v2_research_v0011/runs"
CASES = ROOT / "evals/meihua/direct_reading_v2_research_v001/cases/cases.json"
CASE_IDS = ("DR-01-Q1", "DR-03-Q2", "DR-04-Q2")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _questions() -> dict[str, str]:
    result: dict[str, str] = {}
    for chart in _read(CASES)["cases"]:
        for question in chart["questions"]:
            result[question["question_id"]] = question["question_text"]
    return result


def build() -> tuple[Path, Path]:
    high_run = _read(RUNS / "high_canary.json")
    medium_run = _read(RUNS / "medium_batch.json")
    research = _read(RESEARCH / "remaining_run.json")
    medium = {item["case_id"]: item for item in medium_run["results"]}
    research_high = {
        item["case_id"]: item
        for item in research["calls"]
        if item.get("arm") == "CANDIDATE" and item.get("case_id") in CASE_IDS
    }
    high = {
        "DR-01-Q1": {
            "text": high_run["result"]["response"]["direct_reading"]["text"],
            "latency_ms": high_run["result"]["response"]["audit"]["latency_ms"],
        },
        "DR-03-Q2": {
            "text": research_high["DR-03-Q2"]["output_text"],
            "latency_ms": research_high["DR-03-Q2"]["latency_ms"],
        },
        "DR-04-Q2": {
            "text": research_high["DR-04-Q2"]["output_text"],
            "latency_ms": research_high["DR-04-Q2"]["latency_ms"],
        },
    }
    questions = _questions()
    private_seed = secrets.token_bytes(32)
    pack: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    for case_id in CASE_IDS:
        medium_item = medium[case_id]
        if medium_item["status"] != "SUCCESS":
            raise RuntimeError(f"MEDIUM_NOT_SUCCESS:{case_id}")
        medium_text = medium_item["response"]["direct_reading"]["text"]
        medium_latency = medium_item["response"]["audit"]["latency_ms"]
        swap = int.from_bytes(
            hashlib.sha256(private_seed + case_id.encode("utf-8")).digest(),
            "big",
        ) % 2 == 1
        answers = [medium_text, high[case_id]["text"]]
        labels = ["MEDIUM", "HIGH"]
        if swap:
            answers.reverse()
            labels.reverse()
        pack.append({
            "case_id": case_id,
            "question": questions[case_id],
            "answer_a": answers[0],
            "answer_b": answers[1],
        })
        mapping.append({
            "case_id": case_id,
            "a": labels[0],
            "b": labels[1],
            "high_latency_ms": high[case_id]["latency_ms"],
            "medium_latency_ms": medium_latency,
        })
    pack_path = STAGE / "blind/medium_blind_pack.json"
    mapping_path = STAGE / "private/medium_blind_mapping.json"
    _atomic(pack_path, {"cases": pack})
    _atomic(mapping_path, {
        "private_seed_hex": private_seed.hex(),
        "pack_sha256": hashlib.sha256(pack_path.read_bytes()).hexdigest().upper(),
        "cases": mapping,
    })
    return pack_path, mapping_path


if __name__ == "__main__":
    build()
