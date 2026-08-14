from __future__ import annotations
import ast,inspect
from pathlib import Path
from abalo_iching.application.sites_light_router_adapter_v015 import ModelDecision
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import SDK_RESPONSE_TYPE
from openai.types.responses.parsed_response import ParsedResponseOutputMessage,ParsedResponseOutputText
from openai.types.responses.response_usage import InputTokensDetails,OutputTokensDetails,ResponseUsage
from abalo_iching.application.sites_sdk_runtime_diagnostic_v023 import diagnose_sdk_response
Q={"original_question":"这是一个足够长的离线诊断问题文本。","critical_ambiguity":{"kind":"SUBJECT","description":"主体歧义"}}
def run(response,**kw):return diagnose_sdk_response(case_id="V023",request_payload=Q,sdk_response=response,**kw)
def sdk_response(*,response_id="fixture",decision=None):
 decision=decision or ModelDecision(status="PASS")
 text=ParsedResponseOutputText(annotations=[],text="fixture",type="output_text",parsed=decision)
 message=ParsedResponseOutputMessage(id="fixture-message",content=[text],role="assistant",status="completed",type="message")
 usage=ResponseUsage.model_construct(input_tokens=100,input_tokens_details=InputTokensDetails.model_construct(cache_write_tokens=0,cached_tokens=0),output_tokens=10,output_tokens_details=OutputTokensDetails.model_construct(reasoning_tokens=0),total_tokens=110)
 return SDK_RESPONSE_TYPE.model_construct(id=response_id,model="gpt-5.6-luna-fixture",status="completed",usage=usage,output=[message])
def test_official_sdk_shape_pass_and_ask_rebuild():
 for decision in (ModelDecision(status="PASS"),ModelDecision(status="ASK_ONCE",ambiguity_kind="SUBJECT")):
  r=run(sdk_response(response_id="fixture",decision=decision));assert r["terminal_status"]=="DIAGNOSTIC_SUCCESS";assert r["last_completed_stage"]=="TELEMETRY_REBUILT" and r["failure_stage"] is None;assert r["v017_receipt_rebuilt"] and r["integration_binding_rebuilt"] and r["cost_rebuilt"]
def test_wrong_type_stops_before_bridge_without_side_effect():
 class Evil:
  effects=0
  def __getattr__(self,n):type(self).effects+=1;raise AttributeError(n)
 evil=Evil();r=run(evil);assert r["last_completed_stage"]=="PARSE_RETURNED" and r["failure_stage"]=="SDK_RESPONSE_TO_SNAPSHOT";assert r["bridge_attempts"]==0 and evil.effects==0
def test_incomplete_public_sdk_fields_localize_to_bridge():
 r=run(sdk_response(response_id=None));assert r["snapshot_success"] and r["bridge_attempts"]==1;assert r["last_completed_stage"]=="BRIDGE_RETURNED" and r["failure_code"]=="V017_TELEMETRY_INCOMPLETE"
def test_forced_bridge_and_rebuild_failures_are_distinct():
 b=run(sdk_response(response_id="b"),force_bridge_failure=True);assert b["last_completed_stage"]=="SDK_SNAPSHOT_CREATED" and b["failure_stage"]=="SNAPSHOT_TO_V018_BRIDGE"
 for key in ("force_receipt_rebuild_failure","force_binding_rebuild_failure"):
  r=run(sdk_response(response_id=key),**{key:True});assert r["last_completed_stage"]=="BRIDGE_RETURNED" and r["failure_stage"]=="TELEMETRY_REBUILD"
def test_exact_sdk_object_without_v018_private_snapshot_fields_is_accepted_by_snapshot():
 from openai.types.responses.parsed_response import ParsedResponse
 from abalo_iching.application.sites_light_router_adapter_v015 import ModelDecision
 assert SDK_RESPONSE_TYPE is ParsedResponse[ModelDecision]
def test_static_zero_live_boundary():
 import abalo_iching.application.sites_sdk_runtime_diagnostic_v023 as m
 source=Path(inspect.getsourcefile(m) or "").read_text(encoding="utf-8");tree=ast.parse(source);names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
 assert not ({"OpenAI","getenv","cast_meihua"}&names)
 for forbidden in ("OPENAI_API_KEY","traceback","headers","response.body","repr(") : assert forbidden not in source
