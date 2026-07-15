import re

import pytest

from abalo_iching.application.sites_structured_question_v1 import (
    ALLOWED_GOALS,
    TEMPLATE_VERSION,
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
    parse_structured_fields,
)


def test_every_finite_combination_is_exhaustively_allowed_or_rejected():
    generated = {}
    rejected = []
    for domain in QuestionDomain:
        for goal in DecisionGoal:
            for horizon in TimeHorizon:
                key = (domain, goal, horizon)
                if goal in ALLOWED_GOALS[domain]:
                    question, version = generate_structured_question(*key)
                    generated[key] = question
                    assert version == TEMPLATE_VERSION
                    assert generate_structured_question(*key) == (question, version)
                else:
                    with pytest.raises(ValueError, match="allowed combination"):
                        generate_structured_question(*key)
                    rejected.append(key)
    assert len(generated) == 68
    assert len(rejected) == 12
    assert len(set(generated.values())) == len(generated)


def test_generated_questions_stay_within_frozen_safety_language():
    for domain, goals in ALLOWED_GOALS.items():
        for goal in goals:
            for horizon in TimeHorizon:
                question, _version = generate_structured_question(domain, goal, horizon)
                assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", question)
                assert not any(term in question for term in ["保证", "一定会", "必然", "对方心里", "他会怎么想"])
                assert question.endswith("？")
                assert any(term in question for term in ["我当前", "我应", "现实信号"])


@pytest.mark.parametrize("field_index", [0, 1, 2])
def test_unknown_or_non_string_enum_is_rejected(field_index):
    valid = ["WORK_CAREER", "PLAN_NEXT_STEP", "CURRENT"]
    for bad in ["UNKNOWN", "", None, 3, True, " PLAN_NEXT_STEP"]:
        candidate = valid.copy()
        candidate[field_index] = bad
        with pytest.raises(ValueError):
            parse_structured_fields(*candidate)
