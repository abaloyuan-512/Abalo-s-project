from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path

import pytest

from abalo_iching.application.sites_light_router_adapter_v015 import ModelDecision
from abalo_iching.application.sites_light_router_atomic_receipt_v017 import rebuild_atomic_receipt_sha256
from abalo_iching.application.sites_light_router_sdk_bridge_v018 import (
    bridge_sdk_response_to_v017,
    make_sdk_response_fixture,
    mix_sdk_response_fixtures_for_test,
    rebuild_integration_binding_sha256,
)


QUESTION = "我正在决定这个项目的去留：是继续投入，还是停止并退出？"


def request(kind: str = "SUBJECT") -> dict[str, object]:
    return {"original_question": QUESTION, "critical_ambiguity": {"kind": kind, "description": "关键歧义"}}


def run(response: object, case: str = "CASE-A", kind: str = "SUBJECT"):
    return bridge_sdk_response_to_v017(case_id=case, request_payload=request(kind), sdk_response=response)


def test_complete_pass_and_ask_map_exactly_and_rebuild():
    for case, kind, decision in (
        ("PASS", "SUBJECT", ModelDecision(status="PASS")),
        ("ASK", "JUDGMENT_OBJECT", ModelDecision(status="ASK_ONCE", ambiguity_kind="JUDGMENT_OBJECT")),
    ):
        outcome, audit = run(make_sdk_response_fixture(response_id=f"resp_{case}", decision=decision), case, kind)
        assert outcome == decision.model_dump(mode="json", exclude_none=True)
        assert audit["terminal_status"] == "TELEMETRY_COMPLETE"
        assert audit["sdk_response_extraction_attempts"] == audit["v017_receipt_attempts"] == 1
        assert rebuild_atomic_receipt_sha256(audit["v017_audit"]) == audit["v017_audit"]["raw_receipt_sha256"]
        assert rebuild_integration_binding_sha256(audit) == audit["integration_binding_sha256"]


@pytest.mark.parametrize("kwargs", [
    {"response_id": None},
    {"response_id": "x", "input_tokens": None, "output_tokens": None, "total_tokens": None},
    {"response_id": "x", "total_tokens": 999},
    {"response_id": "x", "status": "incomplete"},
])
def test_missing_or_bad_sdk_metadata_fails_without_complete_evidence(kwargs):
    _, audit = run(make_sdk_response_fixture(**kwargs))
    assert audit["terminal_status"] == "TELEMETRY_INCOMPLETE"
    v = audit["v017_audit"]
    assert v["response_id"] is v["total_tokens"] is v["raw_receipt_sha256"] is None


def test_bad_decision_and_kind_mismatch_fail():
    wrong = make_sdk_response_fixture(response_id="wrong", decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="DECISION_AXIS"))
    _, audit = run(wrong, kind="SUBJECT")
    assert audit["terminal_status"] == "TELEMETRY_INCOMPLETE"


@pytest.mark.parametrize("fields", [{"decision"}, {"id", "usage"}, {"model", "decision"}, {"id", "model", "status", "usage", "decision"}])
def test_two_individually_valid_sdk_responses_cannot_be_mixed(fields):
    a = make_sdk_response_fixture(response_id="resp_A", decision=ModelDecision(status="PASS"))
    b = make_sdk_response_fixture(response_id="resp_B", decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="SUBJECT"))
    assert run(make_sdk_response_fixture(response_id="control_A"))[1]["terminal_status"] == "TELEMETRY_COMPLETE"
    assert run(make_sdk_response_fixture(response_id="control_B", decision=ModelDecision(status="ASK_ONCE", ambiguity_kind="SUBJECT")))[1]["terminal_status"] == "TELEMETRY_COMPLETE"
    mixed = mix_sdk_response_fixtures_for_test(a, b, from_second=fields)
    _, audit = run(mixed)
    assert audit["terminal_status"] == "SDK_RESPONSE_REJECTED" and audit["v017_audit"] is None


def test_same_instance_second_use_and_cross_case_reuse_fail():
    response = make_sdk_response_fixture(response_id="resp_once")
    assert run(response)[1]["terminal_status"] == "TELEMETRY_COMPLETE"
    assert run(response)[1]["terminal_status"] == "SDK_RESPONSE_REJECTED"
    another = make_sdk_response_fixture(response_id="resp_cross")
    assert run(another, "CASE-A")[1]["terminal_status"] == "TELEMETRY_COMPLETE"
    assert run(another, "CASE-B")[1]["terminal_status"] == "SDK_RESPONSE_REJECTED"


class Evil:
    def __init__(self): object.__setattr__(self, "effects", 0)
    def __getattr__(self, name): object.__setattr__(self, "effects", self.effects + 1); raise AttributeError(name)
    def __iter__(self): object.__setattr__(self, "effects", self.effects + 1); return iter(())


def test_wrong_type_and_malicious_object_zero_side_effect():
    evil = Evil()
    _, audit = run(evil)
    assert evil.effects == 0 and audit["sdk_response_extraction_attempts"] == 0


def test_extraction_error_and_invalid_request_leave_no_receipt():
    _, extraction = run(make_sdk_response_fixture(response_id="x", extraction_error=True))
    assert extraction["sdk_response_extraction_attempts"] == 1 and extraction["v017_audit"] is None
    response = make_sdk_response_fixture(response_id="never")
    outcome, invalid = bridge_sdk_response_to_v017(case_id="X", request_payload={"bad": "request"}, sdk_response=response)
    assert outcome["status"] == "FAILED" and invalid["terminal_status"] == "INVALID_REQUEST"
    assert invalid["sdk_response_extraction_attempts"] == 0 and invalid["v017_audit"] is None
    assert run(response)[1]["terminal_status"] == "TELEMETRY_COMPLETE"


def test_naked_exact_sdk_response_is_rejected_before_extraction():
    snapshot = make_sdk_response_fixture(response_id="real_shape")
    fields = dict(snapshot._fields)
    from openai.types.responses.parsed_response import ParsedResponse
    from abalo_iching.application.sites_light_router_sdk_bridge_v018 import SDK_RESPONSE_TYPE
    decision = fields["decision"].value
    naked = SDK_RESPONSE_TYPE.model_construct(
        id=fields["id"].value, model=fields["model"].value,
        status=fields["status"].value, usage=fields["usage"].value, output=[]
    )
    object.__setattr__(naked, "_fake_decision", decision)
    outcome, audit = run(naked)
    assert outcome["status"] == "FAILED"
    assert audit["sdk_response_extraction_attempts"] == 0 and audit["v017_audit"] is None


def test_static_boundary_has_no_client_key_high_or_cast():
    import abalo_iching.application.sites_light_router_sdk_bridge_v018 as module
    source = Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not ({"OpenAI", "cast_meihua", "prepare_direct_reading_v2_request", "process_prepared_direct_reading_v2_request"} & names)
    assert "OPENAI_API_KEY" not in source and "os.getenv" not in source


def test_history_is_immutable():
    root = Path(__file__).resolve().parents[1]
    locked = {
        "evals/meihua/direct_reading_v2_light_router_atomic_receipt_v017/candidate_manifest.json": "3EAED990E1F03DE10A7B44598F5B5D16BE71D51909B46AFD77BF76D655467EC6",
        "evals/meihua/direct_reading_v2_light_router_receipt_v016/candidate_manifest.json": "3396D84D379C4047B301E84332650E607AAE820A806688673535B1E22F827BD1",
        "outputs/v015_router_only_live_ledger.json": "FAB59E6BC856C3EA217D7702C76D8252A670E7E2F17DB8639CB6E0A2EA491321",
    }
    for path, expected in locked.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest().upper() == expected
