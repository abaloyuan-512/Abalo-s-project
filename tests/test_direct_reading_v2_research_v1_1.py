from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from evals.meihua.direct_reading_v2_research_v001.experiment.run_direct_reading_research import (
    _expand_questions,
)
from evals.meihua.direct_reading_v2_research_v0011.experiment.run_direct_reading_research_v1_1 import (
    _call,
)


ROOT = Path(__file__).resolve().parents[1]
REVISION = ROOT / "evals/meihua/direct_reading_v2_research_v0011"
SOURCE = ROOT / "evals/meihua/direct_reading_v2_research_v001"


def _prompts() -> dict:
    return json.loads((REVISION / "prompts/prompt_package.json").read_text(encoding="utf-8"))


def _case() -> dict:
    document = json.loads((SOURCE / "cases/cases.json").read_text(encoding="utf-8"))
    return _expand_questions(document["cases"])[0]


def test_revision_only_reduces_output_tendency_and_preserves_direct_reading() -> None:
    old = json.loads((SOURCE / "prompts/prompt_package.json").read_text(encoding="utf-8"))
    new = _prompts()
    assert new["candidate_model"] == old["candidate_model"] == "gpt-5.6-sol"
    assert new["candidate_reasoning_effort"] == old["candidate_reasoning_effort"] == "high"
    assert new["max_output_tokens"] == old["max_output_tokens"] == 4000
    assert old["candidate_verbosity"] == "high"
    assert new["candidate_verbosity"] == "medium"
    prompt_text = json.dumps(new, ensure_ascii=False)
    assert "1800至2600汉字" in prompt_text
    assert "不要要求补充辨识信息" in prompt_text
    assert "具体日期或必然结果" in prompt_text


def test_completed_response_is_product_complete() -> None:
    captured: list[dict] = []

    class Responses:
        def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                id="resp-complete",
                _request_id="req-complete",
                status="completed",
                incomplete_details=None,
                output_text="结论明确，四层卦理与行动边界均已完整收束。",
                usage=SimpleNamespace(input_tokens=100, output_tokens=1800, total_tokens=1900),
            )

    record = _call(SimpleNamespace(responses=Responses()), case=_case(), prompts=_prompts(), arm="CANDIDATE")
    assert record["status"] == "SUCCESS"
    assert record["product_complete"] is True
    assert record["hit_output_limit"] is False
    assert captured[0]["text"] == {"verbosity": "medium"}
    assert captured[0]["reasoning"] == {"effort": "high"}


def test_max_output_response_is_incomplete_even_with_text() -> None:
    class Responses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp-incomplete",
                _request_id="req-incomplete",
                status="incomplete",
                incomplete_details=SimpleNamespace(model_dump=lambda **_: {"reason": "max_output_tokens"}),
                output_text="这是一篇有内容但在中途被截断的解卦",
                usage=SimpleNamespace(input_tokens=100, output_tokens=4000, total_tokens=4100),
            )

    record = _call(SimpleNamespace(responses=Responses()), case=_case(), prompts=_prompts(), arm="CANDIDATE")
    assert record["status"] == "INCOMPLETE_OUTPUT"
    assert record["product_complete"] is False
    assert record["hit_output_limit"] is True
    assert record["incomplete_details"] == {"reason": "max_output_tokens"}


def test_all_model_inputs_still_exclude_discernment_and_legacy_advice() -> None:
    prompts = _prompts()
    document = json.loads((SOURCE / "cases/cases.json").read_text(encoding="utf-8"))
    for case in _expand_questions(document["cases"]):
        raw = json.dumps(case, ensure_ascii=False)
        for forbidden in ("confirmed_facts", "unknowns", "decision_bottleneck", "source_trace", "answer_pool"):
            assert forbidden not in raw
        assert case["question_text"]
        assert prompts["candidate_user_template"]
