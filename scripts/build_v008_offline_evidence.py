from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingChartFacts,
    PROMPT_VERSION,
    validate_direct_reading_text,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "outputs" / "v007_s1_01_real_result.json"
OUTPUT = ROOT / "evals" / "meihua" / "direct_reading_v2_stability_v008" / "offline_gate_evidence.json"


def _load_corpus() -> tuple[list, list, str]:
    path = ROOT / "tests" / "test_v008_reality_lineage_gate.py"
    spec = importlib.util.spec_from_file_location("v008_reality_lineage_corpus", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("V008_CORPUS_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.POSITIVE_CASES, module.NEGATIVE_CASES, module.PREFIX


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def main() -> int:
    positive_cases, negative_cases, prefix = _load_corpus()
    source = json.loads(RESULT.read_text(encoding="utf-8"))
    reading = source["direct_reading"]["text"]
    facts = DirectReadingChartFacts.model_validate(source["chart_facts"])
    rows: list[dict[str, object]] = []
    for case_id, question, excerpt, optional_context in positive_cases:
        text = f"{reading}\n\n{prefix}{excerpt}"
        errors = validate_direct_reading_text(
            text,
            question_text=question,
            facts=facts,
            optional_context=optional_context,
        )
        rows.append(
            {
                "case_id": f"V008-P-{case_id}",
                "corpus": "release",
                "source_span_sha256": sha256(excerpt.strip()),
                "expected_code": None,
                "actual_codes": list(errors),
                "actual_disposition": "release" if not errors else "block",
                "mutation": False,
            }
        )
    for case_id, question, added, expected_code in negative_cases:
        text = f"{reading}\n\n{added}"
        errors = validate_direct_reading_text(
            text,
            question_text=question,
            facts=facts,
        )
        rows.append(
            {
                "case_id": f"V008-N-{case_id}",
                "corpus": "block",
                "source_span_sha256": None,
                "expected_code": expected_code,
                "actual_codes": list(errors),
                "actual_disposition": "block" if expected_code in errors else "release",
                "mutation": False,
            }
        )
    counts = {
        "release_cases": sum(row["corpus"] == "release" for row in rows),
        "block_cases": sum(row["corpus"] == "block" for row in rows),
        "false_positive": sum(
            row["corpus"] == "release" and row["actual_disposition"] != "release"
            for row in rows
        ),
        "false_negative": sum(
            row["corpus"] == "block" and row["actual_disposition"] != "block"
            for row in rows
        ),
        "mutation": sum(bool(row["mutation"]) for row in rows),
    }
    document = {
        "stage_id": "DIRECT_READING_V2_REALITY_LINEAGE_V008",
        "evidence_level": "OFFLINE_L1_PRODUCTION_VALIDATOR_PATH",
        "prompt_version": PROMPT_VERSION,
        "provider_instantiated": False,
        "model_calls": 0,
        "automatic_retries": 0,
        "counts": counts,
        "cases": rows,
    }
    if counts != {
        "release_cases": 10,
        "block_cases": 21,
        "false_positive": 0,
        "false_negative": 0,
        "mutation": 0,
    }:
        raise RuntimeError(f"V008_OFFLINE_GATE_FAILED:{counts}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

