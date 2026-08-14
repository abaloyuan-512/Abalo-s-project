"""Zero-live diagnostic for the SDK response -> snapshot -> bridge boundaries."""
from __future__ import annotations
from typing import Any
from openai.types.responses.parsed_response import ParsedResponse
from abalo_iching.application.sites_light_router_adapter_v015 import ModelDecision
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import rebuild_atomic_cost_estimate_usd,rebuild_atomic_receipt_sha256
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import SDK_RESPONSE_TYPE,SDKResponseSnapshot,bridge_sdk_response_to_v017,rebuild_integration_binding_sha256

def diagnose_sdk_response(*,case_id:str,request_payload:object,sdk_response:object,force_bridge_failure:bool=False,force_receipt_rebuild_failure:bool=False,force_binding_rebuild_failure:bool=False)->dict[str,Any]:
 result={"case_id":case_id,"terminal_status":"DIAGNOSTIC_FAIL_STOP","last_completed_stage":"PARSE_RETURNED","failure_stage":None,"failure_code":None,"exact_parameterized_type_match":type(sdk_response) is SDK_RESPONSE_TYPE,"authoritative_sdk_type_match":type(sdk_response) is ParsedResponse[ModelDecision],"snapshot_attempts":0,"snapshot_success":False,"bridge_attempts":0,"bridge_success":False,"telemetry_complete":False,"v017_receipt_rebuilt":False,"integration_binding_rebuilt":False,"cost_rebuilt":False,"response_id":None,"usage_recorded":False,"raw_receipt_sha256":None,"integration_binding_sha256":None,"provider_calls":0,"live_calls":0,"real_provider_instantiated":False,"high_calls":0,"prepare_calls":0,"cast_calls":0,"process_calls":0,"automatic_retries":0}
 try:
  result["snapshot_attempts"]=1;snapshot=SDKResponseSnapshot(sdk_response)
 except (ValueError,AttributeError,TypeError):
  result.update({"failure_stage":"SDK_RESPONSE_TO_SNAPSHOT","failure_code":"SDK_RUNTIME_TYPE_OR_SCHEMA_REJECTED"});return result
 result.update({"snapshot_success":True,"last_completed_stage":"SDK_SNAPSHOT_CREATED"})
 try:
  result["bridge_attempts"]=1
  if force_bridge_failure: raise ValueError("fixture-only")
  outcome,bridge=bridge_sdk_response_to_v017(case_id=case_id,request_payload=request_payload,sdk_response=snapshot)
 except (ValueError,AttributeError,TypeError):
  result.update({"failure_stage":"SNAPSHOT_TO_V018_BRIDGE","failure_code":"V018_BRIDGE_REJECTED"});return result
 result["last_completed_stage"]="BRIDGE_RETURNED";result["bridge_success"]=True
 v=bridge.get("v017_audit")
 if bridge.get("terminal_status")!="TELEMETRY_COMPLETE" or type(v) is not dict:
  result.update({"failure_stage":"SNAPSHOT_TO_V018_BRIDGE","failure_code":"V017_TELEMETRY_INCOMPLETE"});return result
 result["telemetry_complete"]=True
 receipt_ok=rebuild_atomic_receipt_sha256(v)==v["raw_receipt_sha256"] and not force_receipt_rebuild_failure
 binding_ok=rebuild_integration_binding_sha256(bridge)==bridge["integration_binding_sha256"] and not force_binding_rebuild_failure
 cost_ok=rebuild_atomic_cost_estimate_usd(v)==v["actual_cost_estimate_usd"]
 if not (receipt_ok and binding_ok and cost_ok):
  result.update({"failure_stage":"TELEMETRY_REBUILD","failure_code":"TELEMETRY_REBUILD_FAILED"});return result
 result.update({"terminal_status":"DIAGNOSTIC_SUCCESS","last_completed_stage":"TELEMETRY_REBUILT","failure_stage":None,"failure_code":None,"v017_receipt_rebuilt":True,"integration_binding_rebuilt":True,"cost_rebuilt":True,"response_id":v["response_id"],"usage_recorded":v["total_tokens"] is not None,"raw_receipt_sha256":v["raw_receipt_sha256"],"integration_binding_sha256":bridge["integration_binding_sha256"],"outcome":outcome})
 return result

__all__=["diagnose_sdk_response"]
