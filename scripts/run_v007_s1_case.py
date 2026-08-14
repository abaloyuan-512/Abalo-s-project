from __future__ import annotations

import argparse
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
FREEZE_PATH = ROOT / "outputs" / "v007_s1_case_freeze.json"
LEDGER_PATH = ROOT / "outputs" / "v007_s1_call_ledger.json"
EXPECTED_FREEZE_SHA256 = "4AD16E382AFD00B0A38740669644EC8895A2876FA834DFC74022B336BA09BD8C"


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int, required=True, choices=(1, 2, 3))
    args = parser.parse_args()

    freeze_bytes = FREEZE_PATH.read_bytes()
    freeze_sha = hashlib.sha256(freeze_bytes).hexdigest().upper()
    if freeze_sha != EXPECTED_FREEZE_SHA256:
        raise RuntimeError("S1_FREEZE_HASH_MISMATCH")
    freeze = json.loads(freeze_bytes.decode("utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if ledger["freeze_sha256"] != freeze_sha:
        raise RuntimeError("S1_LEDGER_FREEZE_MISMATCH")
    if args.slot != ledger["actual_high_attempts"] + 1:
        raise RuntimeError("S1_SLOT_ORDER_VIOLATION")
    if ledger["remaining_high_attempts"] <= 0:
        raise RuntimeError("S1_BUDGET_EXHAUSTED")

    case = freeze["cases"][args.slot - 1]
    if case["slot"] != args.slot or case["case_id"] != freeze["case_order"][args.slot - 1]:
        raise RuntimeError("S1_CASE_IDENTITY_MISMATCH")
    output_path = ROOT / "outputs" / f"v007_{case['case_id'].lower().replace('-', '_')}_real_result.json"
    if output_path.exists():
        raise RuntimeError("S1_CASE_RESULT_ALREADY_EXISTS")

    request_payload = {"question_text": case["question_text"], "numbers": case["numbers"]}
    if "?" in case["question_text"]:
        raise RuntimeError("S1_INPUT_ENCODING_LOSS")
    input_sha = canonical_sha(request_payload)
    request_id = "drv2-" + hashlib.sha256(case["case_id"].encode("ascii")).hexdigest()[:32]

    from abalo_iching.application import sites_direct_reading_v2 as module

    cast_count = 0
    original_cast = module.cast_meihua

    def counted_cast(value):
        nonlocal cast_count
        cast_count += 1
        return original_cast(value)

    module.cast_meihua = counted_cast
    attempt_started = datetime.now(ZoneInfo("Asia/Shanghai"))
    try:
        prepared = prepare_direct_reading_v2_request(request_payload, request_id=request_id)
        if prepared.request.question_text != case["question_text"]:
            raise RuntimeError("S1_PREPARED_QUESTION_MISMATCH")
        if prepared.request.numbers != tuple(case["numbers"]):
            raise RuntimeError("S1_PREPARED_NUMBERS_MISMATCH")
        if case["question_text"] not in prepared.user_prompt:
            raise RuntimeError("S1_PROMPT_QUESTION_MISMATCH")
        result = process_prepared_direct_reading_v2_request(
            prepared,
            provider=OpenAIDirectReadingProvider(),
        )
    finally:
        module.cast_meihua = original_cast
    attempt_finished = datetime.now(ZoneInfo("Asia/Shanghai"))

    reading = result.get("direct_reading") or None
    text = reading.get("text") if reading else None
    evidence = {
        "evidence_type": "V007_S1_REAL_HIGH_CASE",
        "stage_id": freeze["stage_id"],
        "freeze_version": freeze["freeze_version"],
        "freeze_sha256": freeze_sha,
        "slot": args.slot,
        "case_id": case["case_id"],
        "domain": case["domain"],
        "input_type": case["input_type"],
        "input": request_payload,
        "input_sha256": input_sha,
        "request_id": result["audit"]["request_id"],
        "started_at": attempt_started.isoformat(),
        "finished_at": attempt_finished.isoformat(),
        "call_ledger": {
            "authorized_slot": args.slot,
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
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    ledger["actual_high_attempts"] += 1
    ledger["remaining_high_attempts"] -= 1
    ledger["provider_instantiated"] = True
    ledger["cases"].append(
        {
            "slot": args.slot,
            "case_id": case["case_id"],
            "input_sha256": input_sha,
            "result_path": str(output_path.relative_to(ROOT)).replace("\\", "/"),
            "status": evidence["status"],
            "deterministic_cast_count": cast_count,
            "provider_attempts": 1,
            "automatic_retries": 0,
            "validation_errors": evidence["validation_errors"],
            "reading_utf8_sha256": evidence["reading_utf8_sha256"],
            "latency_ms": result["audit"].get("latency_ms"),
            "consumed": True,
        }
    )
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "slot": args.slot,
                "case_id": case["case_id"],
                "status": evidence["status"],
                "cast_count": cast_count,
                "provider_attempts": 1,
                "retry": 0,
                "latency_ms": result["audit"].get("latency_ms"),
                "validation_errors": evidence["validation_errors"],
                "reading_sha256": evidence["reading_utf8_sha256"],
                "remaining": ledger["remaining_high_attempts"],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

