import pytest
from datetime import datetime
import json
from pydantic import ValidationError

from abalo_iching.interpretation import knowledge as knowledge_module
from abalo_iching.interpretation.enums import KnowledgeAccessMode, KnowledgeReviewStatus
from abalo_iching.interpretation.knowledge import KnowledgeAccessPolicy, load_interpretation_knowledge, select_knowledge
from abalo_iching.interpretation.models import HexagramKnowledge, KnowledgeEvidence, LineKnowledge
from abalo_iching.interpretation.prompt_builder import PromptBuilder
from abalo_iching.interpretation.validators import InterpretationValidator
from abalo_iching.interpretation.exceptions import InterpretationValidationError
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider, build_conservative_fake_output
from abalo_iching.interpretation.service import InterpretationService
from abalo_iching.meihua.enums import EvidencePolarity, EvidenceStrength


def approved_hex(record, **overrides):
    update = {
        "review_status": KnowledgeReviewStatus.APPROVED,
        "core_theme": "经人工核验的核心主题",
        "situation_pattern": "经人工核验的情境模式",
        "action_tendency": "谨慎核验现实条件",
        "prohibited_inferences": ["不得读心"],
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-11T10:00:00+08:00",
        "approved_by": "approver-b",
        "approved_at": "2026-07-11T11:00:00+08:00",
        "review_notes": "reviewed",
        "approval_notes": "approved",
        "evidence_direction": EvidencePolarity.MIXED,
        "evidence_strength": EvidenceStrength.MEDIUM,
    }
    update.update(overrides)
    return record.model_copy(update=update)


def approved_line(record, **overrides):
    update = {
        "review_status": KnowledgeReviewStatus.APPROVED,
        "literal_paraphrase": "经人工核验的字面释义",
        "core_theme": "经人工核验的爻位主题",
        "action_tendency": "谨慎核验现实条件",
        "prohibited_inferences": ["不得读心"],
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-11T10:00:00+08:00",
        "approved_by": "approver-b",
        "approved_at": "2026-07-11T11:00:00+08:00",
        "review_notes": "reviewed",
        "approval_notes": "approved",
        "evidence_direction": EvidencePolarity.MIXED,
        "evidence_strength": EvidenceStrength.MEDIUM,
    }
    update.update(overrides)
    return record.model_copy(update=update)


def reviewed_hex(record, **overrides):
    update = {
        "review_status": KnowledgeReviewStatus.REVIEWED,
        "core_theme": "已复核主题",
        "situation_pattern": "已复核情境",
        "action_tendency": "核对现实条件",
        "prohibited_inferences": ["不得推断欺骗"],
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-11T10:00:00+08:00",
        "evidence_direction": EvidencePolarity.MIXED,
        "evidence_strength": EvidenceStrength.MEDIUM,
    }
    update.update(overrides)
    return record.model_copy(update=update)


def reviewed_line(record, **overrides):
    update = {
        "review_status": KnowledgeReviewStatus.REVIEWED,
        "literal_paraphrase": "已复核字面释义",
        "core_theme": "已复核爻位主题",
        "action_tendency": "核对现实条件",
        "prohibited_inferences": ["不得推断欺骗"],
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-11T10:00:00+08:00",
        "evidence_direction": EvidencePolarity.MIXED,
        "evidence_strength": EvidenceStrength.MEDIUM,
    }
    update.update(overrides)
    return record.model_copy(update=update)


def draft_hex(record):
    return record.model_copy(update={
        "review_status": KnowledgeReviewStatus.DRAFT,
        "core_theme": "草稿主题",
        "situation_pattern": "草稿情境",
        "action_tendency": "仅供内部预览",
        "prohibited_inferences": ["不得推断欺骗"],
        "evidence_direction": EvidencePolarity.MIXED,
        "evidence_strength": EvidenceStrength.WEAK,
    })


def test_all_knowledge_starts_canonical_only_and_blank():
    hexagrams, lines = load_interpretation_knowledge()
    assert len(hexagrams) == 64 and len(lines) == 384
    records = [*hexagrams.values(), *lines.values()]
    assert {item.review_status for item in records} == {KnowledgeReviewStatus.CANONICAL_ONLY}
    assert all(item.reviewer is None and item.approved_by is None for item in records)


def test_canonical_only_is_not_selected_as_domain_knowledge(phase2_chart):
    selection = select_knowledge(phase2_chart)
    assert selection.hexagram_knowledge is None
    assert selection.line_knowledge is None
    assert selection.allowed_knowledge_evidence_ids == []


def test_draft_only_available_in_internal_draft_preview(monkeypatch, phase2_chart):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    drafted_hexagrams, drafted_lines = dict(hexagrams), dict(lines)
    drafted_hexagrams[number] = hexagrams[number].model_copy(update={"review_status": KnowledgeReviewStatus.DRAFT})
    drafted_lines[(number, position)] = lines[(number, position)].model_copy(update={"review_status": KnowledgeReviewStatus.DRAFT})
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (drafted_hexagrams, drafted_lines))
    assert select_knowledge(phase2_chart).hexagram_knowledge is None
    review = select_knowledge(phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW))
    assert review.hexagram_knowledge is None
    preview = select_knowledge(
        phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW)
    )
    assert preview.hexagram_knowledge.review_status is KnowledgeReviewStatus.DRAFT
    assert preview.allowed_knowledge_evidence_ids == [f"D-H-{number}", f"D-L-{number}-{position}"]
    assert all(item.preview for item in preview.knowledge_evidence)
    assert preview.is_preview is True


def test_blank_model_copy_cannot_promote_to_approved():
    record = next(iter(load_interpretation_knowledge()[0].values()))
    with pytest.raises(ValidationError):
        record.model_copy(update={"review_status": KnowledgeReviewStatus.APPROVED})


@pytest.mark.parametrize("missing", ["reviewer", "reviewed_at", "approved_by", "approved_at", "core_theme"])
def test_approved_requires_complete_audit_and_content(missing):
    record = next(iter(load_interpretation_knowledge()[0].values()))
    update = approved_hex(record).model_dump()
    update[missing] = None
    with pytest.raises(ValidationError):
        HexagramKnowledge.model_validate(update)


def test_approved_line_requires_key_content():
    record = next(iter(load_interpretation_knowledge()[1].values()))
    payload = approved_line(record).model_dump()
    payload["literal_paraphrase"] = None
    with pytest.raises(ValidationError):
        LineKnowledge.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer", "x"),
        ("reviewer", "   "),
        ("reviewed_at", "x"),
        ("approved_by", "x"),
        ("approved_by", "   "),
        ("approved_at", "x"),
        ("reviewed_at", datetime(2026, 7, 11, 10, 0)),
        ("approved_at", datetime(2026, 7, 11, 11, 0)),
    ],
)
def test_review_identity_and_times_are_strict(field, value):
    record = next(iter(load_interpretation_knowledge()[0].values()))
    payload = approved_hex(record).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        HexagramKnowledge.model_validate(payload)


def test_approval_time_cannot_precede_review_time():
    record = next(iter(load_interpretation_knowledge()[0].values()))
    payload = approved_hex(record).model_dump()
    payload["approved_at"] = "2026-07-11T09:00:00+08:00"
    with pytest.raises(ValidationError, match="approved_at cannot be earlier"):
        HexagramKnowledge.model_validate(payload)


def test_only_complete_approved_entries_receive_stable_ids(monkeypatch, phase2_chart):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    approved_hexagrams, approved_lines = dict(hexagrams), dict(lines)
    approved_hexagrams[number] = approved_hex(hexagrams[number])
    approved_lines[(number, position)] = approved_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (approved_hexagrams, approved_lines))
    selection = select_knowledge(phase2_chart)
    assert selection.allowed_knowledge_evidence_ids == [f"K-H-{number}", f"K-L-{number}-{position}"]
    assert all(not item.preview for item in selection.knowledge_evidence)


def test_approved_knowledge_content_enters_production_prompt_and_trace(
    monkeypatch, phase2_chart, phase2_request, phase2_synthesis
):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    changed_hexagrams, changed_lines = dict(hexagrams), dict(lines)
    changed_hexagrams[number] = approved_hex(hexagrams[number], core_theme="生产知识正文")
    changed_lines[(number, position)] = approved_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (changed_hexagrams, changed_lines))
    selection = select_knowledge(phase2_chart)
    payload = json.loads(PromptBuilder().build(phase2_request, selection, phase2_synthesis).user_payload_json)
    assert payload["allowed_knowledge_evidence"][0]["evidence_id"] == f"K-H-{number}"
    assert payload["allowed_knowledge_evidence"][0]["core_theme"] == "生产知识正文"
    assert payload["allowed_knowledge_evidence"][0]["prohibited_inferences"]
    from abalo_iching.interpretation.renderer import ProgramInterpretationRenderer
    rendered = ProgramInterpretationRenderer().render(phase2_request, selection, phase2_synthesis)
    assert rendered.knowledge_evidence_trace == selection.knowledge_evidence


def test_reviewed_and_draft_evidence_reach_only_internal_preview_prompts(monkeypatch, phase2_chart, phase2_request, phase2_synthesis):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    changed_hexagrams, changed_lines = dict(hexagrams), dict(lines)
    changed_hexagrams[number] = draft_hex(hexagrams[number])
    changed_lines[(number, position)] = reviewed_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (changed_hexagrams, changed_lines))
    assert select_knowledge(phase2_chart).knowledge_evidence == []
    review = select_knowledge(phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW))
    assert [item.evidence_id for item in review.knowledge_evidence] == [f"R-L-{number}-{position}"]
    draft = select_knowledge(phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW))
    assert {item.evidence_id[0] for item in draft.knowledge_evidence} == {"D", "R"}
    prompt = json.loads(PromptBuilder().build(phase2_request, draft, phase2_synthesis).user_payload_json)
    assert {item["evidence_id"][0] for item in prompt["allowed_knowledge_evidence"]} == {"D", "R"}
    assert all(item["preview"] for item in prompt["allowed_knowledge_evidence"])


def test_preview_knowledge_cannot_be_relabelled_as_production(
    monkeypatch, phase2_chart, phase2_request, phase2_synthesis, valid_interpretation
):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    changed_lines = dict(lines)
    changed_lines[(number, position)] = reviewed_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (hexagrams, changed_lines))
    review = select_knowledge(phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW))
    forged = review.model_copy(update={"access_mode": "PRODUCTION", "is_preview": False})
    payload = valid_interpretation.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_ids"] = [f"R-L-{number}-{position}"]
    with pytest.raises(InterpretationValidationError, match="preview_knowledge_in_production"):
        InterpretationValidator().validate(payload, phase2_request, forged, phase2_synthesis)


def test_preview_knowledge_id_cannot_be_spoofed_to_k(monkeypatch, phase2_chart):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    changed_lines = dict(lines)
    changed_lines[(number, position)] = reviewed_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (hexagrams, changed_lines))
    item = select_knowledge(
        phase2_chart, policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW)
    ).knowledge_evidence[0]
    payload = item.model_dump()
    payload["evidence_id"] = f"K-L-{number}-{position}"
    with pytest.raises(ValidationError):
        KnowledgeEvidence.model_validate(payload)


def test_knowledge_direction_and_prohibited_inference_are_validated(
    monkeypatch, phase2_chart, phase2_request, phase2_synthesis, valid_interpretation
):
    hexagrams, lines = load_interpretation_knowledge()
    number = phase2_chart.base_hexagram.king_wen_number
    changed_hexagrams = dict(hexagrams)
    changed_hexagrams[number] = approved_hex(
        hexagrams[number],
        evidence_direction=EvidencePolarity.NEGATIVE,
        prohibited_inferences=["不得推断欺骗"],
    )
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (changed_hexagrams, lines))
    selection = select_knowledge(phase2_chart)
    payload = valid_interpretation.model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_ids"] = [f"K-H-{number}"]
    payload["plain_language_explanation"][0]["text"] = "这一知识证据明确有利并证明成功。"
    with pytest.raises(InterpretationValidationError) as exc:
        InterpretationValidator().validate(payload, phase2_request, selection, phase2_synthesis)
    assert "negative_evidence_semantic_reversal" in exc.value.errors
    payload["plain_language_explanation"][0]["text"] = "这一知识说明存在欺骗。"
    with pytest.raises(InterpretationValidationError) as exc:
        InterpretationValidator().validate(payload, phase2_request, selection, phase2_synthesis)
    assert "knowledge_prohibited_inference" in exc.value.errors


def test_internal_review_service_really_carries_reviewed_evidence_without_charge(
    monkeypatch, phase2_chart, phase2_request, phase2_synthesis
):
    hexagrams, lines = load_interpretation_knowledge()
    number, position = phase2_chart.base_hexagram.king_wen_number, phase2_chart.moving_line
    changed_lines = dict(lines)
    changed_lines[(number, position)] = reviewed_line(lines[(number, position)])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (hexagrams, changed_lines))
    fake = build_conservative_fake_output(phase2_request, phase2_synthesis)
    result = InterpretationService(
        FakeInterpretationProvider([fake]),
        knowledge_access_policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_REVIEW),
    ).interpret(phase2_request)
    assert [item.evidence_id for item in result.interpretation.program_content.knowledge_evidence_trace] == [
        f"R-L-{number}-{position}"
    ]
    assert result.is_preview is True
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False


def test_internal_draft_service_really_carries_draft_evidence_without_charge(
    monkeypatch, phase2_chart, phase2_request, phase2_synthesis
):
    hexagrams, lines = load_interpretation_knowledge()
    number = phase2_chart.base_hexagram.king_wen_number
    changed_hexagrams = dict(hexagrams)
    changed_hexagrams[number] = draft_hex(hexagrams[number])
    monkeypatch.setattr(knowledge_module, "load_interpretation_knowledge", lambda: (changed_hexagrams, lines))
    fake = build_conservative_fake_output(phase2_request, phase2_synthesis)
    result = InterpretationService(
        FakeInterpretationProvider([fake]),
        knowledge_access_policy=KnowledgeAccessPolicy(KnowledgeAccessMode.INTERNAL_DRAFT_PREVIEW),
    ).interpret(phase2_request)
    assert [item.evidence_id for item in result.interpretation.program_content.knowledge_evidence_trace] == [
        f"D-H-{number}"
    ]
    assert result.is_preview is True
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
