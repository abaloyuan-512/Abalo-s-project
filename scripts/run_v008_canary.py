from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_direct_reading_v2 import (
    OpenAIDirectReadingProvider,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "outputs" / "v008_canary_freeze.json"
LEDGER_PATH = ROOT / "outputs" / "v008_canary_call_ledger.json"
MANIFEST_PATH = ROOT / "evals" / "meihua" / "direct_reading_v2_stability_v008" / "candidate_manifest.json"
RESULT_PATH = ROOT / "outputs" / "v008_canary_real_result.json"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def main() -> int:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    manifest_sha = _file_sha(MANIFEST_PATH)
    if _file_sha(FREEZE_PATH) != ledger["freeze_sha256"]:
        raise RuntimeError("V008_FREEZE_HASH_MISMATCH")
    if manifest_sha != ledger.get("candidate_manifest_sha256"):
        raise RuntimeError("V008_CANDIDATE_MANIFEST_MISMATCH")
    if ledger.get("activation_condition_met") is not True:
        raise RuntimeError("V008_OFFLINE_ACCEPTANCE_NOT_ACTIVATED")
    if (
        ledger["authorized_high_attempts"] != 1
        or ledger["actual_high_attempts"] != 0
        or ledger["remaining_high_attempts"] != 1
        or ledger["automatic_retries"] != 0
        or ledger["cases"]
    ):
        raise RuntimeError("V008_LEDGER_NOT_PRISTINE")
    if RESULT_PATH.exists():
        raise RuntimeError("V008_RESULT_ALREADY_EXISTS")

    case = freeze["case"]
    if case["case_id"] != freeze["case_order"][0] or case["slot"] != 1:
        raise RuntimeError("V008_CASE_IDENTITY_MISMATCH")
    request_payload = {
        "question_text": case["question_text"],
        "numbers": case["numbers"],
    }
    if _canonical_sha(request_payload) != case["input_sha256"]:
        raise RuntimeError("V008_INPUT_HASH_MISMATCH")
    if "?" in case["question_text"]:
        raise RuntimeError("V008_INPUT_ENCODING_LOSS")

    from abalo_iching.application import sites_direct_reading_v2 as module

    cast_count = 0
    original_cast = module.cast_meihua

    def counted_cast(value):
        nonlocal cast_count
        cast_count += 1
        return original_cast(value)

    request_id = "drv2-" + hashlib.sha256(case["case_id"].encode("ascii")).hexdigest()[:32]
    module.cast_meihua = counted_cast
    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    try:
        prepared = prepare_direct_reading_v2_request(request_payload, request_id=request_id)
        if prepared.request.question_text != case["question_text"]:
            raise RuntimeError("V008_PREPARED_QUESTION_MISMATCH")
        if prepared.request.numbers != tuple(case["numbers"]):
            raise RuntimeError("V008_PREPARED_NUMBERS_MISMATCH")
        if case["question_text"] not in prepared.user_prompt:
            raise RuntimeError("V008_PROMPT_QUESTION_MISMATCH")
        result = process_prepared_direct_reading_v2_request(
            prepared,
            provider=OpenAIDirectReadingProvider(),
        )
    finally:
        module.cast_meihua = original_cast
    finished = datetime.now(ZoneInfo("Asia/Shanghai"))

    reading = result.get("direct_reading") or None
    text = reading.get("text") if reading else None
    evidence = {
        "evidence_type": "V008_REALITY_LINEAGE_REAL_HIGH_CANARY",
        "stage_id": freeze["stage_id"],
        "freeze_version": freeze["freeze_version"],
        "freeze_sha256": ledger["freeze_sha256"],
        "candidate_manifest_sha256": manifest_sha,
        "slot": 1,
        "case_id": case["case_id"],
        "domain": case["domain"],
        "input_type": case["input_type"],
        "input": request_payload,
        "input_sha256": case["input_sha256"],
        "request_id": result["audit"]["request_id"],
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "call_ledger": {
            "authorized_slot": 1,
            "router_attempts": 0,
            "high_attempts": 1,
            "provider_attempts": 1,
            "automatic_retries": 0,
            "deterministic_cast_count": cast_count,
        },
        "status": result["status"],
        "validation_errors": result.get("validation_errors", []),
        "chart_facts": prepared.chart_facts.model_dump(mode="json"),
        "direct_reading": reading,
        "reading_utf8_sha256": (
            hashlib.sha256(text.encode("utf-8")).hexdigest().upper() if text else None
        ),
        "audit": result["audit"],
    }
    RESULT_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    ledger["actual_high_attempts"] = 1
    ledger["remaining_high_attempts"] = 0
    ledger["provider_instantiated"] = True
    ledger["cases"] = [
        {
            "slot": 1,
            "case_id": case["case_id"],
            "input_sha256": case["input_sha256"],
            "result_path": str(RESULT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "status": evidence["status"],
            "deterministic_cast_count": cast_count,
            "provider_attempts": 1,
            "automatic_retries": 0,
            "validation_errors": evidence["validation_errors"],
            "reading_utf8_sha256": evidence["reading_utf8_sha256"],
            "latency_ms": result["audit"].get("latency_ms"),
            "consumed": True,
        }
    ]
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "case_id": case["case_id"],
                "status": evidence["status"],
                "cast_count": cast_count,
                "provider_attempts": 1,
                "retry": 0,
                "latency_ms": result["audit"].get("latency_ms"),
                "validation_errors": evidence["validation_errors"],
                "reading_sha256": evidence["reading_utf8_sha256"],
                "remaining": 0,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

