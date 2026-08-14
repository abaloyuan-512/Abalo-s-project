"""Run the frozen direct-reading comparison without production integration."""

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


RESEARCH_REL = Path("evals/meihua/direct_reading_v2_research_v001")
PROMPTS_REL = Path("prompts/prompt_package.json")
CASES_REL = Path("cases/cases.json")
MAX_SUCCESSFUL_CALLS = 18


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _render_chart(case: dict[str, Any]) -> str:
    chart = case["chart"]
    lines = [
        f"本卦：第{chart['base_hexagram']['king_wen_number']}卦 {chart['base_hexagram']['name']}（上卦{chart['base_hexagram']['upper_trigram']}，下卦{chart['base_hexagram']['lower_trigram']}）",
        f"互卦：第{chart['mutual_hexagram']['king_wen_number']}卦 {chart['mutual_hexagram']['name']}",
        f"动爻：{chart['moving_line']['name']}，爻辞：{chart['moving_line']['canonical_line_text']}",
        f"变卦：第{chart['changed_hexagram']['king_wen_number']}卦 {chart['changed_hexagram']['name']}（上卦{chart['changed_hexagram']['upper_trigram']}，下卦{chart['changed_hexagram']['lower_trigram']}）",
    ]
    return "\n".join(lines)


def _expand_questions(chart_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for chart_case in chart_cases:
        for question in chart_case["questions"]:
            expanded.append(
                {
                    "case_id": question["question_id"],
                    "pair_id": chart_case["case_id"] if len(chart_case["questions"]) == 2 else None,
                    "question_text": question["question_text"],
                    "numbers": chart_case["numbers"],
                    "numbers_semantics": chart_case["numbers_semantics"],
                    "chart": chart_case["chart"],
                    "versions": chart_case["versions"],
                }
            )
    return expanded


def _request_messages(
    case: dict[str, Any], prompts: dict[str, Any], arm: Literal["REFERENCE", "CANDIDATE"]
) -> list[dict[str, str]]:
    chart_packet = _render_chart(case)
    values = {"question": case["question_text"], "chart_packet": chart_packet}
    if arm == "REFERENCE":
        return [
            {
                "role": "user",
                "content": prompts["reference_user_template"].format(**values),
            }
        ]
    return [
        {"role": "system", "content": prompts["candidate_system"]},
        {
            "role": "user",
            "content": prompts["candidate_user_template"].format(**values),
        },
    ]


def _usage(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


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
    if not output_text:
        raise RuntimeError(f"{case['case_id']} {arm} returned empty output")
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
        "usage": _usage(response),
        "output_text": output_text,
        "status": "SUCCESS",
    }


def _validate_assets(research: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prompts_path = research / PROMPTS_REL
    cases_path = research / CASES_REL
    runner_path = research / "experiment/run_direct_reading_research.py"
    rubric_path = research / "rubric.md"
    checks = {
        "prompts_sha256": _sha_file(prompts_path),
        "cases_sha256": _sha_file(cases_path),
        "runner_sha256": _sha_file(runner_path),
        "rubric_sha256": _sha_file(rubric_path),
    }
    for key, actual in checks.items():
        if str(manifest.get(key, "")).upper() != actual:
            raise RuntimeError(f"frozen asset mismatch: {key}")
    prompts = _load(prompts_path)
    cases_document = _load(cases_path)
    if cases_document.get("case_count") != 5 or cases_document.get("question_count") != 9:
        raise RuntimeError("research requires five frozen charts and nine questions")
    cases = _expand_questions(cases_document["cases"])
    if len(cases) != 9 or len({case["case_id"] for case in cases}) != 9:
        raise RuntimeError("research requires exactly nine unique questions")
    if cases[0]["case_id"] != "DR-01-Q1":
        raise RuntimeError("DR-01 must remain the compatibility canary")
    if prompts["reference_model"] != manifest["chat_reference_model"]:
        raise RuntimeError("reference model mismatch")
    if prompts["candidate_model"] != manifest["candidate_model"]:
        raise RuntimeError("candidate model mismatch")
    if int(manifest["max_successful_model_calls"]) != MAX_SUCCESSFUL_CALLS:
        raise RuntimeError("call budget mismatch")
    return prompts, cases


def run(repo_root: Path, phase: Literal["canary", "remaining"]) -> Path:
    research = repo_root / RESEARCH_REL
    manifest = _load(research / "manifest.json")
    prompts, cases = _validate_assets(research, manifest)
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable")
    runs_dir = research / "runs"
    if phase == "remaining":
        canary_path = runs_dir / "canary_run.json"
        if not canary_path.exists():
            raise RuntimeError("remaining phase requires a completed canary")
        canary = _load(canary_path)
        if (
            canary.get("status") != "COMPLETED"
            or canary.get("successful_call_count") != 2
            or canary.get("prompts_sha256") != manifest["prompts_sha256"]
            or canary.get("cases_sha256") != manifest["cases_sha256"]
        ):
            raise RuntimeError("canary evidence is incomplete or differs from frozen assets")
    marker = runs_dir / f"{phase}_started.json"
    result_path = runs_dir / f"{phase}_run.json"
    _write_exclusive(
        marker,
        {
            "phase": phase,
            "started_at": datetime.now(UTC).isoformat(),
            "automatic_retries": 0,
            "successful_call_budget": MAX_SUCCESSFUL_CALLS,
        },
    )
    selected = cases[:1] if phase == "canary" else cases[1:]
    expected_calls = 2 if phase == "canary" else 16
    payload: dict[str, Any] = {
        "phase": phase,
        "status": "IN_PROGRESS",
        "expected_call_count": expected_calls,
        "automatic_retries": 0,
        "prompts_sha256": manifest["prompts_sha256"],
        "cases_sha256": manifest["cases_sha256"],
        "calls": [],
    }
    _write(result_path, payload)
    client = OpenAI(timeout=120.0, max_retries=0)
    try:
        for case in selected:
            for arm in ("REFERENCE", "CANDIDATE"):
                record = _call(client, case=case, prompts=prompts, arm=arm)
                payload["calls"].append(record)
                _write(result_path, payload)
        payload["status"] = "COMPLETED"
    except Exception as exc:
        payload["status"] = "FAILED_STOPPED"
        payload["fatal_error"] = f"{type(exc).__name__}:{exc}"
        _write(result_path, payload)
        raise
    payload["completed_at"] = datetime.now(UTC).isoformat()
    payload["successful_call_count"] = len(payload["calls"])
    payload["total_tokens"] = sum(
        int(call["usage"].get("total_tokens") or 0) for call in payload["calls"]
    )
    payload["latency_total_ms"] = sum(call["latency_ms"] for call in payload["calls"])
    _write(result_path, payload)
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("canary", "remaining"), required=True)
    args = parser.parse_args()
    print(run(Path.cwd().resolve(), args.phase))


if __name__ == "__main__":
    main()
