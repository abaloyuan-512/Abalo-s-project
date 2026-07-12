"""Build the Phase 2C final-preflight evidence set without network access."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_meihua_live_eval_v001 import (
    DATASET,
    _request,
    append_jsonl,
    atomic_json,
    event_base,
    global_fuse_reason,
    live_components,
    metrics_from_journal,
    mock_provider,
    mock_validator,
    model_preflight,
    now,
    read_jsonl,
    run_mock,
    run_one,
    run_smoke,
    write_blocked,
    write_dry_run,
)


def first_case() -> dict:
    return json.loads(DATASET.read_text("utf-8"))["cases"][0]


def contract_client(case: dict):
    from abalo_iching.interpretation.enums import KnowledgeAccessMode
    from abalo_iching.interpretation.fake_provider import build_conservative_fake_output
    from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, select_knowledge
    from abalo_iching.interpretation.synthesis import ConclusionSynthesizer

    request = _request(case)
    knowledge = select_knowledge(
        request.chart,
        policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
    )
    parsed = build_conservative_fake_output(
        request, ConclusionSynthesizer().synthesize(request.chart, knowledge)
    )

    class Responses:
        def parse(self, **_kwargs):
            data={"id":"resp-contract-offline","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":parsed.model_dump_json()}]}],"usage":{"input_tokens":31,"output_tokens":19,"total_tokens":50},"incomplete_details":None}
            return SimpleNamespace(request_id="req-contract-offline",http_response=SimpleNamespace(json=lambda:data))

    responses=Responses(); responses.with_raw_response=responses
    return SimpleNamespace(responses=responses)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    case = first_case()

    write_blocked(root / "01_no_key_zero_call")
    write_dry_run(root / "02_explicit_dry_run")
    run_mock(root / "03_mock_full_16")

    contract_out = root / "04_contract_mock"
    provider, validator = live_components(contract_client(case))
    contract = run_one(case, "low", contract_out, provider, validator)
    atomic_json(contract_out / "scenario_report.json", contract)

    repair_out = root / "05_repair_retry_mock"
    validation_calls = 0

    def repair_validator(_case, _parsed):
        nonlocal validation_calls
        validation_calls += 1
        return ["EVIDENCE_REFERENCE_NOT_ALLOWED"] if validation_calls == 1 else []

    repair = run_one(case, "low", repair_out, mock_provider, repair_validator)
    repair_events = read_jsonl(repair_out / "attempt_journal.jsonl")
    atomic_json(
        repair_out / "scenario_report.json",
        {
            "result": repair,
            "prompt_hashes": [
                event["prompt_sha256"]
                for event in repair_events
                if event["lifecycle_status"] == "PROVIDER_RETURNED"
            ],
        },
    )

    recovery_out = root / "06_local_recovery_mock"
    base = event_base("recovery", case, "low", 1)
    envelope = mock_provider(case, "low", 1)
    append_jsonl(recovery_out / "attempt_journal.jsonl", base)
    append_jsonl(
        recovery_out / "attempt_journal.jsonl",
        {
            **base,
            "finished_at": now(),
            "lifecycle_status": "PROVIDER_RETURNED",
            **envelope,
            "safe_parsed_result": envelope["parsed_result"],
        },
    )
    provider_calls = 0

    def forbidden_provider(*_args):
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("provider must not be called during local recovery")

    recovery = run_one(case, "low", recovery_out, forbidden_provider, mock_validator)
    atomic_json(
        recovery_out / "scenario_report.json",
        {"result": recovery, "new_provider_calls": provider_calls},
    )

    metadata_out = root / "07_refusal_incomplete_metrics"
    for effort, status, refusal in (
        ("low", "completed", True),
        ("medium", "incomplete", False),
    ):
        def metadata_provider(c, e, n, _context=None, status=status, refusal=refusal):
            return {
                **mock_provider(c, e, n),
                "response_id": f"resp-{status}-{e}",
                "response_status": status,
                "refusal_present": refusal,
                "incomplete_details": "max_output_tokens" if status == "incomplete" else None,
                "parsed_result": None,
                "input_tokens": 23,
                "output_tokens": 7,
                "total_tokens": 30,
                "latency_ms": 11,
            }
        run_one(case, effort, metadata_out, metadata_provider, mock_validator)
    atomic_json(
        metadata_out / "scenario_report.json",
        metrics_from_journal(read_jsonl(metadata_out / "attempt_journal.jsonl")),
    )

    restart_out = root / "08_attempt2_terminal_restart"
    first = run_one(case, "low", restart_out, mock_provider, lambda _c, _p: ["INVALID"])
    second = run_one(case, "low", restart_out, forbidden_provider, mock_validator)
    atomic_json(restart_out / "scenario_report.json", {"first": first, "restart": second})

    class Models:
        def __init__(self, error=None): self.error = error
        def retrieve(self, _model):
            if self.error: raise self.error
            return {}

    classes = {}
    for name, code in (
        ("AuthenticationError", 401), ("NotFoundError", 404),
        ("PermissionDeniedError", 403), ("APIConnectionError", None),
        ("UnexpectedError", 500),
    ):
        error = type(name, (Exception,), {})("redacted")
        error.status_code = code
        classes[name] = model_preflight(SimpleNamespace(models=Models(error)))[1]
    classes["success"] = model_preflight(SimpleNamespace(models=Models()))[1]
    atomic_json(root / "09_model_preflight_classification.json", classes)

    raw_out=root/"10_raw_response_parse_failure_mock"; valid_data=contract_client(case).responses.parse().http_response.json(); raw_calls=0
    class RawSequence:
        def parse(self,**_kwargs):
            nonlocal raw_calls; raw_calls+=1; data=dict(valid_data)
            if raw_calls==1: data={**data,"id":"resp-invalid-raw","output":[{"type":"message","content":[{"type":"output_text","text":"invalid-json"}]}]}
            return SimpleNamespace(request_id=f"req-raw-{raw_calls}",http_response=SimpleNamespace(json=lambda:data))
    raw_responses=RawSequence(); raw_responses.with_raw_response=raw_responses
    raw_provider,raw_validator=live_components(SimpleNamespace(responses=raw_responses))
    atomic_json(raw_out/"scenario_report.json",run_one(case,"low",raw_out,raw_provider,raw_validator))

    recovery_repair_out=root/"11_local_recovery_then_repair_mock"; base=event_base("recovery-repair",case,"low",1); envelope=mock_provider(case,"low",1)
    append_jsonl(recovery_repair_out/"attempt_journal.jsonl",base); append_jsonl(recovery_repair_out/"attempt_journal.jsonl",{**base,"finished_at":now(),"lifecycle_status":"PROVIDER_RETURNED",**envelope,"safe_parsed_result":envelope["parsed_result"]})
    validation_calls=0; attempt_calls=[]
    def recovery_validator(_c,_p):
        nonlocal validation_calls; validation_calls+=1; return ["RECOVERED_VALIDATION_ERROR"] if validation_calls==1 else []
    def recovery_provider(c,e,n,context=None): attempt_calls.append(n); return mock_provider(c,e,n,context)
    recovery_result=run_one(case,"low",recovery_repair_out,recovery_provider,recovery_validator)
    atomic_json(recovery_repair_out/"scenario_report.json",{"result":recovery_result,"provider_attempts":attempt_calls})

    smoke_out=root/"12_single_case_smoke_mock"; smoke_calls=[]
    def smoke_provider(c,e,n,context=None): smoke_calls.append([c["case_id"],e,n]); return mock_provider(c,e,n,context)
    atomic_json(smoke_out/"scenario_report.json",{"summary":run_smoke(smoke_out,smoke_provider,mock_validator),"calls":smoke_calls})

    resume_out=root/"13_smoke_then_full_resume_mock"; resume_calls=[]
    def resume_provider(c,e,n,context=None): resume_calls.append([c["case_id"],e,n]); return mock_provider(c,e,n,context)
    run_smoke(resume_out,resume_provider,mock_validator)
    for planned_case,effort in __import__("scripts.run_meihua_live_eval_v001",fromlist=["build_plan"]).build_plan(json.loads(DATASET.read_text("utf-8"))): run_one(planned_case,effort,resume_out,resume_provider,mock_validator)
    atomic_json(resume_out/"scenario_report.json",{"provider_calls":len(resume_calls),"case_001_low_calls":resume_calls.count(["CASE-001","low",1]),"config_results":len(read_jsonl(resume_out/"config_results.jsonl"))})

    fuse_out=root/"14_global_fuse_mock"; fuse_out.mkdir(parents=True,exist_ok=True); atomic_json(fuse_out/"scenario_report.json",{"authentication":global_fuse_reason([{"terminal_status":"AUTHENTICATION_FAILED"}]),"contract":global_fuse_reason([{"terminal_status":"API_PARAMETER_CONTRACT_ERROR"}]),"repeated_structure":global_fuse_reason([{"terminal_status":"PROVIDER_ERROR","validation_errors":["ResponseStructureError"]}]*2)})
    atomic_json(root / "FINAL_PREFLIGHT_SUMMARY.json", {"real_openai_calls": 0, "scenarios": 14})


if __name__ == "__main__":
    main()
