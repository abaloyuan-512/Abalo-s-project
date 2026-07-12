from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.run_meihua_live_eval_v001 import MODEL,TERMINAL,read_jsonl
EXPECTED={(f"CASE-{i:03d}",MODEL,"low") for i in range(1,13)}|{(f"CASE-{i:03d}",MODEL,"medium") for i in (2,5,6,8)}
def validate(path:Path)->dict:
    results=read_jsonl(path/"config_results.jsonl"); journal=read_jsonl(path/"attempt_journal.jsonl")
    if not results:
        return {"status":"NOT_RUN","complete":False,"validation":"NOT_PASS","human_review_status":"NOT_AVAILABLE","records":0}
    keys=[(x["case_id"],x["model"],x["reasoning_effort"]) for x in results]
    if len(keys)!=len(set(keys)): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"DUPLICATE_CONFIG"}
    if not set(keys)<=EXPECTED: return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"INVALID_DISTRIBUTION"}
    starts=[x for x in journal if x["lifecycle_status"]=="STARTED"]
    if len({x["attempt_id"] for x in starts})>32: return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"ATTEMPT_BUDGET"}
    if any(sum(1 for x in starts if (x["case_id"],x["model"],x["reasoning_effort"])==k)>2 for k in set(keys)): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"PER_CONFIG_ATTEMPT_BUDGET"}
    returned=[x for x in journal if x["lifecycle_status"]=="PROVIDER_RETURNED"]
    response_terminals=[x for x in journal if x["lifecycle_status"] in TERMINAL and x.get("response_id")]
    if len(returned)<len({x["attempt_id"] for x in response_terminals}): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"MISSING_PROVIDER_RETURNED"}
    if any(x["lifecycle_status"] in {"PROVIDER_REFUSED","PROVIDER_INCOMPLETE"} and x.get("response_id") and not x.get("mock_zero_usage_allowed") and not any((x.get(k) or 0)>0 for k in ("input_tokens","output_tokens","total_tokens")) for x in response_terminals): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"RESPONSE_USAGE_MISSING"}
    second_starts={x["attempt_id"] for x in starts if x["attempt_number"]==2}
    repair_returns={x["attempt_id"] for x in returned if x["attempt_number"]==2 and x.get("repair_prompt_version")}
    if repair_returns!=second_starts: return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"REPAIR_COUNT_MISMATCH"}
    required=("program_content_sha256","prompt_version","knowledge_version","canonical_version")
    if any(not all(x.get(f) for f in required) for x in results): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"MISSING_TRACE"}
    if any(x.get("should_charge") or x.get("persist_as_formal_report_allowed") or x.get("is_preview") is not True for x in results): return {"status":"FAILED","complete":False,"validation":"NOT_PASS","error":"SAFETY_INVARIANT"}
    complete=set(keys)==EXPECTED and all(x["terminal_status"] in TERMINAL for x in results)
    return {"status":"COMPLETED_PENDING_HUMAN_REVIEW" if complete else "PARTIAL","complete":complete,"validation":"PASS" if complete else "NOT_PASS","human_review_status":"AVAILABLE" if complete else "NOT_AVAILABLE","records":len(results)}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("output_dir",type=Path);a=p.parse_args();print(json.dumps(validate(a.output_dir)))
