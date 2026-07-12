"""Reliable, resumable Phase 2C runner. Live generation is always explicitly gated."""
from __future__ import annotations
import argparse, hashlib, inspect, json, os, statistics, uuid
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATASET=ROOT/"evals/meihua/live_eval_v001/dataset.json"
MODEL="gpt-5.6-terra"; EVAL_VERSION="MEIHUA_LIVE_EVAL_V001"
MAX_CASES=16; MAX_TOTAL_ATTEMPTS=32; MAX_OUTPUT_TOKENS=2000
TERMINAL={"VALIDATION_PASSED","VALIDATION_FAILED","PROVIDER_REFUSED","PROVIDER_INCOMPLETE","PROVIDER_ERROR","PARSE_FAILED","AUTHENTICATION_FAILED","MODEL_NOT_FOUND","MODEL_PERMISSION_DENIED","API_PARAMETER_CONTRACT_ERROR","STRUCTURED_OUTPUT_CONTRACT_ERROR"}
GLOBAL_FUSE={"AUTHENTICATION_FAILED","MODEL_NOT_FOUND","MODEL_PERMISSION_DENIED","API_PARAMETER_CONTRACT_ERROR","STRUCTURED_OUTPUT_CONTRACT_ERROR"}

class EvalStatus(StrEnum):
    NOT_STARTED="NOT_STARTED"; BLOCKED_NO_API_KEY="BLOCKED_NO_API_KEY"; BLOCKED_MODEL_UNAVAILABLE="BLOCKED_MODEL_UNAVAILABLE"; PARTIAL="PARTIAL"; COMPLETED_PENDING_HUMAN_REVIEW="COMPLETED_PENDING_HUMAN_REVIEW"; FAILED="FAILED"
class LiveEvalGuardError(RuntimeError): pass
class UnknownOutcomeError(RuntimeError): pass

def validate_output_dir(output_dir:Path)->None:
    resolved=output_dir.resolve(); root=ROOT.resolve()
    if resolved==root or root in resolved.parents: raise LiveEvalGuardError("OUTPUT_DIR_MUST_BE_OUTSIDE_GIT_REPOSITORY")

def validate_guards(*,confirm_live_eval:bool,confirm_max_attempts:int|None,output_dir:Path,key_present:bool,expected_max_attempts:int=32)->None:
    if not confirm_live_eval: raise LiveEvalGuardError("LIVE_EVAL_CONFIRMATION_REQUIRED")
    if confirm_max_attempts!=expected_max_attempts: raise LiveEvalGuardError(f"CONFIRM_MAX_ATTEMPTS_{expected_max_attempts}_REQUIRED")
    validate_output_dir(output_dir)
    if not key_present: raise LiveEvalGuardError("OPENAI_API_KEY_NOT_CONFIGURED")

def now(): return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
def append_jsonl(path:Path,row:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(row,ensure_ascii=False)+"\n"); f.flush(); os.fsync(f.fileno())
def read_jsonl(path:Path)->list[dict]:
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]
def atomic_json(path:Path,payload:dict)->None:
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,path)
def write_results(path:Path,rows:list[dict])->None:
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8"); os.replace(tmp,path)
def upsert_result(path:Path,row:dict)->None:
    rows=[x for x in read_jsonl(path) if key(x["case_id"],x["reasoning_effort"])!=key(row["case_id"],row["reasoning_effort"])]; rows.append(row); write_results(path,rows)

def build_plan(dataset:dict)->list[tuple[dict,str]]:
    by={x["case_id"]:x for x in dataset["cases"]}; plan=[(by[x],"low") for x in dataset["low_case_ids"]]+[(by[x],"medium") for x in dataset["medium_case_ids"]]
    if len(plan)!=16 or len(dataset["low_case_ids"])!=12 or len(dataset["medium_case_ids"])!=4: raise LiveEvalGuardError("INVALID_FIXED_PLAN")
    return plan
def key(case_id,effort): return (case_id,MODEL,effort)
def attempt_key(case_id,effort,n): return (case_id,MODEL,effort,n)

def reconcile_unknown(journal:Path)->set[tuple]:
    rows=read_jsonl(journal); by={}
    for r in rows: by.setdefault(tuple(r[x] for x in ("case_id","model","reasoning_effort","attempt_number")),[]).append(r)
    unknown=set()
    for k,events in by.items():
        states={x["lifecycle_status"] for x in events}
        if "STARTED" in states and "PROVIDER_RETURNED" not in states and not states.intersection(TERMINAL|{"UNKNOWN_OUTCOME"}):
            append_jsonl(journal,{**events[-1],"finished_at":now(),"lifecycle_status":"UNKNOWN_OUTCOME","provider_error_type":"INTERRUPTED_WITHOUT_TERMINAL_EVENT"}); unknown.add(k)
        elif "UNKNOWN_OUTCOME" in states: unknown.add(k)
    return unknown

def event_base(run_id,case,effort,attempt):
    return {"run_id":run_id,"attempt_id":f"{case['case_id']}:{MODEL}:{effort}:{attempt}","eval_version":EVAL_VERSION,"case_id":case["case_id"],"model":MODEL,"reasoning_effort":effort,"attempt_number":attempt,"started_at":now(),"finished_at":None,"lifecycle_status":"STARTED","response_id":None,"provider_error_type":None,"validation_errors":[],"input_tokens":0,"output_tokens":0,"total_tokens":0,"latency_ms":0}

def _final(case,effort,n,terminal,envelope,errors):
    return {"case_id":case["case_id"],"model":MODEL,"reasoning_effort":effort,"terminal_status":terminal,"attempts_used":n,"validation_errors":errors,"response_id":envelope.get("response_id"),"request_id":envelope.get("request_id"),"input_tokens":envelope.get("input_tokens",0),"output_tokens":envelope.get("output_tokens",0),"total_tokens":envelope.get("total_tokens",0),"latency_ms":envelope.get("latency_ms",0),"raw_output_text_sha256":envelope.get("raw_output_text_sha256"),"parse_error_type":envelope.get("parse_error_type"),"parse_error_safe_summary":envelope.get("parse_error_safe_summary"),"is_preview":True,"should_charge":False,"persist_as_formal_report_allowed":False,"program_content_sha256":envelope.get("program_content_sha256","unavailable"),"prompt_version":envelope.get("prompt_version","MEIHUA_INTERPRETATION_PROMPT_V1"),"repair_prompt_version":envelope.get("repair_prompt_version"),"prompt_sha256":envelope.get("prompt_sha256"),"knowledge_version":"MEIHUA_INTERPRETATION_KNOWLEDGE_V1","canonical_version":"MEIHUA_CANONICAL_TEXTS_V1","ai_narrative":envelope.get("parsed_result")}

def global_fuse_reason(recent_results:list[dict])->str|None:
    if recent_results and recent_results[-1].get("terminal_status") in GLOBAL_FUSE: return recent_results[-1]["terminal_status"]
    structural={"ResponseValidationError","ResponseStructureError","STRUCTURED_OUTPUT_CONTRACT_ERROR"}
    if len(recent_results)>=2 and all(x.get("terminal_status")=="PROVIDER_ERROR" and any(e in structural for e in x.get("validation_errors",[])) for x in recent_results[-2:]): return "REPEATED_PROVIDER_STRUCTURE_ERROR"
    return None

def parse_ai_narrative(raw_text:str)->dict:
    from abalo_iching.interpretation.models import AINarrativeContent
    return AINarrativeContent.model_validate_json(raw_text).model_dump(mode="json")

def _raw_path(out:Path,case:dict,effort:str,n:int)->Path:
    return out/"raw_responses"/f"{case['case_id']}_{effort}_{n}.json"

def _recover_returned(case,effort,out,journal,results,validator):
    rows=read_jsonl(journal); groups={}
    for r in rows:
        if key(r["case_id"],r["reasoning_effort"])==key(case["case_id"],effort): groups.setdefault(r["attempt_number"],[]).append(r)
    for n,events in sorted(groups.items()):
        states={x["lifecycle_status"] for x in events}
        returned=next((x for x in reversed(events) if x["lifecycle_status"]=="PROVIDER_RETURNED"),None)
        if returned and not states.intersection(TERMINAL):
            parsed=returned.get("safe_parsed_result"); parse_error=None
            if parsed is None and returned.get("raw_response_file"):
                raw_file=out/returned["raw_response_file"]
                if raw_file.is_file():
                    raw_text=json.loads(raw_file.read_text("utf-8")).get("output_text")
                    if raw_text:
                        try: parsed=parse_ai_narrative(raw_text)
                        except Exception as exc: parse_error=type(exc).__name__
            if returned.get("refusal_present"):
                terminal="PROVIDER_REFUSED"; errors=[]
            elif returned.get("response_status")=="incomplete":
                terminal="PROVIDER_INCOMPLETE"; errors=[str(returned.get("incomplete_details") or "incomplete")]
            elif parsed is None and parse_error is None:
                append_jsonl(journal,{**returned,"finished_at":now(),"lifecycle_status":"UNKNOWN_OUTCOME","provider_error_type":"RESPONSE_RETURNED_WITHOUT_RECOVERABLE_LOCAL_RESULT","local_recovery":True})
                return {"unknown_outcome":True}
            elif parse_error:
                terminal="PARSE_FAILED"; errors=[parse_error]
            else:
                errors=list(validator(case,parsed)); terminal="VALIDATION_PASSED" if not errors else "VALIDATION_FAILED"
            append_jsonl(journal,{**returned,"finished_at":now(),"lifecycle_status":terminal,"validation_errors":errors,"local_recovery":True})
            if n==1 and terminal in {"PARSE_FAILED","VALIDATION_FAILED"}:
                return {"resume_attempt":2,"repair_context":{"parse_error_type":parse_error,"validation_errors":errors},"recovered_locally":True}
            returned={**returned,"parsed_result":parsed}; final=_final(case,effort,n,terminal,returned,errors); upsert_result(results,final); return {**final,"recovered_locally":True}
    return None

def run_one(case,effort,out:Path,provider,validator,*,confirm_retry_unknown=False,run_id=None)->dict:
    journal=out/"attempt_journal.jsonl"; results=out/"config_results.jsonl"; run_id=run_id or str(uuid.uuid4())
    existing=read_jsonl(results)
    if any(key(x["case_id"],x["reasoning_effort"])==key(case["case_id"],effort) for x in existing): return {"skipped":"ALREADY_TERMINAL"}
    recovered=_recover_returned(case,effort,out,journal,results,validator)
    if recovered and recovered.get("unknown_outcome") and not confirm_retry_unknown: raise UnknownOutcomeError("UNKNOWN_OUTCOME_REQUIRES_EXPLICIT_CONFIRMATION")
    if recovered and not recovered.get("unknown_outcome") and not recovered.get("resume_attempt"): return recovered
    unknown=reconcile_unknown(journal)
    if any(x[:3]==key(case["case_id"],effort) for x in unknown) and not confirm_retry_unknown: raise UnknownOutcomeError("UNKNOWN_OUTCOME_REQUIRES_EXPLICIT_CONFIRMATION")
    attempts={r["attempt_number"] for r in read_jsonl(journal) if key(r["case_id"],r["reasoning_effort"])==key(case["case_id"],effort) and r["lifecycle_status"]=="STARTED"}
    start=recovered.get("resume_attempt") if recovered and recovered.get("resume_attempt") else max(attempts,default=0)+1
    if start>2: return {"skipped":"ALREADY_TERMINAL"}
    repair_context=recovered.get("repair_context",{}) if recovered else {}
    for n in range(start,3):
        if len({r["attempt_id"] for r in read_jsonl(journal) if r["lifecycle_status"]=="STARTED"})>=MAX_TOTAL_ATTEMPTS: raise LiveEvalGuardError("MAX_TOTAL_ATTEMPTS_REACHED")
        base=event_base(run_id,case,effort,n); append_jsonl(journal,base)
        try:
            parameter_count=len(inspect.signature(provider).parameters)
            returned=provider(case,effort,n,repair_context) if parameter_count>=4 else provider(case,effort,n)
        except Exception as exc:
            name=type(exc).__name__; status=getattr(exc,"lifecycle_status",None)
            if status is None:
                if "Authentication" in name: status="AUTHENTICATION_FAILED"
                elif "Permission" in name: status="MODEL_PERMISSION_DENIED"
                elif isinstance(exc,TypeError): status="API_PARAMETER_CONTRACT_ERROR"
                else: status="PROVIDER_ERROR"
            append_jsonl(journal,{**base,"finished_at":now(),"lifecycle_status":status,"provider_error_type":type(exc).__name__})
            final=_final(case,effort,n,status,{},[type(exc).__name__]); upsert_result(results,final); return final
        raw_payload=returned.pop("_raw_response_json",None); raw_text=returned.pop("_raw_output_text",None)
        if raw_payload is not None:
            raw_file=_raw_path(out,case,effort,n); raw_file.parent.mkdir(parents=True,exist_ok=True)
            atomic_json(raw_file,{"response":raw_payload,"output_text":raw_text})
            returned["raw_response_file"]=raw_file.relative_to(out).as_posix()
        if raw_text is not None: returned["raw_output_text_sha256"]=hashlib.sha256(raw_text.encode()).hexdigest()
        ret={**base,"finished_at":now(),"lifecycle_status":"PROVIDER_RETURNED",**returned}; ret["safe_parsed_result"]=returned.get("parsed_result",returned.get("parsed")); append_jsonl(journal,ret)
        if returned.get("refusal_present"):
            terminal="PROVIDER_REFUSED"; errors=[]; append_jsonl(journal,{**ret,"lifecycle_status":terminal}); final=_final(case,effort,n,terminal,ret,errors); upsert_result(results,final); return final
        if returned.get("response_status")=="incomplete":
            terminal="PROVIDER_INCOMPLETE"; errors=[str(returned.get("incomplete_details") or "incomplete")]; append_jsonl(journal,{**ret,"lifecycle_status":terminal,"validation_errors":errors}); final=_final(case,effort,n,terminal,ret,errors); upsert_result(results,final); return final
        if ret["safe_parsed_result"] is None and raw_text:
            try: ret["safe_parsed_result"]=parse_ai_narrative(raw_text)
            except Exception as exc:
                ret["parse_error_type"]=type(exc).__name__; ret["parse_error_safe_summary"]="AINarrativeContent local validation failed"
        if ret["safe_parsed_result"] is None:
            terminal="PARSE_FAILED"; errors=[ret.get("parse_error_type") or "EMPTY_OUTPUT"]; append_jsonl(journal,{**ret,"lifecycle_status":terminal,"provider_error_type":errors[0]})
            if n<2: repair_context={"parse_error_type":errors[0],"validation_errors":errors}; continue
        else:
            ret["parsed_result"]=ret["safe_parsed_result"]
            errors=list(validator(case,ret["safe_parsed_result"]))
            terminal="VALIDATION_PASSED" if not errors else "VALIDATION_FAILED"
            append_jsonl(journal,{**ret,"lifecycle_status":terminal,"validation_errors":errors})
            if errors and n<2: repair_context={"validation_errors":errors}; continue
        final=_final(case,effort,n,terminal,ret,errors); upsert_result(results,final); return final
    return {"skipped":"ALREADY_TERMINAL"}

def metrics_from_journal(rows):
    starts=[r for r in rows if r["lifecycle_status"]=="STARTED"]; ids={r["attempt_id"] for r in starts}; returned={r["attempt_id"]:r for r in rows if r["lifecycle_status"]=="PROVIDER_RETURNED"}; terminals=[r for r in rows if r["lifecycle_status"] in TERMINAL]
    lats=[x.get("latency_ms",0) for x in returned.values()]; passed={r["attempt_id"] for r in terminals if r["lifecycle_status"]=="VALIDATION_PASSED"}
    first={r["attempt_id"] for r in starts if r["attempt_number"]==1}; configs={tuple(r[x] for x in ("case_id","model","reasoning_effort")) for r in terminals if r["lifecycle_status"]=="VALIDATION_PASSED"}
    return {"base_calls":len(first),"repair_retries":len(ids-first),"total_api_attempts":len(ids),"first_pass_rate":len(passed&first)/len(first) if first else None,"final_pass_rate":len(configs)/16,"provider_refusals":sum(r["lifecycle_status"]=="PROVIDER_REFUSED" for r in terminals),"incomplete":sum(r["lifecycle_status"]=="PROVIDER_INCOMPLETE" for r in terminals),"parse_failures":sum(r["lifecycle_status"]=="PARSE_FAILED" for r in terminals),"validation_failures":sum(r["lifecycle_status"]=="VALIDATION_FAILED" for r in terminals),"timeouts":sum("Timeout" in str(r.get("provider_error_type")) for r in terminals),"rate_limits":sum("RateLimit" in str(r.get("provider_error_type")) for r in terminals),"connection_errors":sum("Connection" in str(r.get("provider_error_type")) for r in terminals),"authentication_failures":sum("Authentication" in str(r.get("provider_error_type")) for r in terminals),"input_tokens":sum(x.get("input_tokens",0) or 0 for x in returned.values()),"output_tokens":sum(x.get("output_tokens",0) or 0 for x in returned.values()),"total_tokens":sum(x.get("total_tokens",0) or 0 for x in returned.values()),"average_latency_ms":statistics.mean(lats) if lats else 0,"p50_latency_ms":statistics.median(lats) if lats else 0,"p95_latency_ms":sorted(lats)[max(0,int(len(lats)*.95)-1)] if lats else 0}

def summarize(rows): return metrics_from_journal(rows)

def state_for(results,key_present=True,model_accessible=True):
    if not results: return EvalStatus.BLOCKED_NO_API_KEY if not key_present else EvalStatus.NOT_STARTED
    passed={key(x["case_id"],x["reasoning_effort"]) for x in results if x["terminal_status"] in TERMINAL}
    if len(passed)==16: return EvalStatus.COMPLETED_PENDING_HUMAN_REVIEW
    return EvalStatus.PARTIAL

def model_preflight(client)->tuple[bool,str]:
    try: client.models.retrieve(MODEL); return True,"MODEL_ACCESSIBLE"
    except Exception as exc:
        name=type(exc).__name__; code=getattr(exc,"status_code",None)
        if name=="AuthenticationError": status="AUTHENTICATION_FAILED"
        elif code==404: status="MODEL_NOT_FOUND"
        elif code==403: status="MODEL_PERMISSION_DENIED"
        elif "Connection" in name or "Timeout" in name: status="NETWORK_FAILED"
        else: status="UNKNOWN_PREFLIGHT_ERROR"
        return False,status

def live_components(client):
    from time import perf_counter
    from abalo_iching.interpretation.enums import KnowledgeAccessMode
    from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy,select_knowledge
    from abalo_iching.interpretation.models import AINarrativeContent
    from abalo_iching.interpretation.prompt_builder import PromptBuilder
    from abalo_iching.interpretation.renderer import ProgramInterpretationRenderer
    from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
    from abalo_iching.interpretation.validators import InterpretationValidator
    from abalo_iching.interpretation.exceptions import InterpretationValidationError
    cache={}
    def context(case):
        if case["case_id"] not in cache:
            req=_request(case); policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW); knowledge=select_knowledge(req.chart,policy=policy); synthesis=ConclusionSynthesizer().synthesize(req.chart,knowledge); program=ProgramInterpretationRenderer().render(req,knowledge,synthesis); cache[case["case_id"]]=(req,knowledge,synthesis,program)
        return cache[case["case_id"]]
    def provider(case,effort,n,repair_context=None):
        req,knowledge,synthesis,program=context(case); repair_context=repair_context or {}; repair_errors=list(repair_context.get("validation_errors",[])); prompt=PromptBuilder().build(req,knowledge,synthesis,repair_errors=repair_errors if n==2 else None); repair_version="MEIHUA_REPAIR_PROMPT_V1" if n==2 else None
        material=prompt.user_payload_json
        if n==2: material += "\nREPAIR_ERROR_TYPE="+str(repair_context.get("parse_error_type"))+"\nRepair only AI narrative fields. Do not generate conclusion, chart facts, timing, support/blocking, or program summary."
        prompt_hash=hashlib.sha256(material.encode()).hexdigest(); started=perf_counter()
        raw=client.responses.with_raw_response.parse(model=MODEL,input=[{"role":"system","content":prompt.system_prompt},{"role":"user","content":material}],text_format=AINarrativeContent,reasoning={"effort":effort},max_output_tokens=MAX_OUTPUT_TOKENS,tools=[],store=False)
        data=raw.http_response.json(); usage=data.get("usage") or {}; output_text=None; refusal=None
        for item in data.get("output") or []:
            for content in item.get("content") or []:
                if content.get("type")=="output_text": output_text=content.get("text")
                elif content.get("type")=="refusal": refusal=content.get("refusal") or "refusal"
        return {"response_id":data.get("id"),"response_status":data.get("status"),"request_id":getattr(raw,"request_id",None),"incomplete_details":data.get("incomplete_details"),"refusal_present":refusal is not None,"refusal_category":"SAFE_REFUSAL" if refusal else None,"input_tokens":int(usage.get("input_tokens",0) or 0),"output_tokens":int(usage.get("output_tokens",0) or 0),"total_tokens":int(usage.get("total_tokens",0) or 0),"latency_ms":int((perf_counter()-started)*1000),"parsed_result":None,"parse_error_type":None,"parse_error_safe_summary":None,"program_content_sha256":hashlib.sha256(program.model_dump_json().encode()).hexdigest(),"prompt_version":prompt.prompt_version,"repair_prompt_version":repair_version,"prompt_sha256":prompt_hash,"_raw_response_json":data,"_raw_output_text":output_text}
    def validator(case,parsed):
        req,knowledge,synthesis,_=context(case)
        try: InterpretationValidator().validate(parsed,req,knowledge,synthesis); return []
        except InterpretationValidationError as exc: return list(exc.errors)
    return provider,validator

def mock_provider(case,effort,n,repair_context=None):
    material=f"{case['case_id']}|{effort}|attempt={n}|errors={json.dumps(repair_context or {},sort_keys=True)}"
    return {"response_id":f"mock-{case['case_id']}-{effort}-{n}","response_status":"completed","refusal_present":False,"parsed_result":{"safe":"synthetic mock narrative"},"input_tokens":100,"output_tokens":50,"total_tokens":150,"latency_ms":10,"program_content_sha256":hashlib.sha256(case["case_id"].encode()).hexdigest(),"prompt_version":"MEIHUA_INTERPRETATION_PROMPT_V1","repair_prompt_version":"MEIHUA_REPAIR_PROMPT_V1" if n==2 else None,"prompt_sha256":hashlib.sha256(material.encode()).hexdigest()}
def mock_validator(case,parsed): return []
def run_mock(out:Path):
    validate_output_dir(out); out.mkdir(parents=True,exist_ok=True); dataset=json.loads(DATASET.read_text("utf-8"))
    for case,effort in build_plan(dataset): run_one(case,effort,out,mock_provider,mock_validator,run_id="MOCK-RUN-V001")
    results=read_jsonl(out/"config_results.jsonl"); summary={"status":state_for(results).value,"human_review_status":"AVAILABLE","metrics":metrics_from_journal(read_jsonl(out/"attempt_journal.jsonl"))}; atomic_json(out/"summary.json",summary); return summary

def write_blocked(out:Path):
    validate_output_dir(out); out.mkdir(parents=True,exist_ok=True); (out/"attempt_journal.jsonl").write_text("",encoding="utf-8"); (out/"config_results.jsonl").write_text("",encoding="utf-8"); summary={"status":EvalStatus.BLOCKED_NO_API_KEY.value,"human_review_status":"NOT_AVAILABLE","metrics":metrics_from_journal([])}; atomic_json(out/"summary.json",summary); return summary
def write_dry_run(out:Path):
    validate_output_dir(out); out.mkdir(parents=True,exist_ok=True); (out/"attempt_journal.jsonl").write_text("",encoding="utf-8"); (out/"config_results.jsonl").write_text("",encoding="utf-8"); summary={"status":EvalStatus.NOT_STARTED.value,"dry_run_completed":True,"human_review_status":"NOT_AVAILABLE","metrics":metrics_from_journal([])}; atomic_json(out/"summary.json",summary); return summary

def run_smoke(out:Path,provider,validator)->dict:
    validate_output_dir(out); dataset=json.loads(DATASET.read_text("utf-8")); case=next(x for x in dataset["cases"] if x["case_id"]=="CASE-001")
    result=run_one(case,"low",out,provider,validator,run_id="LIVE-SMOKE-CASE-001")
    results=read_jsonl(out/"config_results.jsonl"); summary={"status":"SMOKE_COMPLETED" if result.get("terminal_status")=="VALIDATION_PASSED" else "FAILED","human_review_status":"NOT_AVAILABLE","smoke_case":"CASE-001","reasoning_effort":"low","metrics":metrics_from_journal(read_jsonl(out/"attempt_journal.jsonl"))}; atomic_json(out/"summary.json",summary); return summary

def _request(case):
    from abalo_iching import MeihuaInput,cast_meihua
    from abalo_iching.interpretation.enums import QuestionDomain
    from abalo_iching.interpretation.models import InterpretationRequest
    domain={"职业":QuestionDomain.CAREER,"关系":QuestionDomain.RELATIONSHIP,"合作":QuestionDomain.FINANCE_COOPERATION}[case["domain"]]
    chart=cast_meihua(MeihuaInput(*case["numbers"],datetime(2026,7,12,12,tzinfo=ZoneInfo("Asia/Shanghai")),"Asia/Shanghai"))
    return InterpretationRequest(question_id=case["case_id"],question_domain=domain,normalized_question=case["question"],decision_goal=case["decision_goal"],time_horizon=case["time_horizon"],real_world_context=case["real_world_context"],chart=chart)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--dry-run",action="store_true"); p.add_argument("--mock",action="store_true"); p.add_argument("--live-smoke-case",choices=["CASE-001"]); p.add_argument("--confirm-live-eval",action="store_true"); p.add_argument("--confirm-max-attempts",type=int); p.add_argument("--confirm-retry-unknown-outcome",action="store_true"); a=p.parse_args()
    validate_output_dir(a.output_dir)
    if a.mock: print(json.dumps(run_mock(a.output_dir),ensure_ascii=False)); return
    if a.dry_run: print(json.dumps(write_dry_run(a.output_dir),ensure_ascii=False)); return
    if not os.getenv("OPENAI_API_KEY"): print(json.dumps(write_blocked(a.output_dir),ensure_ascii=False)); return
    expected=2 if a.live_smoke_case else 32
    validate_guards(confirm_live_eval=a.confirm_live_eval,confirm_max_attempts=a.confirm_max_attempts,output_dir=a.output_dir,key_present=True,expected_max_attempts=expected)
    from openai import OpenAI
    client=OpenAI(); accessible,message=model_preflight(client); print(message)
    if not accessible:
        a.output_dir.mkdir(parents=True,exist_ok=True); atomic_json(a.output_dir/"summary.json",{"status":EvalStatus.BLOCKED_MODEL_UNAVAILABLE.value,"human_review_status":"NOT_AVAILABLE","responses_generation_calls":0}); return
    provider,validator=live_components(client)
    if a.live_smoke_case: print(json.dumps(run_smoke(a.output_dir,provider,validator),ensure_ascii=False)); return
    dataset=json.loads(DATASET.read_text("utf-8")); a.output_dir.mkdir(parents=True,exist_ok=True); recent=[]
    for case,effort in build_plan(dataset):
        try:
            result=run_one(case,effort,a.output_dir,provider,validator,confirm_retry_unknown=a.confirm_retry_unknown_outcome)
            if result.get("terminal_status"): recent.append(result)
            if global_fuse_reason(recent): break
        except UnknownOutcomeError: raise
    results=read_jsonl(a.output_dir/"config_results.jsonl"); summary={"status":state_for(results).value,"human_review_status":"AVAILABLE" if len(results)==16 else "NOT_AVAILABLE","metrics":metrics_from_journal(read_jsonl(a.output_dir/"attempt_journal.jsonl"))}; atomic_json(a.output_dir/"summary.json",summary); print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__": main()
