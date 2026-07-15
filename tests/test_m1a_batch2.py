"""M1-A Batch 2 safe Provider path and static narrative closure acceptance tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from abalo_iching.application.m1a_request import build_m1a_intake
from abalo_iching.application.sites_meihua_service_v2 import CONTRACT_VERSION_V2
from abalo_iching.application.sites_structured_question_v1 import (
    ALLOWED_GOALS,
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)
from abalo_iching.interpretation.enums import NarrativeReleaseStatus, ServiceStatus, SubjectScope
from abalo_iching.interpretation.exceptions import (
    InterpretationValidationError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderIncompleteError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from abalo_iching.interpretation.m1a_context import (
    M1AEvidenceRole,
    build_m1a_program_context,
    m1a_program_hash,
)
from abalo_iching.interpretation.m1a_evidence_catalog import (
    M1AEvidenceCatalogError,
    build_m1a_evidence_catalog,
)
from abalo_iching.interpretation.m1a_prompt_builder import (
    M1A_CONTRACT_VERSION,
    M1A_NARRATIVE_ASSEMBLY_VERSION,
    M1A_PROMPT_VERSION,
    M1A_PROVIDER_SCHEMA_VERSION,
    M1APromptPayloadError,
    M1APromptBuilder,
)
from abalo_iching.interpretation.m1a_service import M1AFailureCode, M1AService
from abalo_iching.interpretation.m1a_validator import M1A_VALIDATOR_VERSION, M1AValidator
from abalo_iching.interpretation.models import (
    AINarrativeDraftClaim,
    AINarrativeDraftContent,
    ProviderResult,
)
from abalo_iching.meihua.enums import BodyUseRelation, EvidencePolarity, SeasonalStrength


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _intake(
    domain: QuestionDomain = QuestionDomain.WORK_CAREER,
    goal: DecisionGoal = DecisionGoal.PLAN_NEXT_STEP,
    horizon: TimeHorizon = TimeHorizon.CURRENT,
):
    question, template_version = generate_structured_question(domain, goal, horizon)
    return build_m1a_intake(
        question_id=f"m1a-b2-{domain.value}-{goal.value}-{horizon.value}",
        question_domain=domain,
        decision_goal=goal,
        time_horizon=horizon,
        normalized_question=question,
        question_template_version=template_version,
        contract_version=CONTRACT_VERSION_V2,
        is_synthetic=True,
    )


_DOMAIN_ACTION = {
    QuestionDomain.WORK_CAREER: "可以考虑先核实工作准备和求职流程反馈，再做可撤回的小步验证。",
    QuestionDomain.PROJECT_COOPERATION: "可以考虑先澄清项目分工、资源和承诺，再做可撤回的小步验证。",
    QuestionDomain.RELATIONSHIP_COMMUNICATION: "可以考虑先表达自身沟通边界，并观察和记录现实反馈。",
    QuestionDomain.PERSONAL_PLANNING: "可以考虑先调整自身优先级、精力和节奏，再记录现实反馈。",
}
_GOAL_FOCUS = {
    DecisionGoal.IDENTIFY_OBSTACLES: "重点核实阻力、支持条件和风险信号。",
    DecisionGoal.PLAN_NEXT_STEP: "把它作为下一步小步验证。",
    DecisionGoal.PREPARE_COMMUNICATION: "先准备沟通、表达和询问。",
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: "同步调整投入、承诺和边界。",
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: "继续观察、核实并记录反馈信号。",
}


def _valid_draft(intake, catalog) -> AINarrativeDraftContent:
    explanation_ref = catalog.refs_for_role(M1AEvidenceRole.EXPLANATION)[0]
    action_ref = catalog.refs_for_role(M1AEvidenceRole.ACTION_OPTION)[0]
    review_ref = catalog.refs_for_role(M1AEvidenceRole.REVIEW_QUESTION)[0]
    condition_refs = catalog.refs_for_role(M1AEvidenceRole.CONDITION)
    return AINarrativeDraftContent(
        plain_language_explanation=[
            AINarrativeDraftClaim(
                text="这些安全证据可能提示需要核实现实条件和反馈，避免提前形成结论。",
                evidence_refs=[explanation_ref],
                subject_scope=SubjectScope.SITUATION,
            )
        ],
        real_world_advice=[
            AINarrativeDraftClaim(
                text=f"{_DOMAIN_ACTION[intake.question_domain]}{_GOAL_FOCUS[intake.decision_goal]}",
                evidence_refs=[action_ref],
                subject_scope=SubjectScope.PROCESS,
            )
        ],
        conditions_that_change_outcome=(
            [
                AINarrativeDraftClaim(
                    text="如果这些现实条件发生变化，可以重新核实并复盘。",
                    evidence_refs=[condition_refs[0]],
                    subject_scope=SubjectScope.SITUATION,
                )
            ]
            if condition_refs
            else []
        ),
        review_questions=[
            AINarrativeDraftClaim(
                text="你能观察并记录哪些现实反馈信号？",
                evidence_refs=[review_ref],
                subject_scope=SubjectScope.USER,
            )
        ],
    )


class RecordingProvider:
    def __init__(self, outputs, *, provider_name="FAKE", context_to_mutate=None):
        self.outputs = list(outputs)
        self.provider_name = provider_name
        self.context_to_mutate = context_to_mutate
        self.prompts = []

    def generate(self, prompt, *, attempt_number):
        self.prompts.append(prompt)
        if self.context_to_mutate is not None:
            self.context_to_mutate.synthesis.warnings.append("tampered-by-provider")
        item = self.outputs.pop(0)
        if isinstance(item, Exception):
            raise item
        return ProviderResult(
            parsed_output=item,
            response_id=f"m1a-fake-{attempt_number}",
            model="m1a-static-fake",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            latency_ms=0,
            attempt_number=attempt_number,
            provider_name=self.provider_name,
            prompt_version=prompt.prompt_version,
        )


@pytest.fixture
def m1a_context(phase2_chart):
    return build_m1a_program_context(phase2_chart)


@pytest.fixture
def m1a_catalog(m1a_context):
    return build_m1a_evidence_catalog(m1a_context)


def test_provider_payload_is_exact_whitelist_and_contains_no_private_or_forbidden_fields(m1a_context, m1a_catalog):
    prompt = M1APromptBuilder().build(_intake(), m1a_context, m1a_catalog)
    payload = json.loads(prompt.user_payload_json)
    assert set(payload) == {
        "task",
        "prompt_version",
        "provider_schema_version",
        "narrative_assembly_version",
        "m1a_contract_version",
        "structured_intake",
        "normalized_question",
        "evidence_reference_catalog",
        "evidence_role_constraints",
        "domain_narrative_constraints",
        "program_owned_constraints",
        "version_snapshot",
        "repair_context",
    }
    serialized = prompt.user_payload_json.lower()
    for forbidden in (
        "canonical_evidence_id",
        "private_mapping_hash",
        "private_catalog_hash",
        "source_ref",
        "rule_statement",
        "real_world_context",
        "knowledge",
        "base_hexagram",
        "mutual_hexagram",
        "changed_hexagram",
        "moving_line",
        "conclusion_level",
    ):
        assert forbidden not in serialized
    for item in m1a_context.private_chart_evidence:
        assert item.fact not in prompt.user_payload_json
        assert item.rule_statement not in prompt.user_payload_json
        assert item.source_ref not in prompt.user_payload_json


@pytest.mark.parametrize("extra_field", ["real_world_context", "knowledge", "numbers", "conclusion"])
def test_provider_payload_fails_closed_on_every_non_whitelist_sensitive_field(
    extra_field, m1a_context, m1a_catalog
):
    builder = M1APromptBuilder()
    prompt = builder.build(_intake(), m1a_context, m1a_catalog)
    payload = json.loads(prompt.user_payload_json)
    payload[extra_field] = "forbidden"
    with pytest.raises(M1APromptPayloadError):
        builder.validate_payload(payload, context=m1a_context, catalog=m1a_catalog, is_repair=False)


def test_non_m1a_intake_with_real_context_is_rejected_before_prompt(m1a_context, m1a_catalog):
    valid = _intake()
    forged = SimpleNamespace(
        **{name: getattr(valid, name) for name in valid.__dataclass_fields__},
        real_world_context="client text",
    )
    with pytest.raises(M1APromptPayloadError, match="EXACT_NARROW_BOUNDARY"):
        M1APromptBuilder().build(forged, m1a_context, m1a_catalog)


def test_unverifiable_catalog_hash_is_rejected_before_provider(m1a_context, m1a_catalog):
    builder = M1APromptBuilder()
    prompt = builder.build(_intake(), m1a_context, m1a_catalog)
    payload = json.loads(prompt.user_payload_json)
    payload["evidence_reference_catalog"]["entries"][0]["display_payload_hash"] = "0" * 64
    with pytest.raises(M1APromptPayloadError, match="CATALOG_PAYLOAD_MISMATCH"):
        builder.validate_payload(payload, context=m1a_context, catalog=m1a_catalog, is_repair=False)


def test_catalog_contains_exactly_current_chart_evidence_and_provider_view_hides_private_mapping(
    m1a_context, m1a_catalog
):
    assert {item.canonical_evidence_id for item in m1a_catalog.entries} == {
        item.evidence_id for item in m1a_context.private_chart_evidence
    }
    provider_payload = m1a_catalog.to_provider_payload()
    serialized = _stable_json(provider_payload)
    assert "canonical_evidence_id" not in serialized
    assert "private_mapping_hash" not in serialized
    assert "private_catalog_hash" not in serialized
    assert all(set(item) == {
        "evidence_ref",
        "safe_evidence_content",
        "polarity",
        "strength",
        "allowed_roles",
        "conditions",
        "display_payload_hash",
    } for item in provider_payload["entries"])


@pytest.mark.parametrize("prefix", ["K-", "R-", "D-"])
def test_catalog_rejects_all_knowledge_evidence_prefixes(prefix, m1a_context):
    first = replace(m1a_context.private_chart_evidence[0], evidence_id=f"{prefix}H-1")
    forged = replace(m1a_context, private_chart_evidence=(first, *m1a_context.private_chart_evidence[1:]))
    with pytest.raises(M1AEvidenceCatalogError, match="KNOWLEDGE_EVIDENCE_FORBIDDEN"):
        build_m1a_evidence_catalog(forged)


def test_service_fails_closed_when_catalog_source_is_not_current_chart(m1a_context):
    forged = replace(
        m1a_context,
        private_chart_evidence=(
            replace(m1a_context.private_chart_evidence[0], source_ref=""),
            *m1a_context.private_chart_evidence[1:],
        ),
    )
    result = M1AService(RecordingProvider([])).interpret(_intake(), forged)
    assert result.failure_code is M1AFailureCode.PROGRAM_INTEGRITY
    assert result.assembly is None


def test_private_and_provider_hashes_are_independently_reproducible(m1a_context, m1a_catalog):
    m1a_catalog.validate_integrity(m1a_context)
    provider_entries = m1a_catalog.to_provider_payload()["entries"]
    for entry in provider_entries:
        material = {key: value for key, value in entry.items() if key != "display_payload_hash"}
        assert hashlib.sha256(_stable_json(material).encode("utf-8")).hexdigest() == entry["display_payload_hash"]
    assert len(m1a_catalog.provider_catalog_hash) == 64
    assert len(m1a_catalog.private_catalog_hash) == 64
    assert m1a_catalog.provider_catalog_hash != m1a_catalog.private_catalog_hash
    tampered = replace(
        m1a_catalog,
        entries=(
            replace(m1a_catalog.entries[0], private_mapping_hash="0" * 64),
            *m1a_catalog.entries[1:],
        ),
    )
    with pytest.raises(M1AEvidenceCatalogError, match="PRIVATE_MAPPING_HASH_MISMATCH"):
        tampered.validate_integrity(m1a_context)


def test_safe_evidence_preserves_direction_strength_roles_and_distinct_content(m1a_catalog):
    assert len({item.safe_evidence_content for item in m1a_catalog.entries}) == len(m1a_catalog.entries)
    assert {item.polarity for item in m1a_catalog.entries} >= {
        EvidencePolarity.POSITIVE,
        EvidencePolarity.NEGATIVE,
        EvidencePolarity.MIXED,
        EvidencePolarity.NEUTRAL,
    }
    assert all(item.allowed_roles and len(item.provider_payload_hash) == 64 for item in m1a_catalog.entries)


def test_safe_condition_projection_preserves_distinct_conditions_without_chart_terms(phase2_chart):
    season = replace(
        phase2_chart.season_context,
        body_strength=SeasonalStrength.RESTING,
        initial_use_strength=SeasonalStrength.DEAD,
        changed_use_strength=SeasonalStrength.PROSPEROUS,
    )
    chart = replace(
        phase2_chart,
        initial_body_use_relation=BodyUseRelation.BODY_CONTROLS_USE,
        changed_body_use_relation=BodyUseRelation.BODY_CONTROLS_USE,
        season_context=season,
    )
    catalog = build_m1a_evidence_catalog(build_m1a_program_context(chart))
    conditions = [item.conditions for item in catalog.entries if item.conditions]
    assert len(conditions) == 2
    assert conditions[0] != conditions[1]
    serialized = _stable_json(catalog.to_provider_payload())
    assert not any(term in serialized for term in ["体方", "用方", "旺衰", "动爻", "本卦"])


@pytest.mark.parametrize(
    ("domain", "goal"),
    [(domain, goal) for domain, goals in ALLOWED_GOALS.items() for goal in goals],
)
def test_all_17_domain_goal_combinations_accept_legal_observation_and_action(
    domain, goal, m1a_catalog
):
    intake = _intake(domain, goal)
    assert M1AValidator().validate(_valid_draft(intake, m1a_catalog), intake, m1a_catalog)


@pytest.mark.parametrize(
    ("domain", "infiltration"),
    [
        (QuestionDomain.WORK_CAREER, "可以考虑建议投资并保证录用。"),
        (QuestionDomain.PROJECT_COOPERATION, "可以考虑通过融资保证项目成功。"),
        (QuestionDomain.RELATIONSHIP_COMMUNICATION, "可以考虑跟踪对方，因为对方爱你。"),
        (QuestionDomain.PERSONAL_PLANNING, "可以考虑接受抑郁症诊断并必须辞职。"),
    ],
)
def test_four_domain_adjacent_semantic_infiltration_is_rejected(domain, infiltration, m1a_catalog):
    goal = next(iter(ALLOWED_GOALS[domain]))
    intake = _intake(domain, goal)
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["real_world_advice"][0]["text"] = infiltration + _GOAL_FOCUS[goal]
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert f"M1A_{domain.value}_SEMANTIC_BOUNDARY_VIOLATION" in exc.value.errors


def test_unknown_evidence_short_ref_is_rejected(m1a_catalog):
    intake = _intake()
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["plain_language_explanation"][0]["evidence_refs"] = ["M1AEV99"]
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert "M1A_UNKNOWN_EVIDENCE_REF" in exc.value.errors


def test_evidence_role_mismatch_is_rejected(m1a_catalog):
    intake = _intake()
    explanation_only = next(
        item.provider_evidence_ref
        for item in m1a_catalog.entries
        if M1AEvidenceRole.ACTION_OPTION not in item.allowed_roles
    )
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["real_world_advice"][0]["evidence_refs"] = [explanation_only]
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert "M1A_EVIDENCE_ROLE_NOT_ALLOWED" in exc.value.errors


def test_negative_evidence_direction_reversal_is_rejected(m1a_catalog):
    intake = _intake()
    negative_action = next(
        item.provider_evidence_ref
        for item in m1a_catalog.entries
        if item.polarity is EvidencePolarity.NEGATIVE and M1AEvidenceRole.ACTION_OPTION in item.allowed_roles
    )
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["real_world_advice"][0].update(
        text="可以考虑立即推进，因为该证据明显有利；下一步仍记录反馈。",
        evidence_refs=[negative_action],
    )
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert "M1A_NEGATIVE_EVIDENCE_REVERSED" in exc.value.errors


def test_mixed_evidence_cannot_be_forced_to_one_direction(m1a_catalog):
    intake = _intake()
    mixed_ref = next(item.provider_evidence_ref for item in m1a_catalog.entries if item.polarity is EvidencePolarity.MIXED)
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["plain_language_explanation"][0].update(
        text="这些反馈可能明确有利，下一步可以马上推进。",
        evidence_refs=[mixed_ref],
    )
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert "M1A_MIXED_EVIDENCE_FORCED_DIRECTION" in exc.value.errors


def test_weak_evidence_strength_cannot_be_inflated(m1a_catalog):
    intake = _intake()
    weak_ref = next(item.provider_evidence_ref for item in m1a_catalog.entries if item.strength.value == "WEAK")
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["plain_language_explanation"][0].update(
        text="这些反馈可能明确证明结果，仍需记录现实信号。",
        evidence_refs=[weak_ref],
    )
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert "M1A_WEAK_EVIDENCE_STRENGTH_INFLATED" in exc.value.errors


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("这些反馈可能说明本卦与动爻已经确定，仍需核实。", "M1A_PROGRAM_FACT_RESTATEMENT"),
        ("这些反馈可能就是程序结论：明确不利，仍需核实。", "M1A_PROGRAM_CONCLUSION_FORBIDDEN"),
        ("这些反馈可能在未来三天内确定，仍需核实。", "M1A_TIME_JUDGMENT_FORBIDDEN"),
    ],
)
def test_program_facts_conclusion_and_time_are_rejected(text, expected, m1a_catalog):
    intake = _intake()
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["plain_language_explanation"][0]["text"] = text
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert expected in exc.value.errors


def test_provider_cannot_output_program_owned_metadata(m1a_catalog):
    intake = _intake()
    payload = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    payload["program_content"] = {"conclusion": "tampered"}
    with pytest.raises(InterpretationValidationError) as exc:
        M1AValidator().validate(payload, intake, m1a_catalog)
    assert any(item.startswith("schema:") for item in exc.value.errors)


def test_successful_service_assembly_attaches_authoritative_metadata_and_preserves_program(
    m1a_context, m1a_catalog
):
    intake = _intake()
    initial_hash = m1a_program_hash(m1a_context)
    provider = RecordingProvider([_valid_draft(intake, m1a_catalog)])
    result = M1AService(provider).interpret(intake, m1a_context)
    assert result.status is ServiceStatus.SUCCESS
    assert result.assembly is not None
    assert result.assembly.program_content is m1a_context
    assert result.assembly.audit.program_hash == initial_hash == m1a_program_hash(m1a_context)
    assert result.assembly.audit.prompt_version == M1A_PROMPT_VERSION
    assert result.assembly.audit.provider_schema_version == M1A_PROVIDER_SCHEMA_VERSION
    assert result.assembly.audit.validator_version == M1A_VALIDATOR_VERSION
    assert result.assembly.audit.narrative_assembly_version == M1A_NARRATIVE_ASSEMBLY_VERSION
    assert result.assembly.audit.m1a_contract_version == M1A_CONTRACT_VERSION
    claim = result.assembly.ai_content.plain_language_explanation[0]
    assert claim.narrative_kind.value == "EXPLANATION"
    assert claim.epistemic_basis.value == "CHART_EVIDENCE"
    assert claim.evidence_ids[0].startswith("E")
    assert all(
        item.evidence_id not in provider.prompts[0].user_payload_json
        for item in m1a_context.private_chart_evidence
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderConfigurationError(), M1AFailureCode.PROVIDER_CONFIGURATION),
        (ProviderRefusalError(), M1AFailureCode.PROVIDER_REFUSAL),
        (ProviderIncompleteError(), M1AFailureCode.PROVIDER_INCOMPLETE),
        (ProviderSchemaError(), M1AFailureCode.PROVIDER_SCHEMA),
        (ProviderTimeoutError(), M1AFailureCode.PROVIDER_TIMEOUT),
        (ProviderRateLimitError(), M1AFailureCode.PROVIDER_RATE_LIMIT),
        (ProviderAuthenticationError(), M1AFailureCode.PROVIDER_AUTHENTICATION),
        (ProviderConnectionError(), M1AFailureCode.PROVIDER_CONNECTION),
    ],
)
def test_eight_provider_failures_map_to_safe_nonchargeable_state(error, expected, m1a_context):
    result = M1AService(RecordingProvider([error])).interpret(_intake(), m1a_context)
    assert result.status is ServiceStatus.PROVIDER_FAILED
    assert result.failure_code is expected
    assert result.assembly is None
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
    assert result.closed_beta_allowed is False


def test_first_validation_failure_can_repair_once_without_changing_program_or_catalog(
    m1a_context, m1a_catalog
):
    intake = _intake()
    invalid = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    invalid["plain_language_explanation"][0]["evidence_refs"] = ["M1AEV99"]
    initial_hash = m1a_program_hash(m1a_context)
    provider = RecordingProvider([invalid, _valid_draft(intake, m1a_catalog)])
    result = M1AService(provider).interpret(intake, m1a_context)
    assert result.status is ServiceStatus.SUCCESS
    assert [item.attempt_number for item in result.provider_attempts] == [1, 2]
    first_payload, second_payload = [json.loads(item.user_payload_json) for item in provider.prompts]
    assert first_payload["repair_context"] is None
    assert second_payload["repair_context"]["attempt"] == 2
    assert second_payload["repair_context"]["must_preserve_program_hash"] == initial_hash
    assert first_payload["evidence_reference_catalog"] == second_payload["evidence_reference_catalog"]
    assert m1a_program_hash(m1a_context) == initial_hash


def test_second_validation_failure_returns_no_partial_formal_narrative(m1a_context, m1a_catalog):
    intake = _intake()
    invalid = _valid_draft(intake, m1a_catalog).model_dump(mode="json")
    invalid["plain_language_explanation"][0]["evidence_refs"] = ["M1AEV99"]
    result = M1AService(RecordingProvider([invalid, invalid])).interpret(intake, m1a_context)
    assert result.status is ServiceStatus.FAILED_VALIDATION
    assert result.failure_code is M1AFailureCode.VALIDATION
    assert result.assembly is None
    assert len(result.provider_attempts) == 2
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
    assert result.closed_beta_allowed is False


def test_provider_side_program_mutation_is_detected_before_assembly(m1a_context, m1a_catalog):
    intake = _intake()
    provider = RecordingProvider(
        [_valid_draft(intake, m1a_catalog)],
        context_to_mutate=m1a_context,
    )
    result = M1AService(provider).interpret(intake, m1a_context)
    assert result.failure_code is M1AFailureCode.PROGRAM_INTEGRITY
    assert result.assembly is None


def test_non_fake_provider_identity_is_rejected_without_formal_output(m1a_context, m1a_catalog):
    intake = _intake()
    result = M1AService(
        RecordingProvider([_valid_draft(intake, m1a_catalog)], provider_name="OPENAI_RESPONSES_API")
    ).interpret(intake, m1a_context)
    assert result.failure_code is M1AFailureCode.PROVIDER_NOT_OFFLINE
    assert result.assembly is None


def test_release_gate_remains_unverified_and_three_flags_false(m1a_context, m1a_catalog):
    intake = _intake()
    result = M1AService(RecordingProvider([_valid_draft(intake, m1a_catalog)])).interpret(intake, m1a_context)
    assert result.narrative_release.narrative_release_status is NarrativeReleaseStatus.UNVERIFIED
    assert result.should_charge is False
    assert result.persist_as_formal_report_allowed is False
    assert result.closed_beta_allowed is False
