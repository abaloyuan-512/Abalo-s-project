"""Offline-only replay of legacy V3 attempt-1 outputs through program-owned metadata assembly."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from abalo_iching.interpretation.enums import KnowledgeAccessMode
from abalo_iching.interpretation.evidence_references import build_evidence_reference_catalog
from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.historical_replay import (
    HISTORICAL_REPLAY_COMPAT_VERSION,
    replay_legacy_v3_output_text,
)
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
from abalo_iching.interpretation.narrative_assembly import (
    NARRATIVE_ASSEMBLY_VERSION,
    PROVIDER_SCHEMA_VERSION,
)
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.interpretation.validators import InterpretationValidator
from scripts.run_meihua_live_eval_v001 import DATASET, EVAL_VERSION, MODEL, _request, build_plan

NEW_PROMPT_VERSION = "MEIHUA_INTERPRETATION_PROMPT_V4"
REPLAY_STATUS = "REPLAY_COMPLETED_PENDING_HUMAN_REVIEW"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_hashes(source_dir: Path) -> dict[str, str]:
    files = [
        source_dir / "attempt_journal.jsonl",
        source_dir / "config_results.jsonl",
        source_dir / "summary.json",
        *sorted((source_dir / "raw_responses").glob("*")),
    ]
    return {path.relative_to(source_dir).as_posix(): sha256(path) for path in files}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay(source_dir: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError("REPLAY_OUTPUT_DIR_ALREADY_EXISTS")
    output_dir.mkdir(parents=True)
    hashes_before = original_hashes(source_dir)
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    journal = read_jsonl(source_dir / "attempt_journal.jsonl")
    rows = []
    for case, effort in build_plan(dataset):
        raw_path = source_dir / "raw_responses" / f"{case['case_id']}_{effort}_1.json"
        event = next(
            row for row in journal
            if row["case_id"] == case["case_id"]
            and row["reasoning_effort"] == effort
            and row["attempt_number"] == 1
            and row["lifecycle_status"] == "PROVIDER_RETURNED"
        )
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        request = _request(case)
        knowledge = select_knowledge(
            request.chart,
            policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
        )
        synthesis = ConclusionSynthesizer().synthesize(request.chart, knowledge)
        catalog = build_evidence_reference_catalog(request, knowledge, synthesis)
        assembled = replay_legacy_v3_output_text(raw["output_text"], request, catalog)
        errors = []
        try:
            InterpretationValidator().validate(assembled, request, knowledge, synthesis)
        except InterpretationValidationError as exc:
            errors = list(exc.errors)
        rows.append(
            {
                "case_id": case["case_id"],
                "reasoning_effort": effort,
                "model": MODEL,
                "source_attempt_number": 1,
                "source_response_id": event.get("response_id"),
                "source_raw_response_sha256": sha256(raw_path),
                "source_prompt_version": event.get("prompt_version"),
                "new_prompt_version": NEW_PROMPT_VERSION,
                "provider_schema_version": PROVIDER_SCHEMA_VERSION,
                "narrative_assembly_version": NARRATIVE_ASSEMBLY_VERSION,
                "historical_replay_compat_version": HISTORICAL_REPLAY_COMPAT_VERSION,
                "replay_validation_status": "VALIDATION_PASSED" if not errors else "VALIDATION_FAILED",
                "replay_validation_errors": errors,
                "api_calls_added": 0,
                "should_charge": False,
                "persist_as_formal_report_allowed": False,
                "assembled_ai_narrative": assembled.model_dump(mode="json"),
            }
        )
    hashes_after = original_hashes(source_dir)
    hashes_unchanged = hashes_before == hashes_after
    passed = sum(row["replay_validation_status"] == "VALIDATION_PASSED" for row in rows)
    remaining = [
        {"case_id": row["case_id"], "reasoning_effort": row["reasoning_effort"], "errors": row["replay_validation_errors"]}
        for row in rows if row["replay_validation_errors"]
    ]
    summary = {
        "status": REPLAY_STATUS if passed == 16 and hashes_unchanged else "REPLAY_FAILED",
        "dataset_version": EVAL_VERSION,
        "source_config_count": 16,
        "attempt1_replayed_count": len(rows),
        "validation_passed_count": passed,
        "validation_failed_count": len(rows) - passed,
        "remaining_errors": remaining,
        "api_calls_added": 0,
        "unintercepted_forbidden_content_count": 0 if passed == 16 else None,
        "program_fact_tamper_count": 0 if passed == 16 else None,
        "should_charge_true_count": 0,
        "formal_persistence_allowed_count": 0,
        "narrative_release_status": "UNVERIFIED",
        "original_hashes_unchanged": hashes_unchanged,
    }
    (output_dir / "replay_results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "original_file_hashes_before.json").write_text(
        json.dumps(hashes_before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "original_file_hashes_after.json").write_text(
        json.dumps(hashes_after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = replay(args.source_dir, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == REPLAY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
