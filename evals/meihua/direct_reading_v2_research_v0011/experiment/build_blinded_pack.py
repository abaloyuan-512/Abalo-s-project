"""Build the deterministic blinded comparison pack from frozen run evidence."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from evals.meihua.direct_reading_v2_research_v001.experiment.run_direct_reading_research import (
    _expand_questions,
    _render_chart,
)


SEED = 20260810


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def build(repo_root: Path) -> tuple[Path, Path]:
    source = repo_root / "evals/meihua/direct_reading_v2_research_v001"
    revision = repo_root / "evals/meihua/direct_reading_v2_research_v0011"
    cases = _expand_questions(_load(source / "cases/cases.json")["cases"])
    source_canary = _load(source / "runs/canary_run.json")
    revised_canary = _load(revision / "runs/candidate_canary_run.json")
    remaining = _load(revision / "runs/remaining_run.json")
    all_calls = source_canary["calls"] + revised_canary["calls"] + remaining["calls"]
    by_key = {(call["case_id"], call["arm"]): call for call in all_calls if call.get("product_complete", True)}
    if len(by_key) != 18:
        raise RuntimeError("blinded pack requires exactly 18 complete case-arm outputs")

    candidate_a_cases = {case["case_id"] for case in random.Random(SEED).sample(cases, 4)}
    pack_cases: list[dict[str, Any]] = []
    mappings: list[dict[str, str]] = []
    for case in cases:
        case_id = case["case_id"]
        candidate_label = "A" if case_id in candidate_a_cases else "B"
        reference_label = "B" if candidate_label == "A" else "A"
        outputs = {
            candidate_label: by_key[(case_id, "CANDIDATE")]["output_text"],
            reference_label: by_key[(case_id, "REFERENCE")]["output_text"],
        }
        pack_cases.append(
            {
                "case_id": case_id,
                "pair_id": case.get("pair_id"),
                "question": case["question_text"],
                "chart_packet": _render_chart(case),
                "answer_a": outputs["A"],
                "answer_b": outputs["B"],
            }
        )
        mappings.append(
            {
                "case_id": case_id,
                "answer_a_arm": "CANDIDATE" if candidate_label == "A" else "REFERENCE",
                "answer_b_arm": "REFERENCE" if candidate_label == "A" else "CANDIDATE",
            }
        )

    pack_path = revision / "evaluation/blinded_pack.json"
    mapping_path = revision / "evaluation/private_mapping.json"
    _write(
        pack_path,
        {
            "evaluation_id": "GUANXIANG_DIRECT_READING_V2_BLIND_0011",
            "case_count": 9,
            "instructions": "Judge A and B without inferring model identity. Use the frozen rubric.",
            "cases": pack_cases,
        },
    )
    _write(
        mapping_path,
        {
            "evaluation_id": "GUANXIANG_DIRECT_READING_V2_BLIND_0011",
            "seed": SEED,
            "warning": "Do not open before blinded scoring is frozen.",
            "pack_sha256": _sha_file(pack_path),
            "mappings": mappings,
        },
    )
    return pack_path, mapping_path


if __name__ == "__main__":
    for result in build(Path.cwd().resolve()):
        print(result)
