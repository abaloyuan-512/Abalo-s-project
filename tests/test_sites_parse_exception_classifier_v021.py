from __future__ import annotations
import ast, inspect
from pathlib import Path
import httpx, pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, BadRequestError, InternalServerError, RateLimitError
from abalo_iching.application.sites_parse_exception_classifier_v021 import ParseOrSchemaFailure, classify_parse_boundary_failure

REQ=httpx.Request("POST","https://fixture.invalid")
def resp(status: object):
    r=httpx.Response(200,request=REQ); r.status_code=status; return r
def bad(status: object,msg="bait"):
    return BadRequestError(msg,response=resp(status),body=None)
def server(status: object,msg="bait"):
    return InternalServerError(msg,response=resp(status),body=None)

@pytest.mark.parametrize("failure,code,reads",[
 (APITimeoutError(request=REQ),"TIMEOUT",0),(APIConnectionError(request=REQ),"CONNECTION",0),
 (AuthenticationError("x",response=resp(401),body=None),"AUTHENTICATION",0),
 (RateLimitError("x",response=resp(429),body=None),"RATE_LIMIT",0),
 (bad(400),"BAD_REQUEST",1),(server(500),"SERVER_ERROR",1),(server(599),"SERVER_ERROR",1),
 (ParseOrSchemaFailure(),"PARSE_OR_SCHEMA",0),(RuntimeError(),"UNKNOWN_PROVIDER_ERROR",0)])
def test_exact_table(failure,code,reads):
    out=classify_parse_boundary_failure(failure=failure,stage="IN_PARSE_BOUNDARY")
    assert out["failure_code"]==code and out["status_read_count"]==reads

@pytest.mark.parametrize("failure",[bad(500,"bad request"),server(400,"server error"),server(600),bad(True),bad(None),bad("400"),bad(400.0)])
def test_conflicting_or_invalid_trusted_status_is_unknown(failure):
    out=classify_parse_boundary_failure(failure=failure,stage="IN_PARSE_BOUNDARY")
    assert out["failure_code"]=="UNKNOWN_PROVIDER_ERROR" and out["status_read_count"]==1

def test_general_status_and_subclass_are_unknown_without_status_read():
    class Child(BadRequestError): pass
    cases=[APIStatusError("x",response=resp(400),body=None),Child("x",response=resp(400),body=None)]
    for failure in cases:
        out=classify_parse_boundary_failure(failure=failure,stage="IN_PARSE_BOUNDARY")
        assert out["failure_code"]=="UNKNOWN_PROVIDER_ERROR" and out["status_read_count"]==0

def test_response_status_is_authoritative_when_direct_status_conflicts():
    bad_failure=bad(500); bad_failure.status_code=400
    server_failure=server(400); server_failure.status_code=500
    assert classify_parse_boundary_failure(failure=bad_failure,stage="IN_PARSE_BOUNDARY")["failure_code"]=="UNKNOWN_PROVIDER_ERROR"
    assert classify_parse_boundary_failure(failure=server_failure,stage="IN_PARSE_BOUNDARY")["failure_code"]=="UNKNOWN_PROVIDER_ERROR"

class Evil:
    def __init__(self): object.__setattr__(self,"effects",0)
    def __getattr__(self,n): object.__setattr__(self,"effects",self.effects+1); raise AttributeError(n)
    def __str__(self): object.__setattr__(self,"effects",self.effects+1); return "secret"
    @property
    def status_code(self): object.__setattr__(self,"effects",self.effects+1); return 500
    @property
    def body(self): object.__setattr__(self,"effects",self.effects+1); return "raw"
    @property
    def headers(self): object.__setattr__(self,"effects",self.effects+1); return {}
def test_untrusted_object_has_zero_side_effects():
    evil=Evil(); out=classify_parse_boundary_failure(failure=evil,stage="IN_PARSE_BOUNDARY")
    assert evil.effects==0 and out["status_read_count"]==0 and out["failure_code"]=="UNKNOWN_PROVIDER_ERROR"

def test_stage_and_static_safety():
    before=classify_parse_boundary_failure(failure=RuntimeError(),stage="BEFORE_PARSE_BOUNDARY")
    assert before["call_may_have_been_sent"] is False and before["terminal_certainty"]=="FAIL_STOP"
    import abalo_iching.application.sites_parse_exception_classifier_v021 as module
    source=Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8"); tree=ast.parse(source)
    names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
    assert not ({"OpenAI","getenv","cast_meihua","bridge_sdk_response_to_v017"}&names)
    for value in ("message","headers","body","traceback","OPENAI_API_KEY","repr(","str("):
        assert value not in source
