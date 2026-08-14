from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_direct_high_product_v1 import (
    DirectHighEntryMode,
    process_direct_high_product_request,
)
from abalo_iching.application.sites_direct_reading_v2 import (
    MODEL,
    DirectReadingProviderResult,
    DirectReadingUsage,
    prepare_direct_reading_v2_request,
)


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_high_p8_p9_product_v001"
OUTPUT = STAGE / "offline_ledger.json"
FIXED_CLOCK = lambda: datetime(2026, 8, 11, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


class FixtureProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def generate(self, **_kwargs):
        self.calls += 1
        return DirectReadingProviderResult(
            output_text=self.text,
            api_status="completed",
            incomplete_details=None,
            response_id=f"fixture-{self.calls}",
            model=MODEL,
            usage=DirectReadingUsage(input_tokens=10, output_tokens=100, total_tokens=110),
            latency_ms=1,
        )


def main() -> int:
    cases = json.loads(
        (ROOT / "evals/meihua/direct_reading_v2_stability_v010/frozen_cases.json").read_text(encoding="utf-8")
    )["cases"]
    live = json.loads((ROOT / "outputs/v011_stability_run_ledger.json").read_text(encoding="utf-8"))["cases"]
    released_by_id = {row["case_id"]: row["released_direct_reading"] for row in live}
    v009 = json.loads((ROOT / "outputs/v009_canary_real_result.json").read_text(encoding="utf-8"))
    evidence_cases = [
        {
            "anchor": "V009-CANARY-01",
            "question_text": v009["input"]["question_text"],
            "numbers": v009["input"]["numbers"],
            "input_sha256": v009["input_sha256"],
            "released": v009["direct_reading"],
            "expected_reading_sha256": v009["reading_utf8_sha256"],
        },
        *[
            {
                "anchor": frozen["case_id"],
                "question_text": frozen["question_text"],
                "numbers": frozen["numbers"],
                "input_sha256": frozen["input_sha256"],
                "released": released_by_id[frozen["case_id"]],
                "expected_reading_sha256": sha(released_by_id[frozen["case_id"]]["text"]),
            }
            for frozen in cases
        ],
    ]
    original_cast = high_service.cast_meihua
    rows = []
    for index, mode in enumerate(DirectHighEntryMode):
        frozen = evidence_cases[index]
        released = frozen["released"]
        cast_calls = 0

        def counted(value):
            nonlocal cast_calls
            cast_calls += 1
            return original_cast(value)

        provider = FixtureProvider(released["text"])
        high_service.cast_meihua = counted
        try:
            result = process_direct_high_product_request(
                entry_mode=mode,
                original_question=frozen["question_text"],
                numbers=tuple(frozen["numbers"]),
                provider=provider,
                clock=FIXED_CLOCK,
                request_id=f"drv2-product-{mode.value.lower():0<16}",
            )
        finally:
            high_service.cast_meihua = original_cast
        presentation = result.presentation
        rows.append(
            {
                "case_id": f"P8P9-{index + 1:02d}-{mode.value}",
                "quality_anchor": frozen["anchor"],
                "entry_mode": mode.value,
                "input_sha256": frozen["input_sha256"],
                "question_sha_preserved": len({
                    result.product_audit.original_question_sha256_before,
                    result.product_audit.original_question_sha256_sent,
                    result.product_audit.original_question_sha256_after,
                }) == 1,
                "status": result.status,
                "released": result.released,
                "prepare_attempts": 1,
                "deterministic_cast_count": cast_calls,
                "provider_attempts": provider.calls,
                "fixed_high_attempts": provider.calls,
                "automatic_retries": 0,
                "router_attempts": 0,
                "router_live_calls": 0,
                "router_model_calls": 0,
                "mapping_model_calls": 0,
                "mapping_additional_casts": 0,
                "source_reading_sha256": presentation.source_reading_sha256 if presentation else None,
                "expected_reading_sha256": frozen["expected_reading_sha256"],
                "reconstructed_reading_sha256": presentation.reconstructed_reading_sha256 if presentation else None,
                "reconstructed_equals_source": presentation.reconstructed_equals_source if presentation else False,
                "program_strength_source": presentation.page8.program_strength.source if presentation else None,
                "p8_responsibility": presentation.page8.responsibility if presentation else None,
                "p9_responsibility": presentation.page9.responsibility if presentation else None,
            }
        )

    source = (ROOT / "src/abalo_iching/application/sites_direct_high_product_v1.py").read_text(encoding="utf-8")
    imports = [
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    ]
    ledger = {
        "stage_id": "DIRECT_HIGH_P8_P9_PRODUCT_V001",
        "evidence_kind": "OFFLINE_FIXTURE_ONLY",
        "quality_anchors": {
            "V009-CANARY-01": "40376C23B51D91A36049242A3DCE24C2FD97C14AC57EBB17B0AD56AC3FF0CAAD",
            "V011_distinct_cases": [case["case_id"] for case in cases],
        },
        "case_denominator": len(rows),
        "success_count": sum(row["released"] for row in rows),
        "failed_count": sum(not row["released"] for row in rows),
        "prepare_attempts": sum(row["prepare_attempts"] for row in rows),
        "deterministic_cast_count": sum(row["deterministic_cast_count"] for row in rows),
        "provider_attempts": sum(row["provider_attempts"] for row in rows),
        "fixed_high_attempts": sum(row["fixed_high_attempts"] for row in rows),
        "automatic_retries": 0,
        "router_attempts": 0,
        "router_live_calls": 0,
        "router_model_calls": 0,
        "mapping_model_calls": 0,
        "mapping_additional_casts": 0,
        "router_imports": [name for name in imports if "router" in name.lower()],
        "live_calls": 0,
        "real_provider_instantiated": False,
        "deployment": False,
        "production": False,
        "default_replacement": False,
        "rows": rows,
    }
    if not (
        ledger["case_denominator"] == ledger["success_count"] == 3
        and ledger["prepare_attempts"] == ledger["deterministic_cast_count"] == ledger["provider_attempts"] == ledger["fixed_high_attempts"] == 3
        and all(row["question_sha_preserved"] and row["reconstructed_equals_source"] for row in rows)
        and all(row["source_reading_sha256"] == row["expected_reading_sha256"] for row in rows)
        and rows[0]["quality_anchor"] == "V009-CANARY-01"
        and len({row["quality_anchor"] for row in rows}) == 3
        and ledger["router_imports"] == []
    ):
        raise RuntimeError("OFFLINE_LEDGER_INVARIANT")
    OUTPUT.write_bytes((json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(hashlib.sha256(OUTPUT.read_bytes()).hexdigest().upper())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
