"""Real Python transport fixture for the Sites-to-engine contract test.

The deterministic preparation and HTTP server are production code.  Only the
model/validator phase is replaced, so this fixture never consumes API tokens.
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from scripts import run_hosted_api as hosted  # noqa: E402


ENGINE_KEY = "cross-layer-test-engine-key-that-is-long-enough"


def _fixture_text(prepared):
    ledger = json.loads((ROOT / "outputs/v011_stability_run_ledger.json").read_text(encoding="utf-8"))
    for row in ledger["cases"]:
        released = row.get("released_direct_reading")
        if released and released.get("chart_facts") == prepared.chart_facts.model_dump(mode="json"):
            return released["text"]
    raise RuntimeError("NO_MATCHING_FROZEN_DIRECT_READING_FIXTURE")


def _stub_model_phase(prepared, *, progress_callback=None, **_kwargs):
    if progress_callback is not None:
        for stage in ("MODEL_REQUESTED", "MODEL_STREAMING", "MODEL_COMPLETED", "VALIDATING"):
            progress_callback(stage)
    return {
        "contract_version": hosted.DIRECT_READING_CONTRACT_VERSION,
        "status": "SUCCESS",
        "direct_reading": {
            "version": hosted.DIRECT_READING_CONTRACT_VERSION,
            "content_format": "MARKDOWN",
            "text": _fixture_text(prepared),
            "chart_facts": prepared.chart_facts.model_dump(mode="json"),
            "validation_status": "PASSED",
        },
        "page9_finale": {
            "content_version": "GUANXIANG_P9_FINALE_V1",
            "source": "SAME_PROVIDER_OUTPUT",
            "answer": ["可以推进，但要保留现实承接。", "先核实关键条件，再作最终决定。"],
            "additional_model_calls": 0,
        },
        "audit": {
            "request_id": prepared.request_id,
            "model": "must-not-cross-public-boundary",
            "usage": {"total_tokens": 999},
        },
        "error_code": None,
        "error_message": None,
        "retryable": False,
        "failure_stage": None,
    }


def main() -> int:
    os.environ["ABALO_DIRECT_READING_V2_ENABLED"] = "true"
    hosted.process_prepared_direct_reading_v2_request = _stub_model_phase
    server = hosted.create_server("127.0.0.1", 0, ENGINE_KEY)
    print(server.server_port, flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
