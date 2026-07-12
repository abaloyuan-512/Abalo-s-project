"""Offline Contract V1 sweep across every hexagram/line and twelve seasons."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abalo_iching.application import process_sites_meihua_request  # noqa: E402

CONTRACT_DIR = ROOT / "contracts" / "sites_meihua_v1"
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def is_contract_datetime(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return "T" in value and parsed.tzinfo is not None


def validator():
    schema = json.loads((CONTRACT_DIR / "response.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def request(request_id, numbers, timestamp="2026-07-13T10:00:00+08:00"):
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V1",
        "request_id": request_id,
        "question_text": "合成Contract覆盖问题？",
        "numbers": list(numbers),
        "locale": "zh-CN",
        "client_timestamp": timestamp,
        "user_acknowledgements": {"deterministic_only": True, "narrative_unverified": True},
    }


def build_contract_sweep():
    check = validator()
    clock = datetime(2026, 7, 13, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    rows = []
    for upper in range(1, 9):
        for lower in range(1, 9):
            for moving_line in range(1, 7):
                numbers = (upper, lower, moving_line)
                response = process_sites_meihua_request(request(f"sweep-{upper}-{lower}-{moving_line}", numbers), clock=lambda: clock)
                errors = list(check.iter_errors(response))
                result = response["deterministic_result"]
                rows.append({
                    "input_numbers": list(numbers),
                    "base_hexagram": result["base_hexagram"]["king_wen_number"],
                    "moving_line": result["moving_line"],
                    "mutual_hexagram": result["mutual_hexagram"]["king_wen_number"],
                    "changed_hexagram": result["changed_hexagram"]["king_wen_number"],
                    "conclusion_level": result["deterministic_conclusion"]["conclusion_level"],
                    "evidence_sufficiency": result["deterministic_conclusion"]["evidence_sufficiency"],
                    "response_schema_result": "PASS" if not errors else "FAIL",
                    "should_charge": response["release_gate"]["should_charge"],
                    "formal_persistence": response["release_gate"]["formal_report_persistence_allowed"],
                    "closed_beta": response["release_gate"]["closed_beta_allowed"],
                    "narrative_status": response["narrative"]["status"],
                })
    pairs = {(row["base_hexagram"], row["moving_line"]) for row in rows}
    summary = {
        "completed": len(rows), "passed": sum(row["response_schema_result"] == "PASS" for row in rows),
        "hexagrams_covered": len({row["base_hexagram"] for row in rows}), "hexagram_line_pairs": len(pairs),
        "all_six_lines_per_hexagram": all({line for number, line in pairs if number == hexagram} == set(range(1, 7)) for hexagram in range(1, 65)),
        "should_charge_true": sum(row["should_charge"] for row in rows),
        "formal_persistence_true": sum(row["formal_persistence"] for row in rows),
        "closed_beta_true": sum(row["closed_beta"] for row in rows),
        "narrative_not_unverified": sum(row["narrative_status"] != "UNVERIFIED" for row in rows),
        "external_api_calls": 0,
    }
    return rows, summary


def build_seasonal_sweep():
    check = validator()
    rows = []
    for month in range(1, 13):
        clock = datetime(2026, month, 15, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        response = process_sites_meihua_request(request(f"season-2026-{month:02d}", (100, 27, 368)), clock=lambda clock=clock: clock)
        result = response["deterministic_result"]
        rows.append({
            "month": month, "seasonal_strength": result["seasonal_strength"],
            "response_schema_result": "PASS" if not list(check.iter_errors(response)) else "FAIL",
            "client_timestamp_used_for_calculation": response["audit"]["client_timestamp_used_for_calculation"],
        })
    return rows, {"completed": len(rows), "passed": sum(row["response_schema_result"] == "PASS" for row in rows), "client_timestamp_used_true": sum(row["client_timestamp_used_for_calculation"] for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if ROOT.resolve() == args.output.resolve() or ROOT.resolve() in args.output.resolve().parents:
        raise ValueError("output must be outside repository")
    args.output.mkdir(parents=True, exist_ok=False)
    contract_rows, contract_summary = build_contract_sweep()
    seasonal_rows, seasonal_summary = build_seasonal_sweep()
    (args.output / "contract_conformance_384.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in contract_rows), encoding="utf-8")
    (args.output / "seasonal_contract_sweep_12.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in seasonal_rows), encoding="utf-8")
    (args.output / "sweep_summary.json").write_text(json.dumps({"contract": contract_summary, "seasonal": seasonal_summary}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contract": contract_summary, "seasonal": seasonal_summary}))


if __name__ == "__main__":
    main()
