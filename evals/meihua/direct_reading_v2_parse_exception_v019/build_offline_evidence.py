from __future__ import annotations
import hashlib,json
from pathlib import Path
import httpx
from openai import APIConnectionError,APIStatusError,APITimeoutError,AuthenticationError,RateLimitError
from abalo_iching.application.sites_parse_exception_classifier_v019 import ParseOrSchemaFailure,classify_parse_boundary_failure
OUTPUT=Path(__file__).with_name("offline_ledger.json")
REQ=httpx.Request("POST","https://fixture.invalid")
def fixtures():
    response=lambda status:httpx.Response(status,request=REQ)
    return [
      ("TIMEOUT",APITimeoutError(request=REQ),"TIMEOUT"),("CONNECTION",APIConnectionError(request=REQ),"CONNECTION"),
      ("AUTH",AuthenticationError("secret",response=response(401),body=None),"AUTHENTICATION"),
      ("RATE",RateLimitError("raw",response=response(429),body=None),"RATE_LIMIT"),
      ("API_STATUS",APIStatusError("question",response=response(400),body=None),"API_STATUS"),
      ("INVALID_RESPONSE",ParseOrSchemaFailure(),"INVALID_RESPONSE"),("UNKNOWN",RuntimeError("traceback"),"UNKNOWN_PROVIDER_ERROR")]
def build():
    rows=[]
    for case,failure,expected in fixtures():
      result=classify_parse_boundary_failure(failure=failure,stage="IN_PARSE_BOUNDARY")
      assert result["failure_code"]==expected
      rows.append({"case_id":case,**result,"provider_calls":0,"live_calls":0,"sdk_extractions":0,"v017_attempts":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0})
    before=classify_parse_boundary_failure(failure=RuntimeError(),stage="BEFORE_PARSE_BOUNDARY")
    rows.append({"case_id":"BEFORE_BOUNDARY",**before,"provider_calls":0,"live_calls":0,"sdk_extractions":0,"v017_attempts":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0})
    assert len(rows)==8 and sum(r["classification_attempts"] for r in rows)==8
    return {"stage_id":"DIRECT_READING_V2_PARSE_EXCEPTION_V019","status":"OFFLINE_EVIDENCE_COMPLETE","case_denominator":len(rows),"classified_count":len(rows),"safe_failure_count":0,"classification_attempts":8,"code_counts":{code:sum(r["failure_code"]==code for r in rows) for code in sorted({r["failure_code"] for r in rows})},"provider_calls":0,"live_calls":0,"real_provider_instantiated":False,"sdk_extractions":0,"v017_attempts":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0,"automatic_retries":0,"cases":rows,"deployment":False,"production":False,"default_replacement":False}
def main():
    data=build(); encoded=json.dumps(data,ensure_ascii=False,indent=2)+"\n";OUTPUT.write_text(encoded,encoding="utf-8",newline="\n");print(json.dumps({"sha256":hashlib.sha256(encoded.encode()).hexdigest().upper(),"cases":len(data["cases"])}))
if __name__=="__main__":main()
