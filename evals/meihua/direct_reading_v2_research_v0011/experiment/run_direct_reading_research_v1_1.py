"""Run the output-control revision of the direct-reading research."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from openai import OpenAI

from evals.meihua.direct_reading_v2_research_v001.experiment.run_direct_reading_research import (
    _expand_questions,
    _request_messages,
)


REVISION_REL = Path("evals/meihua/direct_reading_v2_research_v0011")
SOURCE_REL = Path("evals/meihua/direct_reading_v2_research_v001")
MAX_NEW_CALLS = 17


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


def _sha_text(value: str) -> str:
    return _sha(value.encode("utf-8"))


def _usage(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _incomplete_details(response: Any) -> Any:
    details = getattr(response, "incomplete_details", None)
    if hasattr(details, "model_dump"):
        return details.model_dump(mode="json")
    return details


def _call(
    client: Any,
    *,
    case: dict[str, Any],
    prompts: dict[str, Any],
    arm: Literal["REFERENCE", "CANDIDATE"],
) -> dict[str, Any]:
    model = prompts["reference_model"] if arm == "REFERENCE" else prompts["candidate_model"]
    messages = _request_messages(case, prompts, arm)
    kwargs: dict[str, Any] = {
        "model": model,
        "input": messages,
        "store": False,
        "tools": [],
        "max_output_tokens": int(prompts["max_output_tokens"]),
    }
    if arm == "CANDIDATE":
        kwargs["reasoning"] = {"effort": prompts["candidate_reasoning_effort"]}
        kwargs["text"] = {"verbosity": prompts["candidate_verbosity"]}
    started_at = datetime.now(UTC)
    started = perf_counter()
    response = client.responses.create(**kwargs)
    finished_at = datetime.now(UTC)
    output_text = str(getattr(response, "output_text", "") or "").strip()
    usage = _usage(response)
    api_status = getattr(response, "status", None)
    hit_limit = usage["output_tokens"] is not None and int(usage["output_tokens"]) >= int(
        prompts["max_output_tokens"]
    )
    product_complete = bool(output_text) and api_status in (None, "completed") and not hit_limit
    return {
        "case_id": case["case_id"],
        "pair_id": case.get("pair_id"),
        "arm": arm,
        "model": model,
        "response_id": getattr(response, "id", None),
        "request_id": getattr(response, "_request_id", None),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "latency_ms": int((perf_counter() - started) * 1000),
        "input_sha256": _sha_text(json.dumps(messages, ensure_ascii=False, sort_keys=True)),
        "output_sha256": _sha_text(output_text),
        "usage": usage,
        "api_status": api_status,
        "incomplete_details": _incomplete_details(response),
        "hit_output_limit": hit_limit,
        "product_complete": product_complete,
        "output_text": output_text,
        "status": "SUCCESS" if product_complete else "INCOMPLETE_OUTPUT",
    }


def _validate_assets(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    revision = repo_root / REVISION_REL
    source = repo_root / SOURCE_REL
    manifest = _load(revision / "manifest.json")
    checks = {
        "prompts_sha256": _sha_file(revision / "prompts/prompt_package.json"),
        "cases_sha256": _sha_file(source / "cases/cases.json"),
        "runner_sha256": _sha_file(revision / "experiment/run_direct_reading_research_v1_1.py"),
        "source_reference_sha256": _sha_file(source / "runs/canary_run.json"),
    }
    for key, actual in checks.items():
        if str(manifest.get(key, "")).upper() != actual:
            raise RuntimeError(f"frozen asset mismatch: {key}")
    prompts = _load(revision / "prompts/prompt_package.json")
    cases_document = _load(source / "cases/cases.json")
    cases = _expand_questions(cases_document["cases"])
    if len(cases) != 9 or cases[0]["case_id"] != "DR-01-Q1":
        raise RuntimeError("source case set changed")
    if prompts["candidate_verbosity"] != "medium" or prompts["candidate_reasoning_effort"] != "high":
        raise RuntimeError("revision must change output control only")
    if int(manifest["max_new_model_calls"]) != MAX_NEW_CALLS:
        raise RuntimeError("revision call budget mismatch")
    reference = _load(source / "runs/canary_run.json")
    reference_calls = [
        call
        for call in reference.get("calls", [])
        if call.get("case_id") == "DR-01-Q1" and call.get("arm") == "REFERENCE"
    ]
    if len(reference_calls) != 1 or reference_calls[0].get("status") != "SUCCESS":
        raise RuntimeError("frozen DR-01 reference is unavailable")
    return prompts, cases, manifest


def run(repo_root: Path, phase: Literal["candidate_canary", "remaining"]) -> Path:
    revision = repo_root / REVISION_REL
    prompts, cases, manifest = _validate_assets(repo_root)
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable")
    runs = revision / "runs"
    if phase == "remaining":
        canary_path = runs / "candidate_canary_run.json"
        if not canary_path.exists():
            raise RuntimeError("remaining requires a completed product-level canary")
        canary = _load(canary_path)
        if (
            canary.get("status") != "COMPLETED"
            or canary.get("product_complete_count") != 1
            or canary.get("prompts_sha256") != manifest["prompts_sha256"]
        ):
            raise RuntimeError("candidate canary did not pass the product completeness gate")
    marker = runs / f"{phase}_started.json"
    result_path = runs / f"{phase}_run.json"
    _write_exclusive(
        marker,
        {
            "phase": phase,
            "started_at": datetime.now(UTC).isoformat(),
            "automatic_retries": 0,
            "new_call_budget": MAX_NEW_CALLS,
        },
    )
    work = [(cases[0], "CANDIDATE")] if phase == "candidate_canary" else [
        (case, arm) for case in cases[1:] for arm in ("REFERENCE", "CANDIDATE")
    ]
    payload: dict[str, Any] = {
        "phase": phase,
        "status": "IN_PROGRESS",
        "expected_call_count": len(work),
        "automatic_retries": 0,
        "prompts_sha256": manifest["prompts_sha256"],
        "cases_sha256": manifest["cases_sha256"],
        "calls": [],
    }
    _write(result_path, payload)
    client = OpenAI(timeout=120.0, max_retries=0)
    try:
        for case, arm in work:
            record = _call(client, case=case, prompts=prompts, arm=arm)
            payload["calls"].append(record)
            _write(result_path, payload)
            if not record["product_complete"]:
                raise RuntimeError(f"{case['case_id']} {arm} returned incomplete output")
        payload["status"] = "COMPLETED"
    except Exception as exc:
        payload["status"] = "FAILED_STOPPED"
        payload["fatal_error"] = f"{type(exc).__name__}:{exc}"
        _write(result_path, payload)
        raise
    payload["completed_at"] = datetime.now(UTC).isoformat()
    payload["api_call_count"] = len(payload["calls"])
    payload["product_complete_count"] = sum(bool(call["product_complete"]) for call in payload["calls"])
    payload["total_tokens"] = sum(int(call["usage"].get("total_tokens") or 0) for call in payload["calls"])
    payload["latency_total_ms"] = sum(call["latency_ms"] for call in payload["calls"])
    _write(result_path, payload)
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("candidate_canary", "remaining"), required=True)
    args = parser.parse_args()
    print(run(Path.cwd().resolve(), args.phase))


if __name__ == "__main__":
    main()
