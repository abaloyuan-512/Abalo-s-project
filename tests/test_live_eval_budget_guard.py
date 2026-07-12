from pathlib import Path
import pytest
from scripts.run_meihua_live_eval_v001 import LiveEvalGuardError,validate_guards,validate_output_dir,build_plan,ROOT
import json
def test_missing_key_blocks_before_call(tmp_path):
    with pytest.raises(LiveEvalGuardError,match="OPENAI_API_KEY_NOT_CONFIGURED"):
        validate_guards(confirm_live_eval=True,confirm_max_attempts=32,output_dir=tmp_path,key_present=False)
def test_missing_confirmations_block(tmp_path):
    with pytest.raises(LiveEvalGuardError): validate_guards(confirm_live_eval=False,confirm_max_attempts=32,output_dir=tmp_path,key_present=True)
    with pytest.raises(LiveEvalGuardError): validate_guards(confirm_live_eval=True,confirm_max_attempts=31,output_dir=tmp_path,key_present=True)
def test_repo_output_is_rejected():
    from scripts.run_meihua_live_eval_v001 import ROOT
    with pytest.raises(LiveEvalGuardError,match="OUTSIDE"):
        validate_guards(confirm_live_eval=True,confirm_max_attempts=32,output_dir=ROOT/"bad",key_present=True)
def test_plan_is_exactly_16_and_at_most_32_attempts():
    from scripts.run_meihua_live_eval_v001 import DATASET
    p=build_plan(json.loads(DATASET.read_text("utf-8"))); assert len(p)==16 and len(p)*2==32
def test_smoke_requires_exactly_two_confirmed_attempts(tmp_path):
    validate_guards(confirm_live_eval=True,confirm_max_attempts=2,output_dir=tmp_path,key_present=True,expected_max_attempts=2)
    with pytest.raises(LiveEvalGuardError): validate_guards(confirm_live_eval=True,confirm_max_attempts=32,output_dir=tmp_path,key_present=True,expected_max_attempts=2)
@pytest.mark.parametrize("mode",["dry-run","mock","smoke","live"])
def test_every_mode_rejects_repo_output(mode):
    with pytest.raises(LiveEvalGuardError,match="OUTSIDE"): validate_output_dir(ROOT/mode)
