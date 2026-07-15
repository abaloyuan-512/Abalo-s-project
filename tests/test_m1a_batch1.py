"""M1-A Batch 1 intake, Chart-only core, and safety-boundary acceptance tests."""

from __future__ import annotations

import ast
import inspect
from dataclasses import fields
from pathlib import Path

import pytest

from abalo_iching.application.m1a_request import M1AIntake, build_m1a_intake
from abalo_iching.application.sites_meihua_service import _gate
from abalo_iching.application.sites_meihua_service_v2 import CONTRACT_VERSION_V2
from abalo_iching.application.sites_structured_question_v1 import (
    ALLOWED_GOALS,
    TEMPLATE_VERSION,
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)
from abalo_iching.interpretation import knowledge as knowledge_module
from abalo_iching.interpretation.enums import NarrativeReleaseStatus
from abalo_iching.interpretation.m1a_context import (
    M1AEvidenceRole,
    M1AProgramContext,
    M1ASafeEvidenceProposition,
    build_m1a_program_context,
    freeze_safe_evidence_allowlist,
)
from abalo_iching.interpretation.release import narrative_release_snapshot
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer
from abalo_iching.meihua.enums import EvidencePolarity, EvidenceStrength
from abalo_iching.meihua.models import MeihuaChart, MeihuaInput


def _intake(domain: QuestionDomain, goal: DecisionGoal, horizon: TimeHorizon) -> M1AIntake:
    question, template_version = generate_structured_question(domain, goal, horizon)
    return build_m1a_intake(
        question_id=f"synthetic-{domain.value}-{goal.value}-{horizon.value}",
        question_domain=domain,
        decision_goal=goal,
        time_horizon=horizon,
        normalized_question=question,
        question_template_version=template_version,
        contract_version=CONTRACT_VERSION_V2,
        is_synthetic=True,
    )


def test_all_17_v2_domain_goal_combinations_build_m1a_intake():
    intakes = [
        _intake(domain, goal, TimeHorizon.CURRENT)
        for domain, allowed_goals in ALLOWED_GOALS.items()
        for goal in allowed_goals
    ]
    assert len(intakes) == 17
    assert {(item.question_domain, item.decision_goal) for item in intakes} == {
        (domain, goal) for domain, goals in ALLOWED_GOALS.items() for goal in goals
    }


def test_all_three_illegal_domain_goal_combinations_are_rejected():
    illegal = [
        (domain, goal)
        for domain in QuestionDomain
        for goal in DecisionGoal
        if goal not in ALLOWED_GOALS[domain]
    ]
    assert len(illegal) == 3
    for domain, goal in illegal:
        with pytest.raises(ValueError, match="allowed combination"):
            _intake(domain, goal, TimeHorizon.CURRENT)


def test_all_time_horizons_preserve_v2_enum_type_and_value():
    for horizon in TimeHorizon:
        intake = _intake(QuestionDomain.WORK_CAREER, DecisionGoal.PLAN_NEXT_STEP, horizon)
        assert type(intake.time_horizon) is TimeHorizon
        assert intake.time_horizon is horizon
        assert intake.time_horizon.value == horizon.value


def test_normalized_question_and_template_version_remain_server_authoritative():
    domain = QuestionDomain.PERSONAL_PLANNING
    goal = DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES
    horizon = TimeHorizon.NEXT_QUARTER
    intake = _intake(domain, goal, horizon)
    assert (intake.normalized_question, intake.question_template_version) == generate_structured_question(
        domain, goal, horizon
    )
    with pytest.raises(ValueError, match="server-owned"):
        build_m1a_intake(
            question_id="synthetic-tampered",
            question_domain=domain,
            decision_goal=goal,
            time_horizon=horizon,
            normalized_question="客户端自由问题",
            question_template_version=TEMPLATE_VERSION,
            contract_version=CONTRACT_VERSION_V2,
            is_synthetic=True,
        )


def test_m1a_intake_is_a_strict_narrow_field_set_without_chart_context_or_numbers():
    assert {item.name for item in fields(M1AIntake)} == {
        "question_id",
        "question_domain",
        "decision_goal",
        "time_horizon",
        "normalized_question",
        "question_template_version",
        "contract_version",
        "is_synthetic",
    }
    forbidden = {
        "numbers",
        "first_number",
        "second_number",
        "third_number",
        "chart",
        "real_world_context",
        "knowledge",
        "conclusion",
        "evidence",
    }
    assert forbidden.isdisjoint({item.name for item in fields(M1AIntake)})


def test_m1a_intake_requires_v2_enum_instances_and_synthetic_marker():
    question, version = generate_structured_question(
        QuestionDomain.WORK_CAREER,
        DecisionGoal.PLAN_NEXT_STEP,
        TimeHorizon.CURRENT,
    )
    common = {
        "question_id": "synthetic-strict-types",
        "question_domain": QuestionDomain.WORK_CAREER,
        "decision_goal": DecisionGoal.PLAN_NEXT_STEP,
        "time_horizon": TimeHorizon.CURRENT,
        "normalized_question": question,
        "question_template_version": version,
        "contract_version": CONTRACT_VERSION_V2,
        "is_synthetic": True,
    }
    with pytest.raises(TypeError, match="Contract V2 enum"):
        build_m1a_intake(**{**common, "question_domain": "WORK_CAREER"})
    with pytest.raises(ValueError, match="synthetic"):
        build_m1a_intake(**{**common, "is_synthetic": False})


def test_program_context_retains_no_chart_input_or_raw_numbers(phase2_chart):
    context = build_m1a_program_context(phase2_chart)
    assert isinstance(context, M1AProgramContext)
    field_names = {item.name for item in fields(context)}
    assert {"chart", "input", "numbers", "real_world_context", "knowledge"}.isdisjoint(field_names)
    assert not any(item.type in {MeihuaChart, MeihuaInput} for item in fields(context))
    assert context.provider_evidence_allowlist == ()


def test_program_private_evidence_is_a_deterministic_one_to_one_copy(phase2_chart):
    context = build_m1a_program_context(phase2_chart)
    assert len(context.private_chart_evidence) == len(phase2_chart.evidence)
    for private, canonical in zip(context.private_chart_evidence, phase2_chart.evidence, strict=True):
        assert (
            private.evidence_id,
            private.evidence_type,
            private.source_ref,
            private.fact,
            private.rule_statement,
            private.polarity,
            private.strength,
            private.data_version,
        ) == (
            canonical.evidence_id,
            canonical.evidence_type,
            canonical.source_ref,
            canonical.fact,
            canonical.rule_statement,
            canonical.polarity,
            canonical.strength,
            canonical.data_version,
        )


def test_m1a_chart_only_path_does_not_call_select_knowledge(monkeypatch, phase2_chart):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("select_knowledge must not be called")

    monkeypatch.setattr(knowledge_module, "select_knowledge", fail_if_called)
    context = build_m1a_program_context(phase2_chart)
    assert context.synthesis == ConclusionSynthesizer().synthesize_chart(phase2_chart)


def test_chart_only_synthesis_signature_and_output_have_zero_knowledge_influence(
    phase2_chart, phase2_knowledge
):
    signature = inspect.signature(ConclusionSynthesizer.synthesize_chart)
    assert tuple(signature.parameters) == ("self", "chart")
    first = ConclusionSynthesizer().synthesize_chart(phase2_chart)
    changed_knowledge = phase2_knowledge.model_copy(
        update={"unreviewed_notice": "SHOULD NEVER ENTER M1-A", "access_mode": "INTERNAL_DRAFT_PREVIEW"}
    )
    assert changed_knowledge != phase2_knowledge
    second = ConclusionSynthesizer().synthesize_chart(phase2_chart)
    assert first == second
    assert "SHOULD NEVER ENTER M1-A" not in first.warnings


def test_chart_only_core_matches_phase2_and_phase2_notice_wrapper_is_unchanged(
    phase2_chart, phase2_knowledge
):
    synthesizer = ConclusionSynthesizer()
    chart_only = synthesizer.synthesize_chart(phase2_chart)
    legacy = synthesizer.synthesize(phase2_chart, phase2_knowledge)
    chart_payload = chart_only.model_dump(mode="json")
    legacy_payload = legacy.model_dump(mode="json")
    assert {key: value for key, value in chart_payload.items() if key != "warnings"} == {
        key: value for key, value in legacy_payload.items() if key != "warnings"
    }
    expected_legacy_warnings = list(chart_only.warnings)
    if phase2_knowledge.unreviewed_notice:
        expected_legacy_warnings.append(phase2_knowledge.unreviewed_notice)
        assert phase2_knowledge.unreviewed_notice not in chart_only.warnings
    assert legacy.warnings == expected_legacy_warnings
    assert synthesizer.synthesize(phase2_chart, phase2_knowledge) == legacy


def test_interpretation_m1a_context_has_no_reverse_application_dependency():
    import abalo_iching.interpretation.m1a_context as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    assert not any(name == "abalo_iching.application" or name.startswith("abalo_iching.application.") for name in imported_modules)


def test_safe_evidence_interface_preserves_identity_direction_strength_roles_conditions_and_hashes():
    assert {item.name for item in fields(M1ASafeEvidenceProposition)} == {
        "canonical_evidence_id",
        "provider_evidence_ref",
        "safe_evidence_content",
        "polarity",
        "strength",
        "allowed_roles",
        "conditions",
        "private_mapping_hash",
        "provider_payload_hash",
    }
    first = M1ASafeEvidenceProposition(
        canonical_evidence_id="E02",
        provider_evidence_ref="EV-001",
        safe_evidence_content="程序裁剪后的安全命题一",
        polarity=EvidencePolarity.POSITIVE,
        strength=EvidenceStrength.STRONG,
        allowed_roles=(M1AEvidenceRole.EXPLANATION, M1AEvidenceRole.ACTION_OPTION),
        conditions=("现实条件一",),
        private_mapping_hash="a" * 64,
        provider_payload_hash="b" * 64,
    )
    second = M1ASafeEvidenceProposition(
        canonical_evidence_id="E03",
        provider_evidence_ref="EV-002",
        safe_evidence_content="程序裁剪后的安全命题二",
        polarity=EvidencePolarity.NEGATIVE,
        strength=EvidenceStrength.WEAK,
        allowed_roles=(M1AEvidenceRole.CONDITION, M1AEvidenceRole.REVIEW_QUESTION),
        conditions=("现实条件二",),
        private_mapping_hash="c" * 64,
        provider_payload_hash="d" * 64,
    )
    assert freeze_safe_evidence_allowlist((first, second)) == (first, second)
    collapsed = M1ASafeEvidenceProposition(
        canonical_evidence_id="E04",
        provider_evidence_ref="EV-003",
        safe_evidence_content=first.safe_evidence_content,
        polarity=EvidencePolarity.MIXED,
        strength=EvidenceStrength.MEDIUM,
        allowed_roles=(M1AEvidenceRole.EXPLANATION,),
        conditions=(),
        private_mapping_hash="e" * 64,
        provider_payload_hash="f" * 64,
    )
    with pytest.raises(ValueError, match="generic content"):
        freeze_safe_evidence_allowlist((first, collapsed))


def test_release_gate_remains_unverified_and_closed():
    snapshot = narrative_release_snapshot()
    gate = _gate()
    assert snapshot.narrative_release_status is NarrativeReleaseStatus.UNVERIFIED
    assert gate["narrative_release_status"] == "UNVERIFIED"
    assert gate["should_charge"] is False
    assert gate["formal_report_persistence_allowed"] is False
    assert gate["closed_beta_allowed"] is False
