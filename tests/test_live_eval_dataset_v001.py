import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/"evals/meihua/live_eval_v001/dataset.json").read_text("utf-8"))
def test_fixed_dataset_identity_and_counts():
    assert DATA["eval_version"]=="MEIHUA_LIVE_EVAL_V001"
    assert len(DATA["cases"])==12
    assert sum(x["case_type"]=="NORMAL" for x in DATA["cases"])==8
    assert sum(x["case_type"]=="ADVERSARIAL" for x in DATA["cases"])==4
    assert all(x["synthetic"] is True for x in DATA["cases"])
def test_fixed_low_and_medium_plan():
    assert len(DATA["low_case_ids"])==12
    assert DATA["medium_case_ids"]==["CASE-002","CASE-005","CASE-006","CASE-008"]
    assert DATA["max_cases"]==16 and DATA["max_total_attempts"]==32 and DATA["max_output_tokens"]==2000
def test_every_case_has_expected_time_horizon():
    expected={"CASE-001":"未来三个月","CASE-002":"未来两个月","CASE-003":"未来三个月","CASE-004":"未来六周","CASE-005":"未来三个月","CASE-006":"未来三个月","CASE-007":"未来两个月","CASE-008":"未来六周","CASE-009":"未来六周","CASE-010":"未来三个月","CASE-011":"未来两个月","CASE-012":"未来六周"}
    assert {x["case_id"]:x["time_horizon"] for x in DATA["cases"]}==expected
