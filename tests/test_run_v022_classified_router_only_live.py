from __future__ import annotations
import ast, importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"scripts/run_v022_classified_router_only_live.py"

def load():
 spec=importlib.util.spec_from_file_location("run_v022",RUNNER);assert spec and spec.loader
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_runner_has_one_parse_no_loop_and_frozen_zero_retry():
 source=RUNNER.read_text(encoding="utf-8");tree=ast.parse(source)
 calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="parse"]
 assert len(calls)==1
 assert not any(isinstance(n,ast.While) for n in ast.walk(tree))
 assert "max_retries=0" in source

def test_initial_ledger_is_complete_and_router_only(monkeypatch):
 module=load();case={"case_id":"X","request":{"original_question":"这是一个足够长且明确的测试问题文本。","critical_ambiguity":{"kind":"SUBJECT","description":"测试歧义"}},"expected_outcome":{"status":"ASK_ONCE","ambiguity_kind":"SUBJECT"}}
 auth={"authorized_router_only_calls":1}
 ledger=module.initial(case,auth);row=ledger["cases"][0]
 assert row["terminal_status"]=="NOT_ATTEMPTED" and ledger["denominator"]==1
 assert ledger["high_calls"]==ledger["prepare_calls"]==ledger["cast_calls"]==ledger["process_calls"]==0
 assert "这是" not in repr(ledger)

def test_failure_writer_preserves_stage_without_exception_text(monkeypatch,tmp_path):
 module=load();module.LEDGER=tmp_path/"ledger.json"
 case={"case_id":"X","request":{"original_question":"这是一个足够长且明确的测试问题文本。","critical_ambiguity":{"kind":"SUBJECT","description":"测试歧义"}},"expected_outcome":{"status":"ASK_ONCE","ambiguity_kind":"SUBJECT"}}
 data=module.initial(case,{"authorized_router_only_calls":1})
 classification={"failure_code":"CONNECTION","failure_stage":"IN_PARSE_BOUNDARY","call_may_have_been_sent":True,"terminal_certainty":"TERMINAL_UNKNOWN","classification_attempts":1,"status_read_count":0}
 assert module.fail(data,classification,0.0,attempted=True,stage="IN_PARSE_BOUNDARY")==1
 text=module.LEDGER.read_text(encoding="utf-8")
 assert "CONNECTION" in text and "TERMINAL_UNKNOWN" in text and "exception" not in text
