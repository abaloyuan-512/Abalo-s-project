import pytest

from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.validators import InterpretationValidator


def validate(output, request, knowledge, synthesis):
    return InterpretationValidator().validate(output, request, knowledge, synthesis)


def with_text(value, text, *, field="plain_language_explanation", evidence_ids=None):
    payload = value.model_dump(mode="json")
    if len(text.strip()) < 4:
        text = f"相关内容：{text}。"
    payload[field][0]["text"] = text
    if evidence_ids is not None:
        payload[field][0]["evidence_ids"] = evidence_ids
    return payload


def test_valid_narrative_passes(valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis):
    assert validate(valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis) == valid_interpretation


def test_ai_schema_has_no_program_owned_or_free_summary_fields(valid_interpretation):
    payload = valid_interpretation.model_dump(mode="json")
    forbidden = {"summary", "direct_conclusion", "conclusion_level", "current_situation", "timing", "supporting_factors", "blocking_factors"}
    assert not forbidden & set(payload)
    assert all("summary" not in claim for claims in payload.values() for claim in claims)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("本卦为坤，说明当前局势厚重。", "program_fact_restatement"),
        ("本次动爻位于三爻。", "program_fact_restatement"),
        ("七月十五号会有消息。", "ai_time_content_forbidden"),
        ("三日之内会有结果。", "ai_time_content_forbidden"),
        ("他其实舍不得离开你。", "third_party_mind_reading"),
        ("建议现在买币。", "financial_instruction"),
        ("建议把药停了。", "medical_instruction"),
        ("这个结果稳稳会成。", "absolute_assertion"),
    ],
)
def test_ten_confirmed_bypass_texts_are_blocked(
    text, error, valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = with_text(valid_interpretation, text)
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert error in exc.value.errors


def test_negative_evidence_cannot_be_rewritten_as_favorable(
    valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = with_text(valid_interpretation, "这一证据表明事情非常有利，应当立即推进。", evidence_ids=["E02"])
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert "negative_evidence_semantic_reversal" in exc.value.errors


def test_positive_evidence_cannot_be_rewritten_as_obstacle(
    valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = with_text(valid_interpretation, "这一项是阻碍，应当停止。", evidence_ids=["E08"])
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert "positive_evidence_semantic_reversal" in exc.value.errors


def test_mixed_evidence_cannot_be_forced_to_direction(
    valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = with_text(valid_interpretation, "这一证据明确有利。", evidence_ids=["E04"])
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert "mixed_evidence_forced_direction" in exc.value.errors


@pytest.mark.parametrize("extra_field", ["summary", "direct_conclusion", "timing", "chart_facts"])
def test_program_owned_fields_have_no_ai_input_position(
    extra_field, valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = valid_interpretation.model_dump(mode="json")
    payload[extra_field] = "当前局势非常有利，成功可能性很高。"
    with pytest.raises(InterpretationValidationError, match=f"schema:{extra_field}"):
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("七月十五号", "ai_time_content_forbidden"), ("七月十五", "ai_time_content_forbidden"),
        ("三日之内", "ai_time_content_forbidden"), ("三天以内", "ai_time_content_forbidden"),
        ("这两天", "ai_time_content_forbidden"), ("近日", "ai_time_content_forbidden"),
        ("过几天", "ai_time_content_forbidden"), ("月底前", "ai_time_content_forbidden"),
        ("下旬", "ai_time_content_forbidden"), ("明晚", "ai_time_content_forbidden"),
        ("后日上午", "ai_time_content_forbidden"), ("下个礼拜", "ai_time_content_forbidden"),
        ("稳稳会成", "absolute_assertion"), ("肯定能成", "absolute_assertion"),
        ("跑不了", "absolute_assertion"), ("没有悬念", "absolute_assertion"),
        ("十拿九稳", "absolute_assertion"), ("板上钉钉", "absolute_assertion"),
        ("一准会", "absolute_assertion"), ("准能成功", "absolute_assertion"),
        ("他其实舍不得你", "third_party_mind_reading"), ("她心里还有你", "third_party_mind_reading"),
        ("对方仍在惦记你", "third_party_mind_reading"), ("他只是没说出口", "third_party_mind_reading"),
        ("她在等你主动", "third_party_mind_reading"), ("对方早已做出决定", "third_party_mind_reading"),
        ("他并不是真想离开", "third_party_mind_reading"), ("她嘴上拒绝但心里接受", "third_party_mind_reading"),
        ("买币", "financial_instruction"), ("卖币", "financial_instruction"),
        ("买这只股", "financial_instruction"), ("赶紧入场", "financial_instruction"),
        ("建议建仓", "financial_instruction"), ("追涨", "financial_instruction"),
        ("做空", "financial_instruction"), ("上杠杆", "financial_instruction"),
        ("把药停了", "medical_instruction"), ("少吃一点药", "medical_instruction"),
        ("不用看医生", "medical_instruction"), ("这是抑郁症", "medical_instruction"),
        ("这不是大问题", "medical_instruction"), ("自己调整剂量", "medical_instruction"),
    ],
)
def test_normalized_narrative_red_team_variants(
    text, error, valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = with_text(valid_interpretation, text)
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert error in exc.value.errors


def test_unknown_evidence_id_is_rejected(valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis):
    payload = with_text(valid_interpretation, "请核对现实条件。", evidence_ids=["E999"])
    with pytest.raises(InterpretationValidationError, match="unknown_evidence_id"):
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)


@pytest.mark.parametrize(
    ("field", "key", "value", "error"),
    [
        ("plain_language_explanation", "narrative_kind", "ACTION_OPTION", "plain_language_explanation_narrative_kind_mismatch"),
        ("real_world_advice", "epistemic_basis", "CHART_EVIDENCE", "real_world_advice_epistemic_basis_mismatch"),
        ("review_questions", "text", "请核对现实反馈。", "review_question_not_question"),
    ],
)
def test_structured_narrative_roles_are_enforced(
    field, key, value, error, valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis
):
    payload = valid_interpretation.model_dump(mode="json")
    payload[field][0][key] = value
    with pytest.raises(InterpretationValidationError) as exc:
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
    assert error in exc.value.errors


def test_action_option_requires_noncoercive_prefix(valid_interpretation, phase2_request, phase2_knowledge, phase2_synthesis):
    payload = with_text(valid_interpretation, "立即执行这个方案。", field="real_world_advice")
    with pytest.raises(InterpretationValidationError, match="action_option_not_noncoercive"):
        validate(payload, phase2_request, phase2_knowledge, phase2_synthesis)
