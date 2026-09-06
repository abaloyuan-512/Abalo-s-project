"""Explicit, bounded synthetic benchmark. Never called by the production server."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from abalo_iching.application.sites_direct_high_product_v1 import build_direct_high_product_presentation
from abalo_iching.application.sites_direct_reading_speed_v1 import prepare_concise_reading
from abalo_iching.application.sites_direct_reading_v3 import (
    DirectReadingPreparedRequest,
    OpenAIDirectReadingProvider,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)

CASES = (
    {"question_text": "我在考虑换工作，应该先留在原岗位观察，还是开始投递新的机会？", "numbers": [5, 6, 3]},
    {"question_text": "我想和朋友合作开一家小店，现在应该先做小规模试卖，还是直接租店铺？", "numbers": [3, 77, 46]},
    {"question_text": "最近我和伴侣沟通不顺，我应该主动约一次认真谈话，还是先给彼此一点空间？", "numbers": [8, 2, 9]},
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=int, choices=range(len(CASES)), required=True)
    parser.add_argument("--profile", choices=("baseline-high", "concise-high", "concise-medium"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-synthetic-live-call", action="store_true", required=True)
    args = parser.parse_args()
    # Exclusive creation prevents an accidental rerun from spending another call.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump({"state": "STARTED", "case": args.case, "profile": args.profile}, handle)
    prepared = prepare_direct_reading_v2_request(
        CASES[args.case],
        clock=lambda: datetime(2026, 9, 6, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert isinstance(prepared, DirectReadingPreparedRequest)
    if args.profile.startswith("concise"):
        prepared = prepare_concise_reading(prepared)
    diagnostics: list[dict[str, Any]] = []
    response = process_prepared_direct_reading_v2_request(
        prepared,
        provider=OpenAIDirectReadingProvider(
            reasoning_effort="medium" if args.profile.endswith("medium") else "high",
            output_profile="concise" if args.profile.startswith("concise") else "standard",
        ),
        diagnostic_sink=diagnostics.append,
        synthetic_diagnostic_confirmed=True,
    )
    mapping_ok = False
    mapping_error: str | None = None
    if response["status"] == "SUCCESS":
        try:
            build_direct_high_product_presentation(prepared, response)
            mapping_ok = True
        except (ValueError, TypeError):
            mapping_error = "P8_P9_PRODUCT_MAPPING_FAILED"
    report = {
        "state": "COMPLETE", "case": args.case, "profile": args.profile,
        "synthetic_question": CASES[args.case]["question_text"],
        "chart_sha256": prepared.chart_sha256, "mapping_ok": mapping_ok, "mapping_error": mapping_error,
        "response": response, "synthetic_diagnostics": diagnostics,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "case": args.case, "profile": args.profile, "status": response["status"],
        "mapping_ok": mapping_ok, "error_code": response.get("error_code"),
        "validation_errors": response.get("validation_errors"),
        "timings": response["audit"].get("phase_timings"),
        "usage": response["audit"].get("usage"),
        "chars": len((response.get("direct_reading") or {}).get("text", "")),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
