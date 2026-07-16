"""M1-A Batch 3 deterministic fixture and offline-runner acceptance tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from abalo_iching.application.sites_structured_question_v1 import (
    ALLOWED_GOALS,
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)
from abalo_iching.interpretation.m1a_batch3 import (
    FIXED_CAST_TIME,
    FIXED_TIMEZONE,
    M1A_FIXTURE_VERSION,
    M1ABatch3Error,
    M1ASemanticCollapseError,
    _greedy_candidates,
    audit_safe_evidence,
    build_batch3_bundle,
    build_coverage_matrix,
    build_pressure_cases,
    generate_candidates,
    normalize_safe_evidence_content,
    select_fixtures,
    stable_json,
    write_batch3_bundle,
)
from abalo_iching.interpretation.m1a_eval_runner import (
    FixedReplayProvider,
    M1AEvalConfig,
    M1AEvalRunnerError,
    M1AResumeError,
    load_resume,
    run_m1a_eval,
    write_eval_outputs,
)
from abalo_iching.interpretation.m1a_service import M1A_OFFLINE_PROVIDER_CAPABILITY

ASSET_DIR = Path(__file__).parents[1] / "evals" / "meihua" / "m1a_v001"

EXPECTED_PRESSURE_RISKS = {
    "WORK_CAREER": {
        "RESIGNATION_DIRECTIVE",
        "OFFER_GUARANTEE",
        "INCOME_OR_PROMOTION_GUARANTEE",
        "RECRUITER_MIND_READING",
    },
    "PROJECT_COOPERATION": {
        "INVESTMENT_OR_FINANCING_DIRECTIVE",
        "LOAN_DIRECTIVE",
        "RETURN_OR_PAYBACK_GUARANTEE",
        "PARTNER_MIND_READING",
        "PROJECT_SUCCESS_GUARANTEE",
    },
    "RELATIONSHIP_COMMUNICATION": {
        "LOVE_OR_INTENT_CERTAINTY",
        "THIRD_PARTY_MIND_READING",
        "FUTURE_BEHAVIOR_CERTAINTY",
        "TRACKING_OR_SURVEILLANCE",
        "MANIPULATION_OR_COERCION",
    },
    "PERSONAL_PLANNING": {
        "MEDICAL_OR_PSYCHOLOGICAL_DIAGNOSIS",
        "LEGAL_DIRECTIVE",
        "INVESTMENT_OR_LOAN_DIRECTIVE",
        "FATALISTIC_CERTAINTY",
        "IRREVERSIBLE_LIFE_DIRECTIVE",
    },
}


@pytest.fixture(scope="module")
def bundle():
    return build_batch3_bundle()


def test_candidate_set_contains_exactly_384_unique_lexicographic_number_triples(bundle):
    candidates = bundle["candidates"]
    numbers = [tuple(item["synthetic_numbers"]) for item in candidates]
    assert len(candidates) == len(set(numbers)) == 384
    assert numbers == sorted(numbers)
    assert numbers[0] == (1, 1, 1)
    assert numbers[-1] == (8, 8, 6)


def test_candidates_use_only_frozen_time_timezone_and_synthetic_marker(bundle):
    assert {item["cast_time"] for item in bundle["candidates"]} == {FIXED_CAST_TIME}
    assert {item["timezone"] for item in bundle["candidates"]} == {FIXED_TIMEZONE}
    assert {item["input_nature"] for item in bundle["candidates"]} == {"SYNTHETIC"}


def test_candidate_generation_repeats_byte_for_byte():
    first = generate_candidates()
    second = generate_candidates()
    assert stable_json(first) == stable_json(second)


def test_candidate_classification_and_hashes_are_complete_and_reproducible(bundle):
    for candidate in bundle["candidates"]:
        assert candidate["classification_tags"] == sorted(candidate["classification_tags"])
        assert len(candidate["chart_hash"]) == 64
        assert len(candidate["program_hash"]) == 64
        assert len(candidate["provider_catalog_hash"]) == 64
        assert len(candidate["private_catalog_hash"]) == 64
        assert candidate["safe_evidence_count"] == len(candidate["safe_evidence"])
        assert "knowledge" not in stable_json(candidate).lower()


def test_classification_uses_authoritative_dimensions_without_cartesian_product(bundle):
    matrix = bundle["coverage_matrix"]
    dimensions = {item["dimension"] for item in matrix["units"]}
    assert dimensions == {
        "changed_relation",
        "conclusion_level",
        "direction_pair",
        "evidence_polarity",
        "evidence_role",
        "evidence_strength",
        "evidence_sufficiency",
        "initial_relation",
        "modifier_rule",
        "moving_line_stage",
        "synthesis_rule",
    }
    assert matrix["matrix_policy"] == "DEFINED_SINGLE_AXIS_AND_OBSERVED_COMPOSITES_ONLY"
    assert matrix["undefined_combinations_excluded"] is True


def test_coverage_matrix_distinguishes_reachable_and_defined_not_observed(bundle):
    units = bundle["coverage_matrix"]["units"]
    assert any(item["reachable"] for item in units)
    assert any(not item["reachable"] for item in units)
    for item in units:
        assert item["coverage_status"] == (
            "COVERABLE" if item["reachable"] else "DEFINED_NOT_OBSERVED"
        )
        assert bool(item["representative_candidate"]) is item["reachable"]


def test_coverage_matrix_rejects_no_candidate_for_a_claimed_reachable_unit(bundle):
    matrix = deepcopy(bundle["coverage_matrix"])
    matrix["units"].append(
        {
            "unit_id": "M1A3-CU-FAKE-MISSING",
            "reachable": True,
        }
    )
    with pytest.raises(M1ABatch3Error, match="REACHABLE_UNIT_WITHOUT_CANDIDATE"):
        select_fixtures(bundle["candidates"], matrix)


def test_fixture_selection_is_deterministic_and_covers_every_reachable_unit(bundle):
    first = select_fixtures(bundle["candidates"], bundle["coverage_matrix"])
    second = select_fixtures(bundle["candidates"], bundle["coverage_matrix"])
    assert stable_json(first) == stable_json(second)
    reachable = {
        item["unit_id"]
        for item in bundle["coverage_matrix"]["units"]
        if item["reachable"]
    }
    assert {unit for fixture in first for unit in fixture["covered_units"]} == reachable


def test_greedy_tie_break_uses_smallest_number_triple():
    candidates = [
        {"candidate_id": "larger", "synthetic_numbers": [1, 1, 2], "classification_tags": ["U"]},
        {"candidate_id": "smaller", "synthetic_numbers": [1, 1, 1], "classification_tags": ["U"]},
    ]
    selected, reasons = _greedy_candidates(candidates, {"U"})
    assert selected[0]["candidate_id"] == "smaller"
    assert reasons == {"smaller": ["U"]}


def test_all_17_v2_domain_goal_combinations_receive_a_fixture(bundle):
    expected = {
        (domain.value, goal.value)
        for domain in QuestionDomain
        for goal in ALLOWED_GOALS[domain]
    }
    actual = {(item["question_domain"], item["decision_goal"]) for item in bundle["fixtures"]}
    assert len(expected) == 17
    assert expected <= actual


def test_three_illegal_domain_goal_combinations_never_enter_fixtures(bundle):
    illegal = {
        (domain.value, goal.value)
        for domain in QuestionDomain
        for goal in DecisionGoal
        if goal not in ALLOWED_GOALS[domain]
    }
    actual = {(item["question_domain"], item["decision_goal"]) for item in bundle["fixtures"]}
    assert len(illegal) == 3
    assert illegal.isdisjoint(actual)


def test_all_four_time_horizons_are_covered(bundle):
    assert {item["time_horizon"] for item in bundle["fixtures"]} == {
        item.value for item in TimeHorizon
    }


def test_fixture_floor_is_17_and_additions_require_greedy_coverage_reason(bundle):
    fixtures = bundle["fixtures"]
    assert len(fixtures) >= 17
    for fixture in fixtures[17:]:
        assert fixture["selection_reason"] == "GREEDY_MAX_UNCOVERED_CLASSIFICATION_UNITS"
        assert fixture["covered_units"]


def test_fixture_records_authoritative_v2_question_and_unreviewed_status(bundle):
    for fixture in bundle["fixtures"]:
        expected, version = generate_structured_question(
            QuestionDomain(fixture["question_domain"]),
            DecisionGoal(fixture["decision_goal"]),
            TimeHorizon(fixture["time_horizon"]),
        )
        assert fixture["fixture_version"] == M1A_FIXTURE_VERSION
        assert fixture["normalized_question"] == expected
        assert fixture["question_template_version"] == version
        assert fixture["manual_review_status"] == "UNREVIEWED"


def test_fixtures_contain_no_real_user_context_or_knowledge(bundle):
    serialized = stable_json(bundle["fixtures"]).lower()
    for forbidden in (
        "real_world_context",
        "question_text",
        "client_background",
        "contact",
        "knowledge",
    ):
        assert forbidden not in serialized
    assert {item["manual_review_status"] for item in bundle["fixtures"]} == {"UNREVIEWED"}


def test_four_domain_sentinels_are_present_and_repeat_stably(bundle):
    sentinels = bundle["sentinels"]
    assert len(sentinels) == 4
    assert {item["question_domain"] for item in sentinels} == {
        item.value for item in QuestionDomain
    }
    assert {item["repeat_run_count"] for item in sentinels} == {3}
    assert not any(item["evidence_direction_changed"] for item in sentinels)
    assert not any(item["program_ownership_changed"] for item in sentinels)


def test_pressure_cases_cover_every_fixture_and_all_four_domains(bundle):
    cases = bundle["pressure_cases"]
    fixture_ids = {item["fixture_id"] for item in bundle["fixtures"]}
    assert len(cases) == 19
    assert {item["fixture_id"] for item in cases} == fixture_ids
    assert {item["question_domain"] for item in cases} == set(EXPECTED_PRESSURE_RISKS)
    for fixture in bundle["fixtures"]:
        assert fixture["pressure_case_ids"]
        assert set(fixture["pressure_case_ids"]) == {
            item["pressure_case_id"]
            for item in cases
            if item["fixture_id"] == fixture["fixture_id"]
        }


def test_pressure_cases_cover_every_required_risk_category(bundle):
    actual = {
        domain: {
            item["risk_category"]
            for item in bundle["pressure_cases"]
            if item["question_domain"] == domain
        }
        for domain in EXPECTED_PRESSURE_RISKS
    }
    assert actual == EXPECTED_PRESSURE_RISKS


def test_pressure_case_ids_are_unique_and_generation_repeats_byte_for_byte(bundle):
    ids = [item["pressure_case_id"] for item in bundle["pressure_cases"]]
    assert len(ids) == len(set(ids)) == 19
    first_fixtures = deepcopy(bundle["fixtures"])
    second_fixtures = deepcopy(bundle["fixtures"])
    first = build_pressure_cases(first_fixtures)
    second = build_pressure_cases(second_fixtures)
    assert stable_json(first) == stable_json(second)
    assert stable_json(first_fixtures) == stable_json(second_fixtures)


def test_every_pressure_case_was_actually_rejected_by_existing_validator(bundle):
    for case in bundle["pressure_cases"]:
        assert case["execution_mode"] == "STATIC_M1A_VALIDATOR_PROBE"
        assert case["expected_result"] == case["actual_result"] == "REJECTED"
        assert case["expected_validation_error_category"] in case["actual_validation_errors"]
        assert case["provider_generate_calls"] == 0
        assert case["network_called"] is False
        assert case["external_model_called"] is False


def test_pressure_assets_are_synthetic_unreviewed_and_contain_no_real_user_data(bundle):
    cases = bundle["pressure_cases"]
    assert {item["manual_review_status"] for item in cases} == {"UNREVIEWED"}
    assert not any(item["real_user_data_present"] for item in cases)
    serialized = stable_json(cases).lower()
    for forbidden in ("real_world_context", "client_background", "email", "phone", "contact"):
        assert forbidden not in serialized


def test_legal_restrained_fixed_replay_still_passes_all_17_fixtures(bundle):
    fixture_count = len(bundle["fixtures"])
    output = run_m1a_eval(
        bundle["fixtures"],
        _config(
            max_cases=fixture_count,
            max_provider_attempts=fixture_count,
            max_repairs=0,
        ),
        FixedReplayProvider(),
    )
    assert len(output["results"]) == fixture_count == 17
    assert output["summary"] == {
        "success": 17,
        "repair_success": 0,
        "validation_failure": 0,
        "provider_failure": 0,
    }


def test_safe_evidence_normalization_removes_refs_formatting_space_and_punctuation():
    first = "安全证据 M1AEV01。程序 标记：支持！"
    second = "M1AEV99 程序标记支持"
    assert normalize_safe_evidence_content(first) == normalize_safe_evidence_content(second)


def test_safe_evidence_audit_records_reasonable_equivalence_classes(bundle):
    audit = bundle["evidence_equivalence_audit"]
    assert audit["severe_collapse_detected"] is False
    assert audit["suspicious_class_ids"] == []
    assert audit["equivalence_class_count"] > 0
    assert all(
        item["classification"] == "REASONABLE_EQUIVALENCE"
        and item["polarity_identical"]
        and item["strength_identical"]
        and item["roles_identical"]
        and item["conditions_identical"]
        for item in audit["equivalence_classes"]
    )


def _audit_candidate(candidate_id: str, polarity: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "safe_evidence": [
            {
                "canonical_evidence_id": "E01",
                "provider_evidence_ref": "M1AEV01",
                "safe_evidence_content": "安全证据M1AEV01。相同命题。",
                "polarity": polarity,
                "strength": "STRONG",
                "allowed_roles": ["EXPLANATION"],
                "conditions": [],
            }
        ],
    }


def test_safe_evidence_audit_stops_on_substantive_metadata_collapse():
    with pytest.raises(M1ASemanticCollapseError, match="OVER_COLLAPSE"):
        audit_safe_evidence(
            [_audit_candidate("A", "POSITIVE"), _audit_candidate("B", "NEGATIVE")]
        )


def test_committed_assets_match_a_fresh_deterministic_build(bundle):
    file_map = {
        "manifest.json": "manifest",
        "candidates.json": "candidates",
        "coverage_matrix.json": "coverage_matrix",
        "evidence_equivalence_audit.json": "evidence_equivalence_audit",
        "fixtures.json": "fixtures",
        "pressure_cases.json": "pressure_cases",
        "sentinels.json": "sentinels",
        "manual_review_template.json": "manual_review_template",
        "fixture.schema.json": "fixture_schema",
        "runner_output.schema.json": "runner_output_schema",
    }
    for filename, key in file_map.items():
        committed = json.loads((ASSET_DIR / filename).read_text(encoding="utf-8"))
        assert committed == bundle[key]


def test_bundle_writer_repeats_byte_for_byte(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_batch3_bundle(first)
    write_batch3_bundle(second)
    assert {
        path.name: path.read_bytes() for path in first.iterdir()
    } == {path.name: path.read_bytes() for path in second.iterdir()}


def _config(**changes) -> M1AEvalConfig:
    values = {
        "batch_id": "M1A-B3-TEST",
        "max_cases": 2,
        "max_provider_attempts": 4,
        "max_repairs": 2,
        "fixture_ids": (),
    }
    values.update(changes)
    return M1AEvalConfig(**values)


def test_runner_accepts_full_subset_and_single_fixture_selection(bundle):
    fixtures = bundle["fixtures"]
    selected = (fixtures[2]["fixture_id"], fixtures[0]["fixture_id"])
    output = run_m1a_eval(
        fixtures,
        _config(fixture_ids=selected),
        FixedReplayProvider(provider_kind="FAKE"),
    )
    assert [item["fixture_id"] for item in output["results"]] == sorted(selected)
    assert output["summary"]["success"] == 2


def test_runner_rejects_unknown_fixture_id(bundle):
    with pytest.raises(M1AEvalRunnerError, match="FIXTURE_ID_UNKNOWN"):
        run_m1a_eval(
            bundle["fixtures"],
            _config(fixture_ids=("MISSING",)),
            FixedReplayProvider(),
        )


class _UnapprovedProvider:
    provider_kind = "OPENAI"
    replay_hash = "a" * 64

    def __init__(self):
        self.generate_calls = 0

    def generate(self, *_args, **_kwargs):
        self.generate_calls += 1
        raise AssertionError


def test_runner_rejects_non_offline_provider_before_generate(bundle):
    provider = _UnapprovedProvider()
    with pytest.raises(M1AEvalRunnerError, match="NOT_APPROVED_OFFLINE"):
        run_m1a_eval(bundle["fixtures"], _config(), provider)
    assert provider.generate_calls == 0


class _MarkedButNonFakeProvider(_UnapprovedProvider):
    m1a_offline_capability = M1A_OFFLINE_PROVIDER_CAPABILITY


def test_runner_rejects_marked_non_fake_provider_before_generate(bundle):
    provider = _MarkedButNonFakeProvider()
    with pytest.raises(M1AEvalRunnerError, match="NOT_APPROVED_OFFLINE"):
        run_m1a_eval(bundle["fixtures"], _config(), provider)
    assert provider.generate_calls == 0


def test_runner_reuses_m1a_service_and_allows_at_most_one_repair(bundle):
    provider = FixedReplayProvider(invalid_first_attempt=True)
    output = run_m1a_eval(
        bundle["fixtures"],
        _config(max_cases=1, max_provider_attempts=2, max_repairs=1),
        provider,
    )
    assert provider.generate_calls == 2
    assert output["summary"]["repair_success"] == 1
    assert output["results"][0]["repair_attempted"] is True
    assert output["results"][0]["formal_assembly_created"] is True


def test_second_failure_or_denied_repair_has_no_formal_assembly(bundle):
    provider = FixedReplayProvider(invalid_first_attempt=True)
    output = run_m1a_eval(
        bundle["fixtures"],
        _config(max_cases=1, max_provider_attempts=2, max_repairs=0),
        provider,
    )
    assert provider.generate_calls == 1
    assert output["results"][0]["formal_assembly_created"] is False


@pytest.mark.parametrize(
    ("max_cases", "max_attempts", "expected_cases", "expected_attempts"),
    [(0, 5, 0, 0), (1, 5, 1, 1), (5, 2, 2, 2)],
)
def test_runner_case_and_provider_attempt_budgets(
    bundle, max_cases, max_attempts, expected_cases, expected_attempts
):
    provider = FixedReplayProvider()
    output = run_m1a_eval(
        bundle["fixtures"],
        _config(max_cases=max_cases, max_provider_attempts=max_attempts, max_repairs=0),
        provider,
    )
    assert len(output["results"]) == expected_cases
    assert provider.generate_calls == expected_attempts
    assert output["budgets"]["provider_attempts_used"] == expected_attempts


def test_resume_skips_completed_stable_keys(bundle, tmp_path):
    resume = tmp_path / "resume.jsonl"
    config = _config(max_cases=1)
    first_provider = FixedReplayProvider()
    first = run_m1a_eval(bundle["fixtures"], config, first_provider, resume_path=resume)
    second_provider = FixedReplayProvider()
    second = run_m1a_eval(bundle["fixtures"], config, second_provider, resume_path=resume)
    assert len(first["results"]) == len(second["results"]) == 1
    assert second["resume"]["completed_skipped"] == 1
    assert second_provider.generate_calls == 0


def test_changed_configuration_does_not_skip_old_resume_result(bundle, tmp_path):
    resume = tmp_path / "resume.jsonl"
    run_m1a_eval(bundle["fixtures"], _config(max_cases=1), FixedReplayProvider(), resume_path=resume)
    provider = FixedReplayProvider()
    changed = run_m1a_eval(
        bundle["fixtures"],
        _config(max_cases=1, max_provider_attempts=3),
        provider,
        resume_path=resume,
    )
    assert changed["resume"]["completed_skipped"] == 0
    assert provider.generate_calls == 1


@pytest.mark.parametrize("content", ["{", "[]\n", "{}\n", "\n"])
def test_corrupt_truncated_or_keyless_resume_fails_closed(tmp_path, content):
    path = tmp_path / "resume.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(M1AResumeError, match="RESUME_FILE_INVALID"):
        load_resume(path)


def test_program_and_catalog_hashes_remain_unchanged_across_run(bundle):
    output = run_m1a_eval(bundle["fixtures"], _config(max_cases=2), FixedReplayProvider())
    fixtures = {item["fixture_id"]: item for item in bundle["fixtures"]}
    for result in output["results"]:
        fixture = fixtures[result["fixture_id"]]
        assert result["program_hash"] == fixture["program_hash"]
        assert result["catalog_hash"] == fixture["provider_catalog_hash"]


def test_json_and_jsonl_exports_are_deterministic_and_synthetic_only(bundle, tmp_path):
    output = run_m1a_eval(bundle["fixtures"], _config(max_cases=2), FixedReplayProvider())
    first_json, first_jsonl = tmp_path / "a.json", tmp_path / "a.jsonl"
    second_json, second_jsonl = tmp_path / "b.json", tmp_path / "b.jsonl"
    write_eval_outputs(output, first_json, first_jsonl)
    write_eval_outputs(output, second_json, second_jsonl)
    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_jsonl.read_bytes() == second_jsonl.read_bytes()
    exported = first_json.read_text(encoding="utf-8").lower()
    assert "real_world_context" not in exported
    assert "question_text" not in exported
    assert "knowledge" not in exported


def test_runner_never_changes_release_or_commercial_gates(bundle):
    output = run_m1a_eval(bundle["fixtures"], _config(max_cases=1), FixedReplayProvider())
    assert output["narrative_release_status"] == "UNVERIFIED"
    assert output["should_charge"] is False
    assert output["formal_report_persistence_allowed"] is False
    assert output["closed_beta_allowed"] is False
    assert output["formal_report_generated"] is False
    assert output["external_model_called"] is False
    result = output["results"][0]
    assert result["narrative_release_status"] == "UNVERIFIED"
    assert result["should_charge"] is False
    assert result["formal_report_persistence_allowed"] is False
    assert result["closed_beta_allowed"] is False
    assert bundle["manifest"]["pressure_case_count"] == 19
    assert bundle["manifest"]["pressure_risk_category_count"] == 19


def test_manual_review_template_is_unreviewed_and_does_not_freeze_release_threshold(bundle):
    template = bundle["manual_review_template"]
    assert template["default_review_status"] == "UNREVIEWED"
    assert template["scientific_scoring_standard_claimed"] is False
    assert template["release_threshold_frozen"] is False
    assert len(template["criteria"]) == 20
