"""Completely offline M1-A fixture evaluation runner for Batch 3."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from zoneinfo import ZoneInfo

from abalo_iching.application.m1a_request import build_m1a_intake
from abalo_iching.application.sites_meihua_service_v2 import CONTRACT_VERSION_V2
from abalo_iching.application.sites_structured_question_v1 import (
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)
from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.models import MeihuaInput

from .enums import ServiceStatus, SubjectScope
from .exceptions import ProviderConfigurationError
from .m1a_batch3 import (
    FIXED_TIMEZONE,
    M1A_RUNNER_OUTPUT_SCHEMA_VERSION,
    candidate_question_id,
    stable_json,
    stable_sha256,
)
from .m1a_context import M1AEvidenceRole, build_m1a_program_context, m1a_program_hash
from .m1a_evidence_catalog import build_m1a_evidence_catalog
from .m1a_service import M1A_OFFLINE_PROVIDER_CAPABILITY, M1AService
from .models import AINarrativeDraftClaim, AINarrativeDraftContent, PromptPackage, ProviderResult

M1A_EVAL_RUNNER_VERSION = "MEIHUA_M1A_OFFLINE_EVAL_RUNNER_V001"
M1A_REPLAY_PROVIDER_VERSION = "MEIHUA_M1A_FIXED_REPLAY_PROVIDER_V001"
_ALLOWED_PROVIDER_KINDS = frozenset({"FAKE", "MOCK"})


class M1AEvalRunnerError(ValueError):
    """Fail-closed runner configuration, integrity, or resume failure."""


class M1AResumeError(M1AEvalRunnerError):
    pass


@runtime_checkable
class M1AOfflineEvalProvider(Protocol):
    m1a_offline_capability: str
    provider_kind: str

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult: ...


_DOMAIN_ACTION = {
    "WORK_CAREER": "可以考虑先核实工作准备和求职流程反馈，再做可撤回的小步验证。",
    "PROJECT_COOPERATION": "可以考虑先澄清项目分工、资源和承诺，再做可撤回的小步验证。",
    "RELATIONSHIP_COMMUNICATION": "可以考虑先表达自身沟通边界，并观察和记录现实反馈。",
    "PERSONAL_PLANNING": "可以考虑先调整自身优先级、精力和节奏，再记录现实反馈。",
}
_GOAL_FOCUS = {
    "IDENTIFY_OBSTACLES": "重点核实阻力、支持条件和风险信号。",
    "PLAN_NEXT_STEP": "把它作为下一步小步验证。",
    "PREPARE_COMMUNICATION": "先准备沟通、表达和询问。",
    "ADJUST_COMMITMENT_BOUNDARIES": "同步调整投入、承诺和边界。",
    "OBSERVE_VERIFY_SIGNALS": "继续观察、核实并记录反馈信号。",
}


class FixedReplayProvider:
    """Static Fake/Mock Provider; it performs no network, model, or external API call."""

    m1a_offline_capability = M1A_OFFLINE_PROVIDER_CAPABILITY

    def __init__(self, *, provider_kind: str = "MOCK", invalid_first_attempt: bool = False) -> None:
        if provider_kind not in _ALLOWED_PROVIDER_KINDS:
            raise M1AEvalRunnerError("M1A_RUNNER_PROVIDER_KIND_NOT_OFFLINE")
        self.provider_kind = provider_kind
        self.invalid_first_attempt = invalid_first_attempt
        self.generate_calls = 0

    @property
    def replay_hash(self) -> str:
        return stable_sha256(
            {
                "provider_version": M1A_REPLAY_PROVIDER_VERSION,
                "provider_kind": self.provider_kind,
                "invalid_first_attempt": self.invalid_first_attempt,
            }
        )

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
        self.generate_calls += 1
        payload = json.loads(prompt.user_payload_json)
        refs = payload["evidence_role_constraints"]
        intake = payload["structured_intake"]
        if self.invalid_first_attempt and attempt_number == 1:
            parsed: dict[str, Any] = {
                "plain_language_explanation": [],
                "real_world_advice": [],
                "conditions_that_change_outcome": [],
                "review_questions": [],
            }
        else:
            explanation_ref = refs["explanation_refs"][0]
            action_ref = refs["action_option_refs"][0]
            review_ref = refs["review_question_refs"][0]
            condition_refs = refs["condition_refs"]
            parsed = AINarrativeDraftContent(
                plain_language_explanation=[
                    AINarrativeDraftClaim(
                        text="这些安全证据可能提示需要核实现实条件和反馈，避免提前形成结论。",
                        evidence_refs=[explanation_ref],
                        subject_scope=SubjectScope.SITUATION,
                    )
                ],
                real_world_advice=[
                    AINarrativeDraftClaim(
                        text=(
                            _DOMAIN_ACTION[intake["question_domain"]]
                            + _GOAL_FOCUS[intake["decision_goal"]]
                        ),
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
        return ProviderResult(
            parsed_output=parsed,
            response_id=f"m1a-{self.provider_kind.lower()}-{attempt_number}",
            model="OFFLINE_STATIC_REPLAY",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            latency_ms=0,
            attempt_number=attempt_number,
            provider_name=self.provider_kind,
            prompt_version=prompt.prompt_version,
        )


class _BudgetedProvider:
    m1a_offline_capability = M1A_OFFLINE_PROVIDER_CAPABILITY

    def __init__(
        self,
        provider: M1AOfflineEvalProvider,
        remaining_attempts: int,
        *,
        allow_repair: bool,
    ) -> None:
        self.provider = provider
        self.provider_kind = provider.provider_kind
        self.remaining_attempts = remaining_attempts
        self.allow_repair = allow_repair
        self.generate_calls = 0

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
        if attempt_number == 2 and not self.allow_repair:
            raise ProviderConfigurationError("M1A_RUNNER_REPAIR_BUDGET_EXHAUSTED")
        if self.generate_calls >= self.remaining_attempts:
            raise ProviderConfigurationError("M1A_RUNNER_PROVIDER_ATTEMPT_BUDGET_EXHAUSTED")
        self.generate_calls += 1
        return self.provider.generate(prompt, attempt_number=attempt_number)


@dataclass(frozen=True, slots=True)
class M1AEvalConfig:
    batch_id: str
    max_cases: int
    max_provider_attempts: int
    max_repairs: int
    fixture_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.batch_id or self.batch_id.strip() != self.batch_id:
            raise M1AEvalRunnerError("M1A_RUNNER_BATCH_ID_INVALID")
        if self.max_cases < 0 or self.max_provider_attempts < 0 or self.max_repairs < 0:
            raise M1AEvalRunnerError("M1A_RUNNER_BUDGET_INVALID")
        if len(set(self.fixture_ids)) != len(self.fixture_ids):
            raise M1AEvalRunnerError("M1A_RUNNER_FIXTURE_IDS_NOT_UNIQUE")

    def configuration_hash(self, *, provider_replay_hash: str) -> str:
        return stable_sha256(
            {
                "runner_version": M1A_EVAL_RUNNER_VERSION,
                "batch_id": self.batch_id,
                "max_cases": self.max_cases,
                "max_provider_attempts": self.max_provider_attempts,
                "max_repairs": self.max_repairs,
                "fixture_ids": list(self.fixture_ids),
                "provider_replay_hash": provider_replay_hash,
            }
        )


def _validate_offline_provider(provider: object) -> M1AOfflineEvalProvider:
    try:
        approved = (
            isinstance(provider, M1AOfflineEvalProvider)
            and provider.m1a_offline_capability == M1A_OFFLINE_PROVIDER_CAPABILITY
            and provider.provider_kind in _ALLOWED_PROVIDER_KINDS
        )
    except Exception:
        approved = False
    if not approved:
        raise M1AEvalRunnerError("M1A_RUNNER_PROVIDER_NOT_APPROVED_OFFLINE")
    return provider


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M1AEvalRunnerError("M1A_RUNNER_FIXTURE_FILE_INVALID") from exc
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise M1AEvalRunnerError("M1A_RUNNER_FIXTURE_FILE_INVALID")
    fixture_ids = [item.get("fixture_id") for item in payload]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise M1AEvalRunnerError("M1A_RUNNER_FIXTURE_IDS_NOT_UNIQUE")
    return payload


def _resume_key(record: dict[str, Any]) -> tuple[str, ...]:
    fields = (
        "batch_id",
        "fixture_id",
        "runner_version",
        "configuration_hash",
        "program_hash",
        "catalog_hash",
    )
    values = tuple(record.get(field) for field in fields)
    if not all(isinstance(value, str) and value for value in values):
        raise M1AResumeError("M1A_RUNNER_RESUME_KEY_INVALID")
    return values


def load_resume(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise M1AResumeError("M1A_RUNNER_RESUME_FILE_INVALID") from exc
    if not lines or any(not line.strip() for line in lines):
        raise M1AResumeError("M1A_RUNNER_RESUME_FILE_INVALID")
    records: list[dict[str, Any]] = []
    try:
        for line in lines:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError
            _resume_key(value)
            records.append(value)
    except (json.JSONDecodeError, TypeError, M1AResumeError) as exc:
        raise M1AResumeError("M1A_RUNNER_RESUME_FILE_INVALID") from exc
    return records


def _build_fixture_program(fixture: dict[str, Any]):
    numbers = tuple(fixture["synthetic_numbers"])
    chart = cast_meihua(
        MeihuaInput(
            *numbers,
            datetime.fromisoformat(fixture["cast_time"]).astimezone(ZoneInfo(FIXED_TIMEZONE)),
            fixture["timezone"],
            candidate_question_id(numbers),
        )
    )
    context = build_m1a_program_context(chart)
    catalog = build_m1a_evidence_catalog(context)
    if m1a_program_hash(context) != fixture["program_hash"]:
        raise M1AEvalRunnerError("M1A_RUNNER_PROGRAM_HASH_MISMATCH")
    if catalog.provider_catalog_hash != fixture["provider_catalog_hash"]:
        raise M1AEvalRunnerError("M1A_RUNNER_CATALOG_HASH_MISMATCH")
    return context, catalog


def _build_intake(fixture: dict[str, Any]):
    domain = QuestionDomain(fixture["question_domain"])
    goal = DecisionGoal(fixture["decision_goal"])
    horizon = TimeHorizon(fixture["time_horizon"])
    question, template_version = generate_structured_question(domain, goal, horizon)
    if question != fixture["normalized_question"]:
        raise M1AEvalRunnerError("M1A_RUNNER_NORMALIZED_QUESTION_MISMATCH")
    return build_m1a_intake(
        question_id=f"eval-{fixture['fixture_id']}",
        question_domain=domain,
        decision_goal=goal,
        time_horizon=horizon,
        normalized_question=question,
        question_template_version=template_version,
        contract_version=CONTRACT_VERSION_V2,
        is_synthetic=True,
    )


def _select_fixtures(
    fixtures: list[dict[str, Any]], fixture_ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    ordered = sorted(fixtures, key=lambda item: item["fixture_id"])
    if not fixture_ids:
        return ordered
    by_id = {item["fixture_id"]: item for item in ordered}
    missing = set(fixture_ids) - set(by_id)
    if missing:
        raise M1AEvalRunnerError("M1A_RUNNER_FIXTURE_ID_UNKNOWN:" + ",".join(sorted(missing)))
    return [by_id[fixture_id] for fixture_id in fixture_ids]


def run_m1a_eval(
    fixtures: list[dict[str, Any]],
    config: M1AEvalConfig,
    provider: object,
    *,
    resume_path: Path | None = None,
) -> dict[str, Any]:
    """Run selected fixtures offline through M1AService and export audit-safe results."""
    offline_provider = _validate_offline_provider(provider)
    replay_hash = getattr(offline_provider, "replay_hash", None)
    if not isinstance(replay_hash, str) or len(replay_hash) != 64:
        raise M1AEvalRunnerError("M1A_RUNNER_REPLAY_HASH_INVALID")
    configuration_hash = config.configuration_hash(provider_replay_hash=replay_hash)
    selected = _select_fixtures(fixtures, config.fixture_ids)[: config.max_cases]
    resume_records = load_resume(resume_path) if resume_path is not None else []
    resume_keys = {_resume_key(item) for item in resume_records}
    results = list(resume_records)
    provider_attempts_used = 0
    repairs_used = 0
    skipped = 0
    for fixture in selected:
        context, catalog = _build_fixture_program(fixture)
        key = (
            config.batch_id,
            fixture["fixture_id"],
            M1A_EVAL_RUNNER_VERSION,
            configuration_hash,
            fixture["program_hash"],
            fixture["provider_catalog_hash"],
        )
        if key in resume_keys:
            skipped += 1
            continue
        remaining_attempts = config.max_provider_attempts - provider_attempts_used
        if remaining_attempts <= 0:
            break
        initial_program_hash = m1a_program_hash(context)
        initial_catalog_hash = catalog.provider_catalog_hash
        budgeted_provider = _BudgetedProvider(
            offline_provider,
            remaining_attempts,
            allow_repair=repairs_used < config.max_repairs,
        )
        result = M1AService(budgeted_provider).interpret(_build_intake(fixture), context)
        attempts = budgeted_provider.generate_calls
        provider_attempts_used += attempts
        repairs = max(0, attempts - 1)
        if repairs_used + repairs > config.max_repairs:
            raise M1AEvalRunnerError("M1A_RUNNER_REPAIR_BUDGET_EXCEEDED")
        repairs_used += repairs
        final_catalog = build_m1a_evidence_catalog(context)
        final_program_hash = m1a_program_hash(context)
        if final_program_hash != initial_program_hash:
            raise M1AEvalRunnerError("M1A_RUNNER_PROGRAM_CHANGED_DURING_RUN")
        if final_catalog.provider_catalog_hash != initial_catalog_hash:
            raise M1AEvalRunnerError("M1A_RUNNER_CATALOG_CHANGED_DURING_RUN")
        record = {
            "batch_id": config.batch_id,
            "fixture_id": fixture["fixture_id"],
            "runner_version": M1A_EVAL_RUNNER_VERSION,
            "configuration_hash": configuration_hash,
            "program_hash": final_program_hash,
            "catalog_hash": final_catalog.provider_catalog_hash,
            "provider_kind": offline_provider.provider_kind,
            "provider_attempt_count": attempts,
            "repair_attempted": repairs == 1,
            "status": result.status.value,
            "failure_code": result.failure_code.value if result.failure_code else None,
            "validation_errors": list(result.validation_errors),
            "formal_assembly_created": result.assembly is not None,
            "narrative_release_status": result.narrative_release.narrative_release_status.value,
            "should_charge": result.should_charge,
            "formal_report_persistence_allowed": result.persist_as_formal_report_allowed,
            "closed_beta_allowed": result.closed_beta_allowed,
            "not_a_live_openai_result": result.not_a_live_openai_result,
        }
        results.append(record)
        resume_keys.add(key)
        if resume_path is not None:
            resume_path.parent.mkdir(parents=True, exist_ok=True)
            resume_path.write_text(
                "\n".join(stable_json(item) for item in sorted(results, key=_resume_key)) + "\n",
                encoding="utf-8",
            )
    current_results = [
        item
        for item in results
        if item.get("batch_id") == config.batch_id
        and item.get("configuration_hash") == configuration_hash
    ]
    counts = Counter(item["status"] for item in current_results)
    repair_successes = sum(
        item["status"] == ServiceStatus.SUCCESS.value and item["repair_attempted"]
        for item in current_results
    )
    output = {
        "schema_version": M1A_RUNNER_OUTPUT_SCHEMA_VERSION,
        "batch_id": config.batch_id,
        "runner_version": M1A_EVAL_RUNNER_VERSION,
        "configuration_hash": configuration_hash,
        "provider_kind": offline_provider.provider_kind,
        "provider_replay_hash": replay_hash,
        "budgets": {
            "max_cases": config.max_cases,
            "max_provider_attempts": config.max_provider_attempts,
            "max_repairs": config.max_repairs,
            "provider_attempts_used": provider_attempts_used,
            "repairs_used": repairs_used,
        },
        "resume": {"completed_skipped": skipped},
        "results": sorted(current_results, key=lambda item: item["fixture_id"]),
        "summary": {
            "success": counts[ServiceStatus.SUCCESS.value] - repair_successes,
            "repair_success": repair_successes,
            "validation_failure": counts[ServiceStatus.FAILED_VALIDATION.value],
            "provider_failure": counts[ServiceStatus.PROVIDER_FAILED.value],
        },
        "narrative_release_status": "UNVERIFIED",
        "should_charge": False,
        "formal_report_persistence_allowed": False,
        "closed_beta_allowed": False,
        "formal_report_generated": False,
        "external_model_called": False,
    }
    return output


def write_eval_outputs(output: dict[str, Any], json_path: Path, jsonl_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(stable_json(output, indent=2) + "\n", encoding="utf-8")
    jsonl_path.write_text(
        "\n".join(stable_json(item) for item in output["results"])
        + ("\n" if output["results"] else ""),
        encoding="utf-8",
    )
