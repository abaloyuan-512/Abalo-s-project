"""M1-A offline Provider loop with one repair and fail-closed program ownership."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from .enums import EpistemicBasis, NarrativeKind, ServiceStatus
from .exceptions import (
    InterpretationValidationError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderError,
    ProviderIncompleteError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from .m1a_context import M1AEvidenceRole, M1AIntakeView, M1AProgramContext, m1a_program_hash
from .m1a_evidence_catalog import (
    M1AEvidenceCatalogError,
    M1ASafeEvidenceCatalog,
    build_m1a_evidence_catalog,
)
from .m1a_prompt_builder import (
    M1A_CONTRACT_VERSION,
    M1A_NARRATIVE_ASSEMBLY_VERSION,
    M1A_PROMPT_VERSION,
    M1A_PROVIDER_SCHEMA_VERSION,
    M1APromptPayloadError,
    M1APromptBuilder,
)
from .m1a_validator import M1A_VALIDATOR_VERSION, M1AValidator
from .models import (
    AINarrativeClaim,
    AINarrativeContent,
    AINarrativeDraftClaim,
    AINarrativeDraftContent,
    NarrativeReleaseSnapshot,
)
from .provider_protocol import InterpretationProvider
from .release import narrative_release_snapshot

M1A_SERVICE_VERSION = "MEIHUA_M1A_OFFLINE_SERVICE_V1"
M1A_OFFLINE_PROVIDER_CAPABILITY = "MEIHUA_M1A_OFFLINE_PROVIDER_CAPABILITY_V1"


@runtime_checkable
class M1AOfflineProviderCapability(Protocol):
    """M1-A-local pre-call gate; the historical Provider protocol stays unchanged."""

    m1a_offline_capability: str


class M1AFailureCode(StrEnum):
    PROVIDER_CONFIGURATION = "M1A_PROVIDER_CONFIGURATION_ERROR"
    PROVIDER_REFUSAL = "M1A_PROVIDER_REFUSAL"
    PROVIDER_INCOMPLETE = "M1A_PROVIDER_INCOMPLETE"
    PROVIDER_SCHEMA = "M1A_PROVIDER_SCHEMA_ERROR"
    PROVIDER_TIMEOUT = "M1A_PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMIT = "M1A_PROVIDER_RATE_LIMIT"
    PROVIDER_AUTHENTICATION = "M1A_PROVIDER_AUTHENTICATION"
    PROVIDER_CONNECTION = "M1A_PROVIDER_CONNECTION"
    PROVIDER_UNEXPECTED = "M1A_PROVIDER_UNEXPECTED_ERROR"
    PROVIDER_NOT_OFFLINE = "M1A_PROVIDER_NOT_OFFLINE"
    PROVIDER_METADATA = "M1A_PROVIDER_METADATA_INVALID"
    VALIDATION = "M1A_NARRATIVE_VALIDATION_FAILED"
    PROGRAM_INTEGRITY = "M1A_PROGRAM_INTEGRITY_FAILED"


_PROVIDER_FAILURES = (
    (ProviderConfigurationError, M1AFailureCode.PROVIDER_CONFIGURATION),
    (ProviderRefusalError, M1AFailureCode.PROVIDER_REFUSAL),
    (ProviderIncompleteError, M1AFailureCode.PROVIDER_INCOMPLETE),
    (ProviderSchemaError, M1AFailureCode.PROVIDER_SCHEMA),
    (ProviderTimeoutError, M1AFailureCode.PROVIDER_TIMEOUT),
    (ProviderRateLimitError, M1AFailureCode.PROVIDER_RATE_LIMIT),
    (ProviderAuthenticationError, M1AFailureCode.PROVIDER_AUTHENTICATION),
    (ProviderConnectionError, M1AFailureCode.PROVIDER_CONNECTION),
)
_FIELD_METADATA = {
    "plain_language_explanation": (
        NarrativeKind.EXPLANATION,
        EpistemicBasis.CHART_EVIDENCE,
        M1AEvidenceRole.EXPLANATION,
    ),
    "real_world_advice": (
        NarrativeKind.ACTION_OPTION,
        EpistemicBasis.ACTION_OPTION,
        M1AEvidenceRole.ACTION_OPTION,
    ),
    "conditions_that_change_outcome": (
        NarrativeKind.CONDITION_TO_VERIFY,
        EpistemicBasis.UNCERTAINTY,
        M1AEvidenceRole.CONDITION,
    ),
    "review_questions": (
        NarrativeKind.REVIEW_QUESTION,
        EpistemicBasis.UNCERTAINTY,
        M1AEvidenceRole.REVIEW_QUESTION,
    ),
}


@dataclass(frozen=True, slots=True)
class M1AProviderAttempt:
    attempt_number: int
    provider_name: str
    response_id: str | None
    model: str
    prompt_version: str
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class M1AAuditSnapshot:
    service_version: str
    m1a_contract_version: str
    prompt_version: str
    provider_schema_version: str
    validator_version: str
    narrative_assembly_version: str
    evidence_catalog_version: str
    provider_catalog_hash: str
    private_catalog_hash: str
    program_hash: str
    audit_id: str
    engine_version: str
    rule_version: str


@dataclass(frozen=True, slots=True)
class M1ANarrativeAssembly:
    program_content: M1AProgramContext
    ai_content: AINarrativeContent
    audit: M1AAuditSnapshot
    narrative_release: NarrativeReleaseSnapshot


@dataclass(frozen=True, slots=True)
class M1AServiceResult:
    status: ServiceStatus
    assembly: M1ANarrativeAssembly | None
    provider_attempts: tuple[M1AProviderAttempt, ...]
    failure_code: M1AFailureCode | None
    validation_errors: tuple[str, ...]
    narrative_release: NarrativeReleaseSnapshot
    should_charge: bool = False
    persist_as_formal_report_allowed: bool = False
    closed_beta_allowed: bool = False
    not_a_live_openai_result: bool = True


def _provider_failure_code(exc: ProviderError) -> M1AFailureCode:
    for error_type, code in _PROVIDER_FAILURES:
        if isinstance(exc, error_type):
            return code
    return M1AFailureCode.PROVIDER_UNEXPECTED


def _is_approved_offline_provider(provider: object) -> bool:
    try:
        return (
            isinstance(provider, M1AOfflineProviderCapability)
            and provider.m1a_offline_capability == M1A_OFFLINE_PROVIDER_CAPABILITY
        )
    except Exception:
        return False


def _assemble_claim(
    claim: AINarrativeDraftClaim,
    *,
    kind: NarrativeKind,
    basis: EpistemicBasis,
    role: M1AEvidenceRole,
    catalog: M1ASafeEvidenceCatalog,
) -> AINarrativeClaim:
    return AINarrativeClaim(
        text=claim.text,
        evidence_ids=[catalog.resolve(ref, required_role=role) for ref in claim.evidence_refs],
        narrative_kind=kind,
        subject_scope=claim.subject_scope,
        epistemic_basis=basis,
    )


def assemble_m1a_narrative(
    draft: AINarrativeDraftContent,
    catalog: M1ASafeEvidenceCatalog,
) -> AINarrativeContent:
    payload: dict[str, list[AINarrativeClaim]] = {}
    for field, (kind, basis, role) in _FIELD_METADATA.items():
        payload[field] = [
            _assemble_claim(claim, kind=kind, basis=basis, role=role, catalog=catalog)
            for claim in getattr(draft, field)
        ]
    return AINarrativeContent.model_validate(payload)


class M1AService:
    def __init__(
        self,
        provider: InterpretationProvider,
        *,
        prompt_builder: M1APromptBuilder | None = None,
        validator: M1AValidator | None = None,
    ) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder or M1APromptBuilder()
        self.validator = validator or M1AValidator()

    def interpret(self, intake: M1AIntakeView, context: M1AProgramContext) -> M1AServiceResult:
        if not _is_approved_offline_provider(self.provider):
            return self._failure(M1AFailureCode.PROVIDER_NOT_OFFLINE)
        initial_program_hash = m1a_program_hash(context)
        try:
            catalog = build_m1a_evidence_catalog(context)
        except (M1AEvidenceCatalogError, TypeError, ValueError):
            return self._failure(M1AFailureCode.PROGRAM_INTEGRITY)
        if catalog.program_hash != initial_program_hash:
            return self._failure(M1AFailureCode.PROGRAM_INTEGRITY)
        repair_errors: list[str] | None = None
        attempts: list[M1AProviderAttempt] = []
        for attempt_number in (1, 2):
            if m1a_program_hash(context) != initial_program_hash:
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            try:
                prompt = self.prompt_builder.build(
                    intake,
                    context,
                    catalog,
                    repair_errors=repair_errors,
                )
            except (M1AEvidenceCatalogError, M1APromptPayloadError, TypeError, ValueError):
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            try:
                provider_result = self.provider.generate(prompt, attempt_number=attempt_number)
            except ProviderError as exc:
                code = _provider_failure_code(exc)
                attempts.append(
                    M1AProviderAttempt(
                        attempt_number=attempt_number,
                        provider_name=type(self.provider).__name__,
                        response_id=None,
                        model="UNAVAILABLE",
                        prompt_version=M1A_PROMPT_VERSION,
                        failure_code=code.value,
                    )
                )
                return self._failure(code, attempts=attempts)
            except Exception:
                attempts.append(
                    M1AProviderAttempt(
                        attempt_number=attempt_number,
                        provider_name=type(self.provider).__name__,
                        response_id=None,
                        model="UNAVAILABLE",
                        prompt_version=M1A_PROMPT_VERSION,
                        failure_code=M1AFailureCode.PROVIDER_UNEXPECTED.value,
                    )
                )
                return self._failure(M1AFailureCode.PROVIDER_UNEXPECTED, attempts=attempts)
            if m1a_program_hash(context) != initial_program_hash:
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            if provider_result.provider_name not in {"FAKE", "MOCK"}:
                return self._failure(M1AFailureCode.PROVIDER_NOT_OFFLINE, attempts=attempts)
            if (
                provider_result.attempt_number != attempt_number
                or provider_result.prompt_version != M1A_PROMPT_VERSION
            ):
                return self._failure(M1AFailureCode.PROVIDER_METADATA, attempts=attempts)
            attempts.append(
                M1AProviderAttempt(
                    attempt_number=attempt_number,
                    provider_name=provider_result.provider_name,
                    response_id=provider_result.response_id,
                    model=provider_result.model,
                    prompt_version=provider_result.prompt_version,
                )
            )
            try:
                draft = self.validator.validate(provider_result.parsed_output, intake, catalog)
            except InterpretationValidationError as exc:
                repair_errors = list(exc.errors)
                if attempt_number == 2:
                    return self._failure(
                        M1AFailureCode.VALIDATION,
                        attempts=attempts,
                        validation_errors=repair_errors,
                    )
                continue
            if m1a_program_hash(context) != initial_program_hash:
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            try:
                ai_content = assemble_m1a_narrative(draft, catalog)
            except (M1AEvidenceCatalogError, TypeError, ValueError):
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            if m1a_program_hash(context) != initial_program_hash:
                return self._failure(M1AFailureCode.PROGRAM_INTEGRITY, attempts=attempts)
            audit = M1AAuditSnapshot(
                service_version=M1A_SERVICE_VERSION,
                m1a_contract_version=M1A_CONTRACT_VERSION,
                prompt_version=M1A_PROMPT_VERSION,
                provider_schema_version=M1A_PROVIDER_SCHEMA_VERSION,
                validator_version=M1A_VALIDATOR_VERSION,
                narrative_assembly_version=M1A_NARRATIVE_ASSEMBLY_VERSION,
                evidence_catalog_version=catalog.catalog_version,
                provider_catalog_hash=catalog.provider_catalog_hash,
                private_catalog_hash=catalog.private_catalog_hash,
                program_hash=initial_program_hash,
                audit_id=hashlib.sha256(
                    f"{intake.question_id}:{initial_program_hash}".encode("utf-8")
                ).hexdigest()[:24],
                engine_version=context.engine_version,
                rule_version=context.rule_version,
            )
            release = narrative_release_snapshot()
            assembly = M1ANarrativeAssembly(
                program_content=context,
                ai_content=ai_content,
                audit=audit,
                narrative_release=release,
            )
            return M1AServiceResult(
                status=ServiceStatus.SUCCESS,
                assembly=assembly,
                provider_attempts=tuple(attempts),
                failure_code=None,
                validation_errors=(),
                narrative_release=release,
            )
        raise AssertionError("unreachable")

    @staticmethod
    def _failure(
        code: M1AFailureCode,
        *,
        attempts: list[M1AProviderAttempt] | None = None,
        validation_errors: list[str] | None = None,
    ) -> M1AServiceResult:
        status = (
            ServiceStatus.FAILED_VALIDATION
            if code in {M1AFailureCode.VALIDATION, M1AFailureCode.PROGRAM_INTEGRITY}
            else ServiceStatus.PROVIDER_FAILED
        )
        return M1AServiceResult(
            status=status,
            assembly=None,
            provider_attempts=tuple(attempts or ()),
            failure_code=code,
            validation_errors=tuple(validation_errors or ()),
            narrative_release=narrative_release_snapshot(),
        )
