"""Execute the single authorized non-production Direct Reading V2 canary."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_direct_reading_v2 import process_direct_reading_v2_request


STAGE_REL = Path("evals/meihua/direct_reading_v2_implementation_v001")
PROMPT_REL = Path("evals/meihua/direct_reading_v2_research_v0011/prompts/prompt_package.json")
CASES_REL = Path("evals/meihua/direct_reading_v2_research_v001/cases/cases.json")
ENGINE_REL = Path("src/abalo_iching/meihua/engine.py")
SERVICE_REL = Path("src/abalo_iching/application/sites_direct_reading_v2.py")
TEST_REL = Path("tests/test_sites_direct_reading_v2.py")
RUNNER_REL = STAGE_REL / "run_nonprod_canary.py"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: object, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run(repo_root: Path) -> Path:
    stage = repo_root / STAGE_REL
    manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "IN_PROGRESS":
        raise RuntimeError("stage is not open for its single canary")
    if int(manifest["live_model_call_limit"]) != 1:
        raise RuntimeError("canary call limit mismatch")
    if int(manifest["live_model_calls_completed"]) != 0:
        raise RuntimeError("canary already consumed")
    if _sha_file(repo_root / PROMPT_REL) != manifest["research_prompt_sha256"]:
        raise RuntimeError("research prompt hash mismatch")
    if _sha_file(repo_root / CASES_REL) != manifest["research_cases_sha256"]:
        raise RuntimeError("research cases hash mismatch")
    if _sha_file(repo_root / ENGINE_REL) != manifest["deterministic_engine_sha256_before"]:
        raise RuntimeError("deterministic engine hash mismatch")
    for key, relative in (
        ("service_sha256", SERVICE_REL),
        ("test_sha256", TEST_REL),
        ("canary_runner_sha256", RUNNER_REL),
    ):
        if _sha_file(repo_root / relative) != manifest.get(key):
            raise RuntimeError(f"{key} mismatch")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable")

    runs = stage / "runs"
    marker = runs / "nonprod_canary_started.json"
    result_path = runs / "nonprod_canary.json"
    if marker.exists() or result_path.exists():
        raise RuntimeError("single canary marker already exists")
    started_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    _write_json(
        marker,
        {
            "stage_id": manifest["stage_id"],
            "started_at": started_at.isoformat(),
            "authorized_model_calls": 1,
            "automatic_retries": 0,
        },
        exclusive=True,
    )
    response = process_direct_reading_v2_request(
        {
            "question_text": "我要不要考虑换工作这件事？",
            "numbers": [5, 6, 3],
        },
        request_id="drv2-5f6d3a2026081101",
    )
    payload = {
        "stage_id": manifest["stage_id"],
        "status": "COMPLETED" if response["status"] == "SUCCESS" else "FAILED_CLOSED",
        "model_call_count": 1,
        "automatic_retries": 0,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "response": response,
    }
    _write_json(result_path, payload, exclusive=True)
    return result_path


if __name__ == "__main__":
    print(run(Path.cwd().resolve()))
