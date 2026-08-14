from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from abalo_iching.application.sites_direct_reading_v2 import (
    DirectReadingChartFacts,
    DirectReadingOptionalContext,
    validate_direct_reading_text,
)


ROOT = Path(__file__).parents[1]
SOURCE_RESULT = ROOT / "outputs" / "v007_s1_01_real_result.json"
PREFIX = "> 用户提供的现实背景（非卦象证据）："

POSITIVE_CASES = [
    (
        "literal_s1_shape",
        "我和伴侣已经就未来生活安排形成了共同方案，但还没有开始执行。",
        "我和伴侣已经就未来生活安排形成了共同方案，但还没有开始执行",
        None,
    ),
    (
        "literal_first_person_preserved",
        "我和伴侣已经就未来生活安排形成了共同方案。",
        "我和伴侣已经就未来生活安排形成了共同方案",
        None,
    ),
    (
        "punctuation_and_space_normalization",
        "你们已经完成预算，且明确了分工。",
        " 你们已经完成预算, 且明确了分工 ",
        None,
    ),
    (
        "negative_background",
        "你们已经确认目前不具备搬家的照护条件。",
        "你们已经确认目前不具备搬家的照护条件",
        None,
    ),
    (
        "conditional_background",
        "你们已经约定，如果预算不足就继续维持现状。",
        "你们已经约定，如果预算不足就继续维持现状",
        None,
    ),
    (
        "user_supplied_quantity",
        "你已经为转换工作预留了六个月生活费。",
        "你已经为转换工作预留了六个月生活费",
        None,
    ),
    (
        "user_supplied_date",
        "你已经在2026年8月11日收到书面通知，目前仍在考虑。",
        "你已经在2026年8月11日收到书面通知，目前仍在考虑",
        None,
    ),
    (
        "quoted_speaker_perspective_preserved",
        "伴侣说“我已经同意搬家”。",
        "伴侣说“我已经同意搬家”",
        None,
    ),
    (
        "optional_context_lineage",
        "我们应该现在推进合作吗？",
        "你们已经签署了非约束性意向书",
        DirectReadingOptionalContext(discernment_note="你们已经签署了非约束性意向书"),
    ),
    (
        "unicode_nfc",
        unicodedata.normalize("NFD", "你已经准备好咖啡预算。"),
        "你已经准备好咖啡预算",
        None,
    ),
]

NEGATIVE_CASES = [
    (
        "suffix_qualification_dropped",
        "你们已经形成共同方案，但尚未最终确认。",
        f"{PREFIX}你们已经形成共同方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "suffix_uncertainty_dropped",
        "你们已经形成共同方案，但结果仍不确定。",
        f"{PREFIX}你们已经形成共同方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "suffix_unless_dropped",
        "你们已经同意搬家，除非照护安排发生变化。",
        f"{PREFIX}你们已经同意搬家",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "quoted_speaker_pronoun_changed",
        "伴侣说“我已经同意搬家”。",
        f"{PREFIX}伴侣说“你已经同意搬家”",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "invented_fact",
        "我们应该推进共同方案吗？",
        "你们已经完成全部资金准备和家庭沟通。",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "faithful_but_unverifiable_paraphrase",
        "我和伴侣已经形成共同方案。",
        f"{PREFIX}双方的共同计划已经彻底敲定",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "subject_substitution",
        "我和同事已经完成预算。",
        f"{PREFIX}你们的伴侣已经完成预算",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "certainty_escalation",
        "你们可能已经形成共同方案。",
        f"{PREFIX}你们已经形成共同方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "reported_certainty_escalation",
        "据说你们已经形成共同方案，但还需要双方确认。",
        f"{PREFIX}你们已经形成共同方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "condition_dropped",
        "如果双方父母都同意，你们已经具备搬家的条件。",
        f"{PREFIX}你们已经具备搬家的条件",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "negation_dropped",
        "你们还没有完成资金准备。",
        f"{PREFIX}你们已经完成资金准备",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "fact_appended_to_excerpt",
        "你们已经形成共同方案。",
        f"{PREFIX}你们已经形成共同方案并完成全部资金准备",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "cross_case_fact",
        "我应该接受新工作吗？",
        f"{PREFIX}你们已经形成共同生活方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "missing_fixed_attribution",
        "你们已经形成共同方案。",
        "你们已经形成共同方案。",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "hexagram_claims_background",
        "你们已经形成共同方案。",
        "卦象证明这一现实背景：你们已经形成共同方案。",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "nested_prefix_injection",
        "你们已经形成共同方案。",
        f"{PREFIX}{PREFIX}你们已经形成共同方案",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "invented_third_party_motive",
        "你们已经形成共同方案。",
        "伴侣其实想离开你。",
        "THIRD_PARTY_MIND_READING",
    ),
    (
        "invented_action_date",
        "你们已经形成共同方案。",
        "你们应该在2026年9月1日启动搬家。",
        "UNSUPPORTED_DATE",
    ),
    (
        "existing_work_ten_years_red_team",
        "我应该接受新工作吗？",
        "你在公司工作了十年。",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "existing_team_restructure_red_team",
        "我应该接受新工作吗？",
        "你的团队正在重组。",
        "UNSUPPORTED_REALITY_FACT",
    ),
    (
        "dangerous_markup_remains_visible_to_all_gates",
        "你们已经形成共同方案。",
        f"{PREFIX}你们已经形成共同方案\n<script>alert(1)</script>",
        "DANGEROUS_MARKUP",
    ),
]


@pytest.fixture(scope="module")
def released_case() -> tuple[str, DirectReadingChartFacts]:
    result = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    return (
        result["direct_reading"]["text"],
        DirectReadingChartFacts.model_validate(result["chart_facts"]),
    )


def _errors(
    released_case: tuple[str, DirectReadingChartFacts],
    *,
    question: str,
    added: str,
    optional_context: DirectReadingOptionalContext | None = None,
) -> tuple[str, ...]:
    reading, facts = released_case
    return validate_direct_reading_text(
        f"{reading}\n\n{added}",
        question_text=question,
        facts=facts,
        optional_context=optional_context,
    )


@pytest.mark.parametrize(
    ("case_id", "question", "excerpt", "optional_context"),
    POSITIVE_CASES,
)
def test_verified_user_background_lineage_releases(
    released_case: tuple[str, DirectReadingChartFacts],
    case_id: str,
    question: str,
    excerpt: str,
    optional_context: DirectReadingOptionalContext | None,
) -> None:
    errors = _errors(
        released_case,
        question=question,
        added=f"{PREFIX}{excerpt}",
        optional_context=optional_context,
    )

    assert "UNSUPPORTED_REALITY_FACT" not in errors, case_id


def test_verified_excerpt_can_be_followed_by_conditional_inference(
    released_case: tuple[str, DirectReadingChartFacts],
) -> None:
    errors = _errors(
        released_case,
        question="你们已经形成共同方案，但尚未执行。",
        added=(
            f"{PREFIX}你们已经形成共同方案，但尚未执行\n"
            "如果执行压力超过承受范围，可能需要暂停并重新核实条件。"
        ),
    )

    assert "UNSUPPORTED_REALITY_FACT" not in errors


@pytest.mark.parametrize(
    ("case_id", "question", "added", "expected_code"),
    NEGATIVE_CASES,
)
def test_unverified_or_unsafe_reality_claims_remain_blocked(
    released_case: tuple[str, DirectReadingChartFacts],
    case_id: str,
    question: str,
    added: str,
    expected_code: str,
) -> None:
    errors = _errors(released_case, question=question, added=added)

    assert expected_code in errors, case_id


def test_production_validation_receives_optional_context_lineage(monkeypatch) -> None:
    from abalo_iching.application import sites_direct_reading_v2 as module
    from tests.test_sites_direct_reading_v2 import StubProvider, _complete_text, _provider_result

    question = "我们应该现在推进合作吗？"
    background = "你们已经签署了非约束性意向书"
    text = f"{_complete_text()}\n\n{PREFIX}{background}"
    provider = StubProvider(_provider_result(text))

    result = module.process_direct_reading_v2_request(
        {
            "question_text": question,
            "numbers": [5, 6, 3],
            "optional_context": {"discernment_note": background},
        },
        provider=provider,
        request_id="drv2-v008-production-lineage",
    )

    assert result["status"] == "SUCCESS"
    assert len(provider.calls) == 1
    assert PREFIX in provider.calls[0][1]

