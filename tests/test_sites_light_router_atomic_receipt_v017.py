from __future__ import annotations
import hashlib, inspect, json
import pytest
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import (
 make_atomic_fixture_response,mix_valid_responses_for_test,process_atomic_fixture_receipt,rebuild_atomic_receipt_sha256)

Q="我正在决定一个副业项目的去留：是继续投入，还是停止并退出？"
def req(kind="SUBJECT"): return {"original_question":Q,"critical_ambiguity":{"kind":kind,"description":"关键歧义"}}
def payload(rid="resp_A", decision=None, usage=None): return {"response_id":rid,"model":"gpt-5.6-luna-fixture","provider_status":"completed","usage":usage or {"input_tokens":100,"output_tokens":10,"total_tokens":110},"decision":decision or {"status":"PASS"}}
def run(resp,case="CASE-A",kind="SUBJECT"): return process_atomic_fixture_receipt(case_id=case,request_payload=req(kind),response=resp)

def test_two_instances_are_unique_and_rebuildable():
 a=make_atomic_fixture_response(payload());b=make_atomic_fixture_response(payload())
 _,aa=run(a);_,bb=run(b,case="CASE-B")
 assert aa["receipt_instance_token_sha256"]!=bb["receipt_instance_token_sha256"]
 assert aa["raw_receipt_sha256"]!=bb["raw_receipt_sha256"]
 assert rebuild_atomic_receipt_sha256(aa)==aa["raw_receipt_sha256"]

@pytest.mark.parametrize("from_second",[
 {"decision"},
 {"model","decision"},
 {"response_id","usage"},
 {"response_id","model","provider_status","usage","decision"},
])
def test_two_individually_valid_receipts_cannot_be_mixed(from_second):
 a=make_atomic_fixture_response(payload("resp_A"));b=make_atomic_fixture_response(payload("resp_B",{"status":"ASK_ONCE","ambiguity_kind":"SUBJECT"},{"input_tokens":200,"output_tokens":20,"total_tokens":220}))
 assert run(make_atomic_fixture_response(payload("valid_A")))[1]["terminal_status"]=="RECEIPT_COMPLETE"
 assert run(make_atomic_fixture_response(payload("valid_B",{"status":"ASK_ONCE","ambiguity_kind":"SUBJECT"})))[1]["terminal_status"]=="RECEIPT_COMPLETE"
 mixed=mix_valid_responses_for_test(a,b,from_second=from_second)
 _,audit=run(mixed)
 assert audit["terminal_status"]=="RECEIPT_INCOMPLETE" and audit["receipt_observed"] is False
 assert audit["response_id"] is audit["total_tokens"] is audit["raw_receipt_sha256"] is None

def test_same_instance_second_use_and_cross_case_reuse_fail_without_evidence():
 r=make_atomic_fixture_response(payload())
 assert run(r)[1]["terminal_status"]=="RECEIPT_COMPLETE"
 _,second=run(r)
 assert second["terminal_status"]=="RECEIPT_INCOMPLETE" and second["response_id"] is None
 r2=make_atomic_fixture_response(payload("resp_cross")); assert run(r2,case="CASE-A")[1]["receipt_observed"]
 _,cross=run(r2,case="CASE-B"); assert cross["receipt_observed"] is False

def test_old_token_or_receipt_metadata_has_no_injection_api():
 params=set(inspect.signature(process_atomic_fixture_receipt).parameters)
 assert params=={"case_id","request_payload","response"}
 class Pretender(dict):
  pass
 pretend=Pretender(payload("resp_old_token"))
 pretend["receipt_instance_token"]="old-token"
 _,audit=run(pretend)
 assert audit["provider_attempts"]==0 and audit["receipt_instance_token_sha256"] is None

def test_response_is_immutable_and_one_shot():
 r=make_atomic_fixture_response(payload())
 with pytest.raises(AttributeError): r._token="forged"
 assert run(r)[1]["terminal_status"]=="RECEIPT_COMPLETE"
 assert run(r)[1]["terminal_status"]=="RECEIPT_INCOMPLETE"

def test_attempt_accounting_is_derived_from_transport_boundary(monkeypatch):
 import abalo_iching.application.sites_light_router_atomic_receipt_v017 as module
 calls=[]
 original=module._AtomicFixtureTransport.fetch
 def counted(self):
  calls.append("fetch")
  return original(self)
 monkeypatch.setattr(module._AtomicFixtureTransport,"fetch",counted)
 _,complete=run(make_atomic_fixture_response(payload("resp_counted")))
 assert calls==["fetch"]
 assert complete["provider_attempts"]==complete["fixture_transport_calls"]==len(calls)==1
 calls.clear()
 _,invalid=run({"not":"a response"})
 assert calls==[] and invalid["provider_attempts"]==invalid["fixture_transport_calls"]==0

def test_binding_changes_receipt_sha():
 _,a=run(make_atomic_fixture_response(payload()),case="CASE-A")
 _,b=run(make_atomic_fixture_response(payload()),case="CASE-B")
 assert a["request_binding_sha256"]!=b["request_binding_sha256"] and a["raw_receipt_sha256"]!=b["raw_receipt_sha256"]

class Evil:
 def __init__(self): object.__setattr__(self,"effects",0)
 def __getattr__(self,n): object.__setattr__(self,"effects",self.effects+1);raise AttributeError
 def __iter__(self): object.__setattr__(self,"effects",self.effects+1);return iter(())
def test_malicious_object_zero_attempt_zero_side_effect():
 e=Evil();_,a=run(e);assert e.effects==0 and a["provider_attempts"]==0 and not a["receipt_observed"]

@pytest.mark.parametrize("bad",[
 {"response_id":"x","model":"m","provider_status":"completed","decision":{"status":"PASS"}},
 payload(usage={"input_tokens":1,"output_tokens":1,"total_tokens":3}),
 payload(decision={"status":"FAILED"}),
])
def test_missing_usage_bad_usage_and_bad_decision_fail(bad):
 try:r=make_atomic_fixture_response(bad)
 except ValueError:return
 _,a=run(r);assert a["terminal_status"]=="RECEIPT_INCOMPLETE" and a["response_id"] is None

def test_projection_binds_all_public_fields():
 _,a=run(make_atomic_fixture_response(payload()))
 for field,value in (("receipt_instance_token_sha256","0"*64),("request_binding_sha256","1"*64),("response_id","changed"),("input_tokens",101),("normalized_decision",{"status":"ASK_ONCE","ambiguity_kind":"SUBJECT"})):
  x=dict(a);x[field]=value
  if field=="input_tokens":x["total_tokens"]=111
  with pytest.raises(ValueError) if field=="normalized_decision" else pytest.raises(AssertionError):
   if field=="normalized_decision": rebuild_atomic_receipt_sha256(x)
   else: assert rebuild_atomic_receipt_sha256(x)==a["raw_receipt_sha256"]

def test_history_immutable():
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]
 locked={"evals/meihua/direct_reading_v2_light_router_receipt_v016/candidate_manifest.json":"3396D84D379C4047B301E84332650E607AAE820A806688673535B1E22F827BD1","outputs/v015_router_only_live_ledger.json":"FAB59E6BC856C3EA217D7702C76D8252A670E7E2F17DB8639CB6E0A2EA491321"}
 for p,h in locked.items(): assert hashlib.sha256((root/p).read_bytes()).hexdigest().upper()==h

def test_frozen_offline_ledger_has_required_failures_and_conserves_counts():
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]
 ledger=json.loads((root/"evals/meihua/direct_reading_v2_light_router_atomic_receipt_v017/offline_ledger.json").read_text(encoding="utf-8"))
 ids=[row["case_id"] for row in ledger["cases"]]
 assert "MISSING_USAGE" in ids and "MALICIOUS_RECEIPT_OR_FIELD" in ids
 assert "CROSS_RECEIPT_MIX" in ids and "CROSS_CASE_REUSE" in ids
 assert ledger["case_denominator"]==len(ids)==11
 assert ledger["provider_attempts"]==ledger["fixture_transport_calls"]==sum(row["provider_attempts"] for row in ledger["cases"])
 assert ledger["complete_receipt_count"]==ledger["response_id_count"]==ledger["usage_record_count"]==ledger["instance_token_evidence_count"]==ledger["raw_receipt_digest_count"]==2
 failed=[row for row in ledger["cases"] if row["terminal_status"]!="RECEIPT_COMPLETE"]
 assert all(row["response_id"] is row["total_tokens"] is row["receipt_instance_token_sha256"] is row["raw_receipt_sha256"] is None for row in failed)
