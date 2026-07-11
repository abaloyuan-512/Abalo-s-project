"""Orchestrate deterministic synthesis, provider output, one repair, and local validation."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from zoneinfo import TZPATH

from .enums import NarrativeReleaseStatus, ServiceStatus
from .exceptions import InterpretationValidationError
from .knowledge import KnowledgeAccessPolicy, select_knowledge
from .models import InterpretationRequest, MeihuaInterpretation, ModelMetadata, ServiceResult
from .prompt_builder import PromptBuilder
from .provider_protocol import InterpretationProvider
from .renderer import ProgramInterpretationRenderer
from .release import narrative_release_snapshot
from .synthesis import ConclusionSynthesizer
from .validators import InterpretationValidator


def timezone_version_snapshot() -> tuple[str, str, str]:
    try:
        tzdata_version = version("tzdata")
    except PackageNotFoundError:
        return (
            "NOT_INSTALLED",
            "SYSTEM_TZ_DATABASE",
            "SYSTEM_TZ_DATABASE_VERSION_UNAVAILABLE",
        )
    system_zone_paths_exist = any(Path(path).exists() for path in TZPATH)
    if system_zone_paths_exist:
        return (
            tzdata_version,
            "PYTHON_ZONEINFO_WITH_TZDATA_FALLBACK",
            "SYSTEM_TZ_DATABASE_VERSION_UNAVAILABLE",
        )
    return (tzdata_version, "PYTHON_TZDATA_PACKAGE", "SYSTEM_TZ_DATABASE_VERSION_UNAVAILABLE")


class InterpretationService:
    def __init__(
        self,
        provider: InterpretationProvider,
        *,
        synthesizer: ConclusionSynthesizer | None = None,
        validator: InterpretationValidator | None = None,
        prompt_builder: PromptBuilder | None = None,
        knowledge_access_policy: KnowledgeAccessPolicy | None = None,
        renderer: ProgramInterpretationRenderer | None = None,
    ) -> None:
        self.provider = provider
        self.synthesizer = synthesizer or ConclusionSynthesizer()
        self.validator = validator or InterpretationValidator()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.knowledge_access_policy = knowledge_access_policy or KnowledgeAccessPolicy()
        self.renderer = renderer or ProgramInterpretationRenderer()

    def interpret(self, request: InterpretationRequest) -> ServiceResult:
        knowledge = select_knowledge(request.chart, policy=self.knowledge_access_policy)
        synthesis = self.synthesizer.synthesize(request.chart, knowledge)
        program_content = self.renderer.render(request, knowledge, synthesis)
        repair_errors: list[str] | None = None
        provider_attempts: list[dict[str, int | str | None]] = []
        for attempt in (1, 2):
            prompt = self.prompt_builder.build(
                request,
                knowledge,
                synthesis,
                repair_errors=repair_errors,
            )
            provider_result = self.provider.generate(prompt, attempt_number=attempt)
            provider_attempts.append(
                {
                    "provider_name": provider_result.provider_name,
                    "response_id": provider_result.response_id,
                    "model": provider_result.model,
                    "input_tokens": provider_result.input_tokens,
                    "output_tokens": provider_result.output_tokens,
                    "total_tokens": provider_result.total_tokens,
                    "attempt_number": provider_result.attempt_number,
                }
            )
            try:
                output = self.validator.validate(provider_result.parsed_output, request, knowledge, synthesis)
            except InterpretationValidationError as exc:
                repair_errors = list(exc.errors)
                if attempt == 2:
                    raise InterpretationValidationError(
                        repair_errors,
                        attempts=2,
                        provider_attempts=tuple(provider_attempts),
                    ) from exc
                continue
            tzdata_version, timezone_source, system_note = timezone_version_snapshot()
            metadata = ModelMetadata(
                provider_name=provider_result.provider_name,
                response_id=provider_result.response_id,
                model=provider_result.model,
                input_tokens=provider_result.input_tokens,
                output_tokens=provider_result.output_tokens,
                total_tokens=provider_result.total_tokens,
                latency_ms=provider_result.latency_ms,
                attempt_number=provider_result.attempt_number,
                prompt_version=provider_result.prompt_version,
                tzdata_package_version=tzdata_version,
                timezone_source=timezone_source,
                system_tz_database_note=system_note,
            )
            interpretation = MeihuaInterpretation(
                program_content=program_content,
                ai_content=output,
                model_metadata=metadata,
                narrative_release=narrative_release_snapshot(),
            )
            is_fake = provider_result.provider_name == "FAKE"
            release_allows_formal = (
                interpretation.narrative_release.narrative_release_status
                is NarrativeReleaseStatus.APPROVED_FOR_CLOSED_BETA
            )
            is_preview = knowledge.is_preview or not release_allows_formal or is_fake
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                interpretation=interpretation,
                synthesis=synthesis,
                should_charge=release_allows_formal and not is_preview and not is_fake,
                not_a_live_openai_result=is_fake,
                is_preview=is_preview,
                persist_as_formal_report_allowed=release_allows_formal and not is_preview and not is_fake,
            )
        raise AssertionError("unreachable")
