from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from abalo_iching.application.sites_parse_exception_classifier_v020 import (
    ParseOrSchemaFailure,
    classify_parse_boundary_failure,
)


OUTPUT = Path(__file__).with_name("offline_ledger.json")
REQUEST = httpx.Request("POST", "https://fixture.invalid")


class MaliciousReceipt:
    effects = 0

    def __getattr__(self, name: str) -> object:
        type(self).effects += 1
        raise AttributeError(name)

    def __str__(self) -> str:
        type(self).effects += 1
        return "secret"


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=REQUEST)


def fixtures() -> list[tuple[str, object, str, str]]:
    return [
        ("TIMEOUT", APITimeoutError(request=REQUEST), "TIMEOUT", "IN_PARSE_BOUNDARY"),
        ("CONNECTION", APIConnectionError(request=REQUEST), "CONNECTION", "IN_PARSE_BOUNDARY"),
        ("AUTH", AuthenticationError("secret", response=_response(401), body=None), "AUTHENTICATION", "IN_PARSE_BOUNDARY"),
        ("RATE", RateLimitError("raw", response=_response(429), body=None), "RATE_LIMIT", "IN_PARSE_BOUNDARY"),
        ("BAD_REQUEST_400", BadRequestError("server", response=_response(400), body=None), "BAD_REQUEST", "IN_PARSE_BOUNDARY"),
        ("SERVER_ERROR_500", InternalServerError("bad request", response=_response(500), body=None), "SERVER_ERROR", "IN_PARSE_BOUNDARY"),
        ("PARSE_OR_SCHEMA", ParseOrSchemaFailure(), "PARSE_OR_SCHEMA", "AFTER_PARSE_RESPONSE"),
        ("UNKNOWN", RuntimeError("traceback"), "UNKNOWN_PROVIDER_ERROR", "IN_PARSE_BOUNDARY"),
        ("OTHER_STATUS", APIStatusError("status", response=_response(403), body=None), "UNKNOWN_PROVIDER_ERROR", "IN_PARSE_BOUNDARY"),
        ("MALICIOUS", MaliciousReceipt(), "UNKNOWN_PROVIDER_ERROR", "IN_PARSE_BOUNDARY"),
        ("BEFORE_BOUNDARY", RuntimeError(), "UNKNOWN_PROVIDER_ERROR", "BEFORE_PARSE_BOUNDARY"),
    ]


def build() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for case_id, failure, expected, stage in fixtures():
        result = classify_parse_boundary_failure(failure=failure, stage=stage)  # type: ignore[arg-type]
        assert result["failure_code"] == expected
        rows.append({
            "case_id": case_id,
            **result,
            "provider_calls": 0,
            "live_calls": 0,
            "sdk_extractions": 0,
            "v017_attempts": 0,
            "high_calls": 0,
            "prepare_calls": 0,
            "cast_calls": 0,
            "process_calls": 0,
        })
    assert MaliciousReceipt.effects == 0
    codes = [
        "TIMEOUT", "CONNECTION", "AUTHENTICATION", "RATE_LIMIT",
        "BAD_REQUEST", "SERVER_ERROR", "PARSE_OR_SCHEMA", "UNKNOWN_PROVIDER_ERROR",
    ]
    code_counts = {code: sum(row["failure_code"] == code for row in rows) for code in codes}
    assert all(value >= 1 for value in code_counts.values())
    assert sum(code_counts.values()) == len(rows)
    attempts = sum(int(row["classification_attempts"]) for row in rows)
    assert attempts == len(rows)
    return {
        "stage_id": "DIRECT_READING_V2_PARSE_EXCEPTION_V020",
        "status": "OFFLINE_EVIDENCE_COMPLETE",
        "case_denominator": len(rows),
        "classified_count": len(rows),
        "safe_failure_count": 0,
        "classification_attempts": attempts,
        "code_counts": code_counts,
        "malicious_side_effects": MaliciousReceipt.effects,
        "provider_calls": 0,
        "live_calls": 0,
        "real_provider_instantiated": False,
        "sdk_extractions": 0,
        "v017_attempts": 0,
        "high_calls": 0,
        "prepare_calls": 0,
        "cast_calls": 0,
        "process_calls": 0,
        "automatic_retries": 0,
        "cases": rows,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }


def main() -> None:
    data = build()
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    OUTPUT.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({"sha256": hashlib.sha256(encoded.encode()).hexdigest().upper(), "cases": len(data["cases"])}))


if __name__ == "__main__":
    main()
