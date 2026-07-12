import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts.run_meihua_live_eval_v001 import *
from scripts.run_meihua_live_eval_v001 import _request
from scripts.validate_meihua_live_eval_v001 import validate

def case(): return json.loads(DATASET.read_text("utf-8"))["cases"][0]
def draft_json(value, request, knowledge, synthesis):
    from abalo_iching.interpretation.evidence_references import build_evidence_reference_catalog
    catalog=build_evidence_reference_catalog(request,knowledge,synthesis)
    ref_by_id={item.canonical_evidence_id:item.evidence_ref for item in catalog.entries}
    payload=value.model_dump(mode="json")
    for claims in payload.values():
        for claim in claims:
            claim["evidence_refs"]=[ref_by_id[item] for item in claim.pop("evidence_ids")]
            claim.pop("narrative_kind"); claim.pop("epistemic_basis")
    return json.dumps(payload,ensure_ascii=False)
def test_zero_state_blocked_and_not_human_review(tmp_path):
    s=write_blocked(tmp_path); assert s["status"]=="BLOCKED_NO_API_KEY" and s["human_review_status"]=="NOT_AVAILABLE"
    assert validate(tmp_path)["validation"]=="NOT_PASS"
def test_started_is_written_before_provider(tmp_path):
    def p(c,e,n):
        assert read_jsonl(tmp_path/"attempt_journal.jsonl")[-1]["lifecycle_status"]=="STARTED"; return mock_provider(c,e,n)
    run_one(case(),"low",tmp_path,p,mock_validator)
def test_provider_and_validation_are_separate_events(tmp_path):
    run_one(case(),"low",tmp_path,mock_provider,mock_validator); states=[x["lifecycle_status"] for x in read_jsonl(tmp_path/"attempt_journal.jsonl")]
    assert states==["STARTED","PROVIDER_RETURNED","VALIDATION_PASSED"]
def test_validation_failure_and_repair_are_separate(tmp_path):
    run_one(case(),"low",tmp_path,mock_provider,lambda c,p: ["bad"] if len([x for x in read_jsonl(tmp_path/"attempt_journal.jsonl") if x["lifecycle_status"]=="STARTED"])==1 else [])
    starts=[x for x in read_jsonl(tmp_path/"attempt_journal.jsonl") if x["lifecycle_status"]=="STARTED"]; assert [x["attempt_number"] for x in starts]==[1,2]
def test_dangling_started_becomes_unknown_and_blocks(tmp_path):
    append_jsonl(tmp_path/"attempt_journal.jsonl",event_base("r",case(),"low",1))
    with pytest.raises(UnknownOutcomeError): run_one(case(),"low",tmp_path,mock_provider,mock_validator)
    assert "UNKNOWN_OUTCOME" in [x["lifecycle_status"] for x in read_jsonl(tmp_path/"attempt_journal.jsonl")]
def test_unknown_requires_explicit_confirmation(tmp_path):
    b=event_base("r",case(),"low",1); append_jsonl(tmp_path/"attempt_journal.jsonl",b); append_jsonl(tmp_path/"attempt_journal.jsonl",{**b,"lifecycle_status":"UNKNOWN_OUTCOME"})
    assert run_one(case(),"low",tmp_path,mock_provider,mock_validator,confirm_retry_unknown=True)["terminal_status"]=="VALIDATION_PASSED"
def test_completed_config_is_not_called_again(tmp_path):
    run_one(case(),"low",tmp_path,mock_provider,mock_validator)
    assert run_one(case(),"low",tmp_path,lambda *x: (_ for _ in()).throw(AssertionError()),mock_validator)["skipped"]=="ALREADY_TERMINAL"
@pytest.mark.parametrize("status",["PROVIDER_REFUSED","PROVIDER_INCOMPLETE","PROVIDER_ERROR"])
def test_provider_failures_recorded(tmp_path,status):
    class E(Exception): lifecycle_status=status
    r=run_one(case(),"low",tmp_path,lambda *x: (_ for _ in()).throw(E()),mock_validator); assert r["terminal_status"]==status
def test_parse_failure_recorded(tmp_path):
    r=run_one(case(),"low",tmp_path,lambda *x:{"parsed":None},mock_validator); assert r["terminal_status"]=="PARSE_FAILED"
def test_metrics_are_from_attempt_journal(tmp_path):
    run_one(case(),"low",tmp_path,mock_provider,mock_validator); m=metrics_from_journal(read_jsonl(tmp_path/"attempt_journal.jsonl")); assert m["total_api_attempts"]==1 and m["total_tokens"]==150

def test_metrics_use_nearest_rank_p95_and_explicit_expected_count():
    rows=[]
    for attempt,latency in ((1,8417),(2,6522)):
        base=event_base("metrics",case(),"low",attempt)
        rows.extend([base,{**base,"lifecycle_status":"PROVIDER_RETURNED","latency_ms":latency},{**base,"lifecycle_status":"VALIDATION_FAILED"}])
    metrics=metrics_from_journal(rows,expected_config_count=1)
    assert metrics["p50_latency_ms"]==7469.5
    assert metrics["p95_latency_ms"]==8417
    assert metrics["p95_latency_ms"]>=metrics["p50_latency_ms"]
    assert metrics["completed_config_count"]==1
    assert metrics["expected_config_count"]==1
    assert metrics["passed_config_count"]==0
def test_mock_full_16_is_complete(tmp_path):
    s=run_mock(tmp_path); assert s["status"]=="COMPLETED_PENDING_HUMAN_REVIEW" and s["metrics"]["total_api_attempts"]==16
    assert validate(tmp_path)["validation"]=="PASS"
def test_model_preflight_success_and_failure():
    class OK: models=type("M",(),{"retrieve":lambda self,x:{}})()
    class NO: models=type("M",(),{"retrieve":lambda self,x:(_ for _ in()).throw(PermissionError())})()
    assert model_preflight(OK())[0] is True and model_preflight(NO())[0] is False

@pytest.mark.parametrize(("name","code","expected"),[
    ("AuthenticationError",401,"AUTHENTICATION_FAILED"),
    ("NotFoundError",404,"MODEL_NOT_FOUND"),
    ("PermissionDeniedError",403,"MODEL_PERMISSION_DENIED"),
    ("APIConnectionError",None,"NETWORK_FAILED"),
    ("UnexpectedError",500,"UNKNOWN_PREFLIGHT_ERROR"),
])
def test_model_preflight_error_classification(name,code,expected):
    exc=type(name,(Exception,),{})("redacted")
    exc.status_code=code
    class Models:
        def retrieve(self,_): raise exc
    assert model_preflight(SimpleNamespace(models=Models()))==(False,expected)

def test_dry_run_is_distinct_from_missing_key(tmp_path):
    dry=write_dry_run(tmp_path/"dry")
    blocked=write_blocked(tmp_path/"blocked")
    assert dry["status"]=="NOT_STARTED" and dry["dry_run_completed"] is True
    assert blocked["status"]=="BLOCKED_NO_API_KEY" and "dry_run_completed" not in blocked

def test_repair_prompt_is_distinct_and_contains_first_error():
    from abalo_iching.interpretation.fake_provider import build_conservative_fake_output
    captured=[]
    class Responses:
        def parse(self,**kwargs):
            captured.append(kwargs)
            req=_request(case())
            from abalo_iching.interpretation.enums import KnowledgeAccessMode
            from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy,select_knowledge
            from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
            knowledge=select_knowledge(req.chart,policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW))
            parsed=build_conservative_fake_output(req,ConclusionSynthesizer().synthesize(req.chart,knowledge))
            data={"id":"resp-contract","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":draft_json(parsed,req,knowledge,ConclusionSynthesizer().synthesize(req.chart,knowledge))}]}],"usage":{"input_tokens":21,"output_tokens":13,"total_tokens":34},"incomplete_details":None}
            return SimpleNamespace(request_id="req-contract",http_response=SimpleNamespace(json=lambda:data))
    responses=Responses(); responses.with_raw_response=responses
    provider,validator=live_components(SimpleNamespace(responses=responses))
    first=provider(case(),"low",1,{})
    second=provider(case(),"low",2,{"validation_errors":["EVIDENCE_REFERENCE_NOT_ALLOWED"]})
    assert first["parsed_result"] is not None
    assert validator(case(),first["parsed_result"])==[]
    assert first["prompt_sha256"]!=second["prompt_sha256"]
    assert "EVIDENCE_REFERENCE_NOT_ALLOWED" in captured[1]["input"][1]["content"]
    assert captured[0]["reasoning"]["effort"]=="low"

def test_provider_returned_is_recovered_locally_without_new_call(tmp_path):
    c=case(); base=event_base("recovery",c,"low",1); envelope=mock_provider(c,"low",1)
    append_jsonl(tmp_path/"attempt_journal.jsonl",base)
    append_jsonl(tmp_path/"attempt_journal.jsonl",{**base,"finished_at":now(),"lifecycle_status":"PROVIDER_RETURNED",**envelope,"safe_parsed_result":envelope["parsed_result"]})
    calls=0
    def forbidden(*args):
        nonlocal calls; calls+=1; raise AssertionError("provider called")
    result=run_one(c,"low",tmp_path,forbidden,mock_validator)
    assert result["recovered_locally"] is True and calls==0 and result["terminal_status"]=="VALIDATION_PASSED"

def test_unrecoverable_returned_requires_explicit_confirmation(tmp_path):
    c=case(); base=event_base("unknown",c,"low",1)
    append_jsonl(tmp_path/"attempt_journal.jsonl",base)
    append_jsonl(tmp_path/"attempt_journal.jsonl",{**base,"finished_at":now(),"lifecycle_status":"PROVIDER_RETURNED","response_id":"resp-lost","safe_parsed_result":None})
    with pytest.raises(UnknownOutcomeError): run_one(c,"low",tmp_path,mock_provider,mock_validator)

@pytest.mark.parametrize(("status","refusal","terminal"),[("completed",True,"PROVIDER_REFUSED"),("incomplete",False,"PROVIDER_INCOMPLETE")])
def test_refusal_and_incomplete_preserve_response_metrics(tmp_path,status,refusal,terminal):
    def provider(c,e,n):
        return {**mock_provider(c,e,n),"response_id":"resp-meta","response_status":status,"refusal_present":refusal,"incomplete_details":"max_output_tokens" if status=="incomplete" else None,"parsed_result":None,"input_tokens":17,"output_tokens":5,"total_tokens":22,"latency_ms":19}
    result=run_one(case(),"low",tmp_path,provider,mock_validator)
    assert result["terminal_status"]==terminal and result["response_id"]=="resp-meta" and result["total_tokens"]==22 and result["latency_ms"]==19
    assert metrics_from_journal(read_jsonl(tmp_path/"attempt_journal.jsonl"))["total_tokens"]==22

def test_attempt_two_failure_restart_is_terminal(tmp_path):
    result=run_one(case(),"low",tmp_path,mock_provider,lambda c,p:["INVALID"])
    assert result["attempts_used"]==2 and result["terminal_status"]=="VALIDATION_FAILED"
    assert run_one(case(),"low",tmp_path,lambda *a: (_ for _ in()).throw(AssertionError()),mock_validator)=={"skipped":"ALREADY_TERMINAL"}

def test_raw_response_parse_failure_keeps_metadata_and_repairs(tmp_path):
    from abalo_iching.interpretation.fake_provider import build_conservative_fake_output
    calls=0
    class Responses:
        def parse(self,**kwargs):
            nonlocal calls; calls+=1
            if calls==1: text="not valid narrative json"
            else:
                req=_request(case())
                from abalo_iching.interpretation.enums import KnowledgeAccessMode
                from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy,select_knowledge
                from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
                k=select_knowledge(req.chart,policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW))
                synth=ConclusionSynthesizer().synthesize(req.chart,k); text=draft_json(build_conservative_fake_output(req,synth),req,k,synth)
            data={"id":f"resp-raw-{calls}","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":text}]}],"usage":{"input_tokens":40,"output_tokens":20,"total_tokens":60}}
            return SimpleNamespace(request_id=f"req-{calls}",http_response=SimpleNamespace(json=lambda:data))
    responses=Responses(); responses.with_raw_response=responses
    provider,validator=live_components(SimpleNamespace(responses=responses))
    result=run_one(case(),"low",tmp_path,provider,validator)
    journal=read_jsonl(tmp_path/"attempt_journal.jsonl")
    first_return=next(x for x in journal if x["attempt_number"]==1 and x["lifecycle_status"]=="PROVIDER_RETURNED")
    assert first_return["response_id"]=="resp-raw-1" and first_return["total_tokens"]==60 and first_return["latency_ms"]>=0
    assert [x["lifecycle_status"] for x in journal][:3]==["STARTED","PROVIDER_RETURNED","PARSE_FAILED"]
    assert result["attempts_used"]==2 and result["terminal_status"]=="VALIDATION_PASSED"

def test_recovery_validation_failure_calls_only_attempt_two(tmp_path):
    c=case(); base=event_base("recover-repair",c,"low",1); envelope=mock_provider(c,"low",1)
    append_jsonl(tmp_path/"attempt_journal.jsonl",base)
    append_jsonl(tmp_path/"attempt_journal.jsonl",{**base,"finished_at":now(),"lifecycle_status":"PROVIDER_RETURNED",**envelope,"safe_parsed_result":envelope["parsed_result"]})
    calls=[]
    def provider(c,e,n,context): calls.append((n,context)); return mock_provider(c,e,n,context)
    validations=0
    def validator(c,p):
        nonlocal validations; validations+=1; return ["FIRST_RECOVERY_ERROR"] if validations==1 else []
    result=run_one(c,"low",tmp_path,provider,validator)
    assert [n for n,_ in calls]==[2] and "FIRST_RECOVERY_ERROR" in calls[0][1]["validation_errors"]
    assert result["attempts_used"]==2 and len(read_jsonl(tmp_path/"config_results.jsonl"))==1

def test_smoke_is_fixed_and_full_run_resumes_without_duplicate(tmp_path):
    calls=[]
    def provider(c,e,n,context=None): calls.append((c["case_id"],e,n)); return mock_provider(c,e,n,context)
    summary=run_smoke(tmp_path,provider,mock_validator)
    assert summary["status"]=="SMOKE_COMPLETED" and calls==[("CASE-001","low",1)] and summary["human_review_status"]=="NOT_AVAILABLE"
    dataset=json.loads(DATASET.read_text("utf-8"))
    for c,e in build_plan(dataset): run_one(c,e,tmp_path,provider,mock_validator)
    assert calls.count(("CASE-001","low",1))==1
    assert len(read_jsonl(tmp_path/"config_results.jsonl"))==16
    assert metrics_from_journal(read_jsonl(tmp_path/"attempt_journal.jsonl"))["total_api_attempts"]==16

def test_successful_smoke_uses_one_config_denominator(tmp_path):
    summary=run_smoke(tmp_path,mock_provider,mock_validator)
    assert summary["metrics"]["final_pass_rate"]==1.0
    assert summary["metrics"]["expected_config_count"]==1
    assert summary["metrics"]["passed_config_count"]==1

def test_journal_and_result_carry_v3_audit_versions(tmp_path):
    result=run_one(case(),"low",tmp_path,mock_provider,mock_validator)
    started=read_jsonl(tmp_path/"attempt_journal.jsonl")[0]
    assert started["prompt_version"]=="MEIHUA_INTERPRETATION_PROMPT_V5"
    assert started["validator_contract_version"]=="MEIHUA_INTERPRETATION_VALIDATOR_V2"
    assert started["dataset_version"]=="MEIHUA_LIVE_EVAL_V001"
    assert result["validator_contract_version"]=="MEIHUA_INTERPRETATION_VALIDATOR_V2"
    assert result["dataset_version"]=="MEIHUA_LIVE_EVAL_V001"

@pytest.mark.parametrize("status",sorted(GLOBAL_FUSE))
def test_fatal_contract_and_access_errors_trigger_global_fuse(status):
    assert global_fuse_reason([{"terminal_status":status}])==status

def test_two_consecutive_provider_structure_errors_trigger_global_fuse():
    rows=[{"terminal_status":"PROVIDER_ERROR","validation_errors":["ResponseStructureError"]}]*2
    assert global_fuse_reason(rows)=="REPEATED_PROVIDER_STRUCTURE_ERROR"
def test_time_horizon_enters_request():
    assert _request(case()).time_horizon=="未来三个月"
