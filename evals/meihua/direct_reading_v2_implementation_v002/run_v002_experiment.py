from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching.application.sites_direct_reading_v2 import (  # noqa: E402
    OpenAIDirectReadingProvider,
    process_direct_reading_v2_request,
)
from scripts.run_hosted_api import create_server  # noqa: E402


STAGE = ROOT / "evals/meihua/direct_reading_v2_implementation_v002"
MANIFEST = STAGE / "manifest.json"
CASES = ROOT / "evals/meihua/direct_reading_v2_research_v001/cases/cases.json"
RUNS = STAGE / "runs"
PRIVATE = STAGE / "private"
ENGINE_KEY = "synthetic-v002-engine-key-that-is-long-enough"
MEDIUM_CASE_IDS = ("DR-01-Q1", "DR-03-Q2", "DR-04-Q2")
FIXED_CAST_AT = "2026-08-11T12:00:00+08:00"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_tree(path: Path) -> str:
    rows = [
        f"{item.relative_to(path).as_posix()}:{sha_file(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest().upper()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def exclusive_marker(name: str) -> Path:
    path = RUNS / f"{name}.started"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(datetime.now().astimezone().isoformat() + "\n")
    return path


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify_execution_freeze(manifest: dict[str, Any]) -> None:
    snapshot = manifest.get("execution_snapshot")
    files = manifest.get("execution_files")
    trees = manifest.get("execution_trees")
    if not isinstance(snapshot, dict) or not isinstance(files, dict) or not isinstance(trees, dict):
        raise RuntimeError("EXECUTION_FREEZE_MISSING")
    snapshot_path = ROOT / str(snapshot.get("path", ""))
    if not snapshot_path.is_file() or sha_file(snapshot_path) != snapshot.get("sha256"):
        raise RuntimeError("EXECUTION_SNAPSHOT_MISMATCH")
    for relative, expected in files.items():
        path = ROOT / relative
        if not path.is_file() or sha_file(path) != expected:
            raise RuntimeError(f"EXECUTION_FILE_MISMATCH:{relative}")
    for relative, expected in trees.items():
        path = ROOT / relative
        if not path.is_dir() or sha_tree(path) != expected:
            raise RuntimeError(f"EXECUTION_TREE_MISMATCH:{relative}")
    if manifest.get("automatic_retry_limit") != 0 or int(manifest.get("live_model_call_limit", 0)) != 5:
        raise RuntimeError("CALL_BUDGET_CONTRACT_MISMATCH")


def verify_live_preflight(*, require_sites: bool = False) -> None:
    """Check every zero-call prerequisite before consuming a phase marker."""
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY_MISSING")
    if require_sites:
        node_executable = os.environ.get("ABALO_V002_NODE_EXECUTABLE", "").strip()
        if not node_executable or not Path(node_executable).is_file():
            raise RuntimeError("NODE_EXECUTABLE_MISSING")
        for path in (
            ROOT / "sites/hosted-app/dist/server/index.js",
            ROOT / "sites/hosted-app/tests/fixtures/run-final-sites-canary.mjs",
        ):
            if not path.is_file():
                raise RuntimeError(f"SITES_CANARY_ASSET_MISSING:{path.name}")


def verify_final_budget_state(manifest: dict[str, Any]) -> None:
    """Separate paid attempts from conservatively consumed batch slots."""
    if int(manifest.get("live_model_calls_completed", -1)) != 3:
        raise RuntimeError("FINAL_CANARY_ACTUAL_CALL_STATE_INVALID")
    if int(manifest.get("authorized_budget_slots_consumed", -1)) != 4:
        raise RuntimeError("FINAL_CANARY_SLOT_STATE_INVALID")


def case_index() -> dict[str, dict[str, Any]]:
    document = json.loads(CASES.read_text(encoding="utf-8"))
    indexed: dict[str, dict[str, Any]] = {}
    for chart in document["cases"]:
        for question in chart["questions"]:
            indexed[question["question_id"]] = {
                "case_id": question["question_id"],
                "question_text": question["question_text"],
                "numbers": chart["numbers"],
                "cast_at": FIXED_CAST_AT,
            }
    return indexed


def synthetic_request_id(case_id: str, phase: str) -> str:
    digest = hashlib.sha256(f"{phase}:{case_id}".encode()).hexdigest()[:32]
    return f"drv2-{digest}"


def run_case(case: dict[str, Any], *, effort: str, phase: str) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    response = process_direct_reading_v2_request(
        {"question_text": case["question_text"], "numbers": case["numbers"]},
        provider=OpenAIDirectReadingProvider(reasoning_effort=effort),  # type: ignore[arg-type]
        clock=lambda: datetime.fromisoformat(case["cast_at"]),
        request_id=synthetic_request_id(case["case_id"], phase),
        diagnostic_sink=diagnostics.append,
        synthetic_diagnostic_confirmed=True,
    )
    private_path = PRIVATE / f"{phase}_{case['case_id']}.json"
    atomic_json(
        private_path,
        {
            "synthetic": True,
            "case_id": case["case_id"],
            "effort": effort,
            "response": response,
            "rejected_output_diagnostics": diagnostics,
        },
    )
    return {
        "case_id": case["case_id"],
        "effort": effort,
        "status": response["status"],
        "response": response,
        "private_evidence_path": str(private_path.relative_to(ROOT)).replace("\\", "/"),
        "private_evidence_sha256": sha_file(private_path),
    }


def high_canary() -> None:
    manifest = load_manifest()
    verify_execution_freeze(manifest)
    if int(manifest.get("live_model_calls_completed", -1)) != 0:
        raise RuntimeError("HIGH_CANARY_BUDGET_STATE_INVALID")
    verify_live_preflight()
    exclusive_marker("high_canary")
    result = run_case(case_index()["DR-01-Q1"], effort="high", phase="high_canary")
    atomic_json(
        RUNS / "high_canary.json",
        {"phase": "HIGH_CORRECTNESS_CANARY", "call_attempts": 1, "automatic_retries": 0, "result": result},
    )


def medium_batch() -> None:
    manifest = load_manifest()
    verify_execution_freeze(manifest)
    if int(manifest.get("live_model_calls_completed", -1)) != 1:
        raise RuntimeError("MEDIUM_BATCH_BUDGET_STATE_INVALID")
    high = json.loads((RUNS / "high_canary.json").read_text(encoding="utf-8"))
    if high["result"]["status"] != "SUCCESS":
        raise RuntimeError("HIGH_CANARY_NOT_SUCCESS")
    verify_live_preflight()
    exclusive_marker("medium_batch")
    indexed = case_index()
    document: dict[str, Any] = {
        "phase": "MEDIUM_LATENCY_BATCH",
        "call_attempts": 0,
        "automatic_retries": 0,
        "results": [],
    }
    for case_id in MEDIUM_CASE_IDS:
        result = run_case(indexed[case_id], effort="medium", phase="medium_batch")
        document["call_attempts"] += 1
        document["results"].append(result)
        atomic_json(RUNS / "medium_batch.json", document)
        if result["status"] != "SUCCESS":
            break


def final_http_canary() -> None:
    manifest = load_manifest()
    verify_execution_freeze(manifest)
    verify_final_budget_state(manifest)
    selected_effort = str(manifest.get("selected_reasoning_effort", ""))
    if selected_effort not in {"medium", "high"}:
        raise RuntimeError("SELECTED_EFFORT_MISSING")
    verify_live_preflight(require_sites=True)
    exclusive_marker("final_http_canary")
    previous_enabled = os.environ.get("ABALO_DIRECT_READING_V2_ENABLED")
    previous_effort = os.environ.get("ABALO_DIRECT_READING_REASONING_EFFORT")
    os.environ["ABALO_DIRECT_READING_V2_ENABLED"] = "true"
    os.environ["ABALO_DIRECT_READING_REASONING_EFFORT"] = selected_effort
    case = case_index()["DR-01-Q1"]
    request_id = synthetic_request_id(case["case_id"], "final_http_canary")
    diagnostics: list[dict[str, Any]] = []
    server = create_server(
        "127.0.0.1",
        0,
        ENGINE_KEY,
        direct_reading_diagnostic_sink=diagnostics.append,
        direct_reading_internal_audit_sink=diagnostics.append,
        direct_reading_synthetic_diagnostic_confirmed=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    started = time.perf_counter()
    outcome = "PROCESS_FAILED"
    route_result: dict[str, Any] | None = None
    stdout_text = ""
    stderr_text = ""
    failure_code: str | None = None
    try:
        node_executable = os.environ["ABALO_V002_NODE_EXECUTABLE"].strip()
        dist = ROOT / "sites/hosted-app/dist/server/index.js"
        helper = ROOT / "sites/hosted-app/tests/fixtures/run-final-sites-canary.mjs"
        completed = subprocess.run(
            [
                node_executable,
                str(helper),
                str(dist),
                str(server.server_port),
                ENGINE_KEY,
                request_id,
                case["question_text"],
                json.dumps(case["numbers"]),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=220,
        )
        stdout_text = completed.stdout
        stderr_text = completed.stderr
        if completed.returncode != 0:
            failure_code = "SITES_CANARY_PROCESS_FAILED"
        else:
            route_result = json.loads(completed.stdout)
            outcome = "COMPLETED"
    except subprocess.TimeoutExpired as exc:
        failure_code = "SITES_CANARY_PROCESS_TIMEOUT"
        stdout_text = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr_text = exc.stderr if isinstance(exc.stderr, str) else ""
    except (UnicodeError, json.JSONDecodeError, OSError):
        failure_code = "SITES_CANARY_EVIDENCE_ERROR"
    finally:
        private_path = PRIVATE / "final_http_canary_diagnostics.json"
        with server.direct_reading_jobs_lock:
            job = server.direct_reading_jobs.get(request_id)
            job_snapshot = {
                "status": job.get("status"),
                "stage": job.get("stage"),
                "has_response": job.get("response") is not None,
            } if job is not None else None
        atomic_json(
            private_path,
            {
                "synthetic": True,
                "case_id": case["case_id"],
                "diagnostics": diagnostics,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "python_job": job_snapshot,
            },
        )
        atomic_json(
            RUNS / "final_http_canary.json",
            {
                "phase": "FINAL_SITES_TO_PYTHON_HTTP_CANARY",
                "call_attempts": 1,
                "automatic_retries": 0,
                "selected_reasoning_effort": selected_effort,
                "outcome": outcome,
                "failure_code": failure_code,
                "route_result": route_result,
                "private_diagnostic_path": str(private_path.relative_to(ROOT)).replace("\\", "/"),
                "private_diagnostic_sha256": sha_file(private_path),
                "wall_latency_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        if previous_enabled is None:
            os.environ.pop("ABALO_DIRECT_READING_V2_ENABLED", None)
        else:
            os.environ["ABALO_DIRECT_READING_V2_ENABLED"] = previous_enabled
        if previous_effort is None:
            os.environ.pop("ABALO_DIRECT_READING_REASONING_EFFORT", None)
        else:
            os.environ["ABALO_DIRECT_READING_REASONING_EFFORT"] = previous_effort
    if outcome != "COMPLETED":
        raise RuntimeError(failure_code or "SITES_CANARY_PROCESS_FAILED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("high-canary", "medium-batch", "final-http-canary"))
    args = parser.parse_args()
    {"high-canary": high_canary, "medium-batch": medium_batch, "final-http-canary": final_http_canary}[args.phase]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
