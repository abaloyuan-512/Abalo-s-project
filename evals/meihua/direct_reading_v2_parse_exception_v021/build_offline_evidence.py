from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import httpx
from openai import APIConnectionError,APITimeoutError,AuthenticationError,BadRequestError,InternalServerError,RateLimitError
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/"src"))
from abalo_iching.application.sites_parse_exception_classifier_v021 import ParseOrSchemaFailure,classify_parse_boundary_failure
OUT=Path(__file__).with_name("offline_ledger.json");REQ=httpx.Request("POST","https://fixture.invalid")
def r(status): x=httpx.Response(200,request=REQ);x.status_code=status;return x
def fixtures(): return [
 ("TIMEOUT",APITimeoutError(request=REQ),"TIMEOUT","IN_PARSE_BOUNDARY"),("CONNECTION",APIConnectionError(request=REQ),"CONNECTION","IN_PARSE_BOUNDARY"),
 ("AUTH",AuthenticationError("x",response=r(401),body=None),"AUTHENTICATION","IN_PARSE_BOUNDARY"),("RATE",RateLimitError("x",response=r(429),body=None),"RATE_LIMIT","IN_PARSE_BOUNDARY"),
 ("BAD_REQUEST_400",BadRequestError("server",response=r(400),body=None),"BAD_REQUEST","IN_PARSE_BOUNDARY"),("SERVER_500",InternalServerError("bad",response=r(500),body=None),"SERVER_ERROR","IN_PARSE_BOUNDARY"),("SERVER_599",InternalServerError("bad",response=r(599),body=None),"SERVER_ERROR","IN_PARSE_BOUNDARY"),
 ("PARSE",ParseOrSchemaFailure(),"PARSE_OR_SCHEMA","AFTER_PARSE_RESPONSE"),("UNKNOWN",RuntimeError(),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),
 ("BAD_REQUEST_TYPE_STATUS_CONFLICT",BadRequestError("bad request",response=r(500),body=None),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),("SERVER_ERROR_TYPE_STATUS_CONFLICT",InternalServerError("server error",response=r(400),body=None),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),
 ("TRUSTED_STATUS_BOOL",BadRequestError("x",response=r(True),body=None),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),("SERVER_600",InternalServerError("x",response=r(600),body=None),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),
 ("BEFORE",RuntimeError(),"UNKNOWN_PROVIDER_ERROR","BEFORE_PARSE_BOUNDARY")]
def _with_direct_status(failure, direct_status):
 failure.status_code=direct_status
 return failure
def build():
 cases=fixtures()
 cases.extend([
  ("BAD_DIRECT_400_RESPONSE_500",_with_direct_status(BadRequestError("x",response=r(500),body=None),400),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY"),
  ("SERVER_DIRECT_500_RESPONSE_400",_with_direct_status(InternalServerError("x",response=r(400),body=None),500),"UNKNOWN_PROVIDER_ERROR","IN_PARSE_BOUNDARY")])
 rows=[]
 for cid,f,e,s in cases:
  got=classify_parse_boundary_failure(failure=f,stage=s);assert got["failure_code"]==e
  rows.append({"case_id":cid,**got,"provider_calls":0,"live_calls":0,"sdk_extractions":0,"v017_attempts":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0})
 codes=["TIMEOUT","CONNECTION","AUTHENTICATION","RATE_LIMIT","BAD_REQUEST","SERVER_ERROR","PARSE_OR_SCHEMA","UNKNOWN_PROVIDER_ERROR"]
 counts={c:sum(x["failure_code"]==c for x in rows) for c in codes};assert all(counts.values()) and sum(counts.values())==len(rows)
 return {"stage_id":"DIRECT_READING_V2_PARSE_EXCEPTION_V021","status":"OFFLINE_EVIDENCE_COMPLETE","case_denominator":len(rows),"classified_count":len(rows),"safe_failure_count":0,"classification_attempts":sum(x["classification_attempts"] for x in rows),"status_read_count":sum(x["status_read_count"] for x in rows),"code_counts":counts,"provider_calls":0,"live_calls":0,"real_provider_instantiated":False,"sdk_extractions":0,"v017_attempts":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0,"automatic_retries":0,"cases":rows,"deployment":False,"production":False,"default_replacement":False}
def main():
 data=build();text=json.dumps(data,ensure_ascii=False,indent=2)+"\n";OUT.write_text(text,encoding="utf-8",newline="\n");print(hashlib.sha256(text.encode()).hexdigest().upper())
if __name__=="__main__":main()
