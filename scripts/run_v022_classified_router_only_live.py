from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
from time import perf_counter
from typing import Any
from openai import OpenAI
from abalo_iching.application.sites_light_router_adapter_v015 import TIMEOUT_SECONDS,build_openai_request
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import rebuild_atomic_cost_estimate_usd,rebuild_atomic_receipt_sha256
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import SDKResponseSnapshot,bridge_sdk_response_to_v017,rebuild_integration_binding_sha256
from abalo_iching.application.sites_parse_exception_classifier_v021 import ParseOrSchemaFailure,classify_parse_boundary_failure

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"evals/meihua/direct_reading_v2_parse_exception_v021"
MANIFEST=STAGE/"candidate_manifest.json"; QA=STAGE/"independent_acceptance_result.json"
CASE=STAGE/"v022_live_case.json"; AUTH=STAGE/"v022_live_authorization.json"
V018=ROOT/"evals/meihua/direct_reading_v2_light_router_sdk_bridge_v018/candidate_manifest.json"
V017=ROOT/"evals/meihua/direct_reading_v2_light_router_atomic_receipt_v017/candidate_manifest.json"
LEDGER=ROOT/"outputs/v022_classified_router_only_live_ledger.json"
EXPECTED={MANIFEST:"E4E6AFF14B5B4D8AAF444C4D53F1CD5F4526929653EA30A574551BC1223C7F08",QA:"D921E893935864A0234E79D9DBCD9A136E3F619368282CD896F570678CD18C1E",CASE:"CCEC6AD29DFB94637D32A2970F96984524553B0E7B7544E09345FA00ADC50B34",AUTH:"6AA4B93B11A8BA9B054882A77773F0F5BDC45EA946D001D9FBF3AA49CEA28D6C",V018:"30C1E24EB0675B7FC5091431AA1599CBAD9D0A14314713CDCDC812956D432109",V017:"3EAED990E1F03DE10A7B44598F5B5D16BE71D51909B46AFD77BF76D655467EC6"}
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def write(data:dict[str,Any])->None:
 tmp=LEDGER.with_suffix(".json.tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n");tmp.replace(LEDGER)
def guard()->tuple[dict[str,Any],dict[str,Any]]:
 if LEDGER.exists():raise RuntimeError("LEDGER_EXISTS")
 for path,expected in EXPECTED.items():
  if sha(path)!=expected:raise RuntimeError("LOCK_MISMATCH")
 case=json.loads(CASE.read_text(encoding="utf-8"));auth=json.loads(AUTH.read_text(encoding="utf-8"))
 if auth["authorized_router_only_calls"]!=1 or auth["automatic_retries"]!=0 or any(auth[x]!=0 for x in ("high_calls","prepare_calls","cast_calls","process_calls","v014_consumption_calls")):raise RuntimeError("AUTH_MISMATCH")
 return case,auth
def initial(case:dict[str,Any],auth:dict[str,Any])->dict[str,Any]:
 qsha=hashlib.sha256(case["request"]["original_question"].encode()).hexdigest().upper()
 row={"case_id":case["case_id"],"input_question_sha256":qsha,"ambiguity_kind":case["request"]["critical_ambiguity"]["kind"],"expected_outcome":case["expected_outcome"],"terminal_status":"NOT_ATTEMPTED","last_completed_stage":"PREFLIGHT","provider_kind":"OPENAI","provider_attempts":0,"router_live_calls":0,"real_provider_instantiated":False,"call_may_have_been_sent":False,"provider_response_observed":False,"failure_code":None,"failure_stage":None,"terminal_certainty":None,"classification_attempts":0,"status_read_count":0,"response_id":None,"provider_model":None,"provider_status":None,"input_tokens":None,"output_tokens":None,"total_tokens":None,"outcome":None,"question_sha_before":None,"question_sha_sent":None,"question_sha_after":None,"original_question_preserved":False,"sdk_response_extraction_attempts":0,"v017_receipt_attempts":0,"v017_fixture_fetches":0,"sdk_response_local_instance_sha256":None,"v017_request_binding_sha256":None,"v017_instance_token_sha256":None,"raw_decision_payload_sha256":None,"normalized_decision_sha256":None,"raw_receipt_sha256":None,"v017_receipt_rebuilt":False,"integration_binding_sha256":None,"integration_binding_rebuilt":False,"actual_cost_estimate_usd":None,"cost_estimate_mode":None,"input_usd_per_million":None,"output_usd_per_million":None,"rate_snapshot_sha256":None,"rate_source":None,"cost_rounding":None,"cost_precision_usd":None,"cost_estimate_rebuilt":False,"canonical_round_trip":False,"latency_ms":None}
 return {"stage_id":"DIRECT_READING_V2_CLASSIFIED_ROUTER_LIVE_V022","status":"STARTED","phase":"PREFLIGHT","candidate_manifest_sha256":EXPECTED[MANIFEST],"qa_result_sha256":EXPECTED[QA],"live_case_sha256":EXPECTED[CASE],"live_authorization_sha256":EXPECTED[AUTH],"authorization":auth,"denominator":1,"authorized_router_only_calls":1,"actual_provider_attempts":0,"real_router_live_calls":0,"not_attempted_terminal":0,"remaining_router_only_calls":1,"success_count":0,"failed_count":0,"response_id_count":0,"usage_record_count":0,"v017_receipt_count":0,"integration_binding_count":0,"automatic_retries":0,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0,"v014_consumption_calls":0,"cases":[row],"product_wiring":False,"deployment":False,"production":False,"default_replacement":False}
def fail(data:dict[str,Any],classification:dict[str,object],started:float,*,attempted:bool,stage:str)->int:
 row=data["cases"][0];row.update({"terminal_status":classification["terminal_certainty"],"last_completed_stage":stage,"failure_code":classification["failure_code"],"failure_stage":classification["failure_stage"],"terminal_certainty":classification["terminal_certainty"],"classification_attempts":classification["classification_attempts"],"status_read_count":classification["status_read_count"],"call_may_have_been_sent":classification["call_may_have_been_sent"],"latency_ms":max(0,int((perf_counter()-started)*1000))});data.update({"status":"FAIL_STOP","phase":stage,"failed_count":1,"remaining_router_only_calls":0,"not_attempted_terminal":0 if attempted else 1});write(data);return 1
def main()->int:
 case,auth=guard();data=initial(case,auth);write(data);row=data["cases"][0];started=perf_counter()
 if not os.getenv("OPENAI_API_KEY"):
  return fail(data,classify_parse_boundary_failure(failure=RuntimeError(),stage="BEFORE_PARSE_BOUNDARY"),started,attempted=False,stage="PREFLIGHT")
 try: client=OpenAI(timeout=TIMEOUT_SECONDS,max_retries=0)
 except BaseException as exc:return fail(data,classify_parse_boundary_failure(failure=exc,stage="BEFORE_PARSE_BOUNDARY"),started,attempted=False,stage="CLIENT_CONSTRUCTION")
 row.update({"terminal_status":"IN_FLIGHT_UNKNOWN","last_completed_stage":"CLIENT_READY","provider_attempts":1,"router_live_calls":1,"real_provider_instantiated":True,"call_may_have_been_sent":True});data.update({"phase":"PARSE_ENTERED","actual_provider_attempts":1,"real_router_live_calls":1,"remaining_router_only_calls":0});write(data)
 try: response=client.responses.parse(**build_openai_request(case["request"]))
 except BaseException as exc:return fail(data,classify_parse_boundary_failure(failure=exc,stage="IN_PARSE_BOUNDARY"),started,attempted=True,stage="IN_PARSE_BOUNDARY")
 row.update({"provider_response_observed":True,"last_completed_stage":"PARSE_RETURNED"});data["phase"]="PARSE_RETURNED";write(data)
 try:
  snapshot=SDKResponseSnapshot(response);outcome,bridge=bridge_sdk_response_to_v017(case_id=case["case_id"],request_payload=case["request"],sdk_response=snapshot)
 except BaseException:
  return fail(data,classify_parse_boundary_failure(failure=ParseOrSchemaFailure(),stage="AFTER_PARSE_RESPONSE"),started,attempted=True,stage="POST_RESPONSE_SNAPSHOT_OR_BRIDGE")
 try:
  v=bridge["v017_audit"];receipt_ok=bool(v and rebuild_atomic_receipt_sha256(v)==v["raw_receipt_sha256"]);binding_ok=rebuild_integration_binding_sha256(bridge)==bridge["integration_binding_sha256"];cost=rebuild_atomic_cost_estimate_usd(v);cost_ok=cost==v["actual_cost_estimate_usd"]
  usage_ok=type(v["input_tokens"]) is int and type(v["output_tokens"]) is int and type(v["total_tokens"]) is int and v["total_tokens"]==v["input_tokens"]+v["output_tokens"]
  success=outcome==case["expected_outcome"] and bridge["terminal_status"]=="TELEMETRY_COMPLETE" and receipt_ok and binding_ok and cost_ok and usage_ok and bool(v["response_id"]) and v["provider_status"]=="completed" and v["question_sha_before"]==row["input_question_sha256"]==v["question_sha_sent"]==v["question_sha_after"] and v["original_question_preserved"] is True and v["canonical_round_trip"] is True and bridge["sdk_response_extraction_attempts"]==1 and bridge["v017_receipt_attempts"]==1 and v["fixture_transport_calls"]==1
  row.update({"terminal_status":"SUCCESS" if success else "FAIL_STOP","last_completed_stage":"ACCEPTANCE_COMPLETE","response_id":v["response_id"],"provider_model":v["provider_model"],"provider_status":v["provider_status"],"input_tokens":v["input_tokens"],"output_tokens":v["output_tokens"],"total_tokens":v["total_tokens"],"outcome":outcome,"question_sha_before":v["question_sha_before"],"question_sha_sent":v["question_sha_sent"],"question_sha_after":v["question_sha_after"],"original_question_preserved":v["original_question_preserved"],"sdk_response_extraction_attempts":bridge["sdk_response_extraction_attempts"],"v017_receipt_attempts":bridge["v017_receipt_attempts"],"v017_fixture_fetches":v["fixture_transport_calls"],"sdk_response_local_instance_sha256":bridge["sdk_response_local_instance_sha256"],"v017_request_binding_sha256":v["request_binding_sha256"],"v017_instance_token_sha256":v["receipt_instance_token_sha256"],"raw_decision_payload_sha256":v["raw_decision_payload_sha256"],"normalized_decision_sha256":v["normalized_decision_sha256"],"raw_receipt_sha256":v["raw_receipt_sha256"],"v017_receipt_rebuilt":receipt_ok,"integration_binding_sha256":bridge["integration_binding_sha256"],"integration_binding_rebuilt":binding_ok,"actual_cost_estimate_usd":cost,"cost_estimate_mode":"INTERNAL_CONSERVATIVE_ESTIMATE_NOT_API_INVOICE","input_usd_per_million":v["input_usd_per_million"],"output_usd_per_million":v["output_usd_per_million"],"rate_snapshot_sha256":v["rate_snapshot_sha256"],"rate_source":v["rate_source"],"cost_rounding":v["cost_rounding"],"cost_precision_usd":v["cost_precision_usd"],"cost_estimate_rebuilt":cost_ok,"canonical_round_trip":v["canonical_round_trip"],"latency_ms":max(0,int((perf_counter()-started)*1000))})
  data.update({"status":"SUCCESS" if success else "FAIL_STOP","phase":"ACCEPTANCE_COMPLETE","success_count":1 if success else 0,"failed_count":0 if success else 1,"response_id_count":1 if success else 0,"usage_record_count":1 if success else 0,"v017_receipt_count":1 if success else 0,"integration_binding_count":1 if success else 0});write(data);return 0 if success else 1
 except BaseException:
  return fail(data,classify_parse_boundary_failure(failure=ParseOrSchemaFailure(),stage="AFTER_PARSE_RESPONSE"),started,attempted=True,stage="TELEMETRY_REBUILD")
if __name__=="__main__":sys.exit(main())
