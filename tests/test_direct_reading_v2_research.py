from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from evals.meihua.direct_reading_v2_research_v001.experiment.run_direct_reading_research import (
    _call,
    _expand_questions,
    _render_chart,
    _request_messages,
)


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "evals/meihua/direct_reading_v2_research_v001"


def test_prompt_package_is_lean_and_has_no_discernment_gate() -> None:
    prompts = json.loads((RESEARCH / "prompts/prompt_package.json").read_text(encoding="utf-8"))
    text = json.dumps(prompts, ensure_ascii=False)
    assert prompts["reference_model"] == "chat-latest"
    assert prompts["candidate_model"] == "gpt-5.6-sol"
    assert prompts["max_output_tokens"] == 4000
    assert "confirmed_facts" not in text
    assert "unknowns" not in text
    assert "source_trace" not in text
    assert "请返回补充" not in text
    assert "没有额外辨识或现实背景。请仍然完成一篇完整解卦" in text


def test_every_case_sends_only_question_and_frozen_chart() -> None:
    prompts = json.loads((RESEARCH / "prompts/prompt_package.json").read_text(encoding="utf-8"))
    chart_cases = json.loads((RESEARCH / "cases/cases.json").read_text(encoding="utf-8"))["cases"]
    cases = _expand_questions(chart_cases)
    assert len(cases) == 9
    for case in cases:
        packet = _render_chart(case)
        assert case["question_text"]
        assert case["chart"]["moving_line"]["canonical_line_text"] in packet
        for arm in ("REFERENCE", "CANDIDATE"):
            body = json.dumps(_request_messages(case, prompts, arm), ensure_ascii=False)
            assert case["question_text"] in body
            assert case["chart"]["base_hexagram"]["name"] in body
            assert case["chart"]["mutual_hexagram"]["name"] in body
            assert case["chart"]["changed_hexagram"]["name"] in body
            for forbidden in ("answer_pool", "decision_bottleneck", "confirmed_facts", "unknowns"):
                assert forbidden not in body


def test_four_pairs_reuse_chart_but_change_question() -> None:
    chart_cases = json.loads((RESEARCH / "cases/cases.json").read_text(encoding="utf-8"))["cases"]
    cases = _expand_questions(chart_cases)
    pairs: dict[str, list[dict]] = {}
    for case in cases:
        if case.get("pair_id"):
            pairs.setdefault(case["pair_id"], []).append(case)
    assert len(pairs) == 4
    for items in pairs.values():
        assert len(items) == 2
        assert items[0]["question_text"] != items[1]["question_text"]
        assert items[0]["numbers"] == items[1]["numbers"]
        assert items[0]["chart"] == items[1]["chart"]


def test_calls_are_natural_text_without_schema_or_tools() -> None:
    prompts = json.loads((RESEARCH / "prompts/prompt_package.json").read_text(encoding="utf-8"))
    chart_cases = json.loads((RESEARCH / "cases/cases.json").read_text(encoding="utf-8"))["cases"]
    case = _expand_questions(chart_cases)[0]
    captured: list[dict] = []

    class Responses:
        def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                id="resp-test",
                _request_id="req-test",
                output_text="这是围绕所问生成的完整解卦。",
                usage=SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30),
            )

    client = SimpleNamespace(responses=Responses())
    _call(client, case=case, prompts=prompts, arm="REFERENCE")
    _call(client, case=case, prompts=prompts, arm="CANDIDATE")
    assert captured[0]["model"] == "chat-latest"
    assert "reasoning" not in captured[0]
    assert "text" not in captured[0]
    assert captured[1]["model"] == "gpt-5.6-sol"
    assert captured[1]["reasoning"] == {"effort": "high"}
    assert captured[1]["text"] == {"verbosity": "high"}
    for kwargs in captured:
        assert kwargs["tools"] == []
        assert kwargs["store"] is False
        assert "text_format" not in kwargs
