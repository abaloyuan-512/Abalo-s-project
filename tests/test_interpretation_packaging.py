from importlib.resources import files
from pathlib import Path


def test_package_resources_include_both_knowledge_files_and_prompt():
    data = files("abalo_iching.data.meihua")
    prompts = files("abalo_iching.interpretation.prompts")
    assert data.joinpath("hexagram_canonical_texts_v1.json").is_file()
    assert data.joinpath("interpretation_knowledge_v1.json").is_file()
    assert prompts.joinpath("meihua_interpretation_v1.txt").is_file()


def test_pyproject_declares_json_prompt_and_runtime_dependencies():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"abalo_iching.data.meihua" = ["*.json"]' in text
    assert '"abalo_iching.interpretation.prompts" = ["*.txt"]' in text
    assert '"openai>=2.45,<3"' in text
    assert '"pydantic>=2.10,<3"' in text


def test_live_smoke_is_opt_in_and_not_a_pytest_test():
    text = Path("scripts/run_openai_interpretation_smoke.py").read_text(encoding="utf-8")
    assert "--confirm-live-call" in text
    assert "OPENAI_API_KEY" in text
    assert "LIVE_CALL_NOT_RUN" in text
    assert "内部评测结果，不构成正式报告" in text
    adapter_spec = Path("docs/specs/MEIHUA_OPENAI_ADAPTER_V1.md").read_text(encoding="utf-8")
    assert "LIVE_MODEL_AVAILABILITY_NOT_VERIFIED" in adapter_spec


def test_legacy_entrypoints_are_not_part_of_phase2_diff():
    assert Path("streamlit_app.py").is_file()
    assert Path("iching_tools.py").is_file()
