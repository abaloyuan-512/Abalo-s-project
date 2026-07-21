from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Protocol

from pydantic import ValidationError

from .background_provider import OpenAIGate2BackgroundProvider
from .budget import Gate2BudgetError, Gate2CalibrationBudgetGuard
from .calibration_prompt_builder import Gate2CalibrationPromptBuilder
from .live_provider import Gate2LiveProviderError
from .models import (
    DatasetRole,
    DryRunStatus,
    ExperimentArm,
    Gate2DryRunResult,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    Gate2PromptPackage,
    Gate2ValidationReport,
    OUTPUT_SCHEMA_VERSION,
    ValidationFailure,
    gate2_output_schema_sha256,
)
from .prompt_builder import Gate2PromptBuilder
from .runner import Gate2ExecutionBlocked, Gate2OfflineRunner
from .validators import Gate2ExperimentValidator, gate2_validator_source_sha256


class Gate2PromptBuilderLike(Protocol):
    version: str

    def build(self, request: Gate2ExperimentRequest) -> Gate2PromptPackage: ...


class Gate2BackgroundCalibrationRunner:
    """阶段 C.1后台校准运行器；恢复轮询不会创建新生成。"""

    stage_label = "C.1"
    provider_type: ClassVar[type[OpenAIGate2BackgroundProvider]] = (
        OpenAIGate2BackgroundProvider
    )
    output_model: ClassVar[type[Gate2ExperimentOutput]] = Gate2ExperimentOutput
    schema_version = OUTPUT_SCHEMA_VERSION
    schema_sha256_factory: ClassVar[Callable[[], str]] = staticmethod(
        gate2_output_schema_sha256
    )
    validator_sha256_factory: ClassVar[Callable[[], str]] = (
        staticmethod(gate2_validator_source_sha256)
    )
    offline_only = False

    def __init__(
        self,
        *,
        repository_root: Path,
        budget_guard: Gate2CalibrationBudgetGuard,
        prompt_builder: Gate2PromptBuilderLike | None = None,
        validator: Gate2ExperimentValidator | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or Gate2CalibrationPromptBuilder()
        self.validator = validator or Gate2ExperimentValidator()
        self.budget_guard = budget_guard
        self._offline_support = Gate2OfflineRunner(
            repository_root=repository_root,
            prompt_builder=self.prompt_builder,
            validator=self.validator,
        )

    def run(
        self,
        request: Gate2ExperimentRequest,
        *,
        provider: OpenAIGate2BackgroundProvider,
        evidence_root: Path,
        resume_response_id: str | None = None,
    ) -> Gate2DryRunResult:
        Gate2OfflineRunner._assert_request_allowed(request)
        self._assert_component_versions(request)
        if request.metadata.dataset_role is not DatasetRole.CALIBRATION:
            raise Gate2ExecutionBlocked(
                f"阶段 {self.stage_label}只允许可见合成校准集"
            )
        if request.metadata.arm is ExperimentArm.A:
            raise Gate2ExecutionBlocked(
                f"阶段 {self.stage_label}后台运行器不调用A组基线"
            )
        if type(provider) is not self.provider_type:
            raise Gate2ExecutionBlocked(
                f"阶段 {self.stage_label}只接受隔离的后台Provider"
            )
        if request.metadata.model != provider.model:
            raise Gate2ExecutionBlocked(
                f"请求模型与阶段 {self.stage_label}后台Provider不一致"
            )
        if request.metadata.reasoning_effort != provider.reasoning_effort:
            raise Gate2ExecutionBlocked(
                f"请求推理档位与阶段 {self.stage_label}后台Provider不一致"
            )
        if request.metadata.max_output_tokens != provider.max_output_tokens:
            raise Gate2ExecutionBlocked(
                f"请求输出上限与阶段 {self.stage_label}后台Provider不一致"
            )

        prompt = self.prompt_builder.build(request)
        if self.offline_only:
            if not provider.offline_simulation:
                raise Gate2ExecutionBlocked("离线运行器拒绝非模拟后台Provider")
            estimated_cost = Decimal("0")
        else:
            estimated_cost = provider.pricing.conservative_preflight_estimate(
                prompt,
                max_output_tokens=provider.max_output_tokens,
            )
        self.budget_guard.authorize(estimated_cost)

        provider_result = None
        provider_failure: Gate2LiveProviderError | None = None
        parsed_output = None
        validation = Gate2ValidationReport()
        status = DryRunStatus.PROVIDER_FAILED
        try:
            if resume_response_id:
                provider_result = provider.resume(
                    prompt,
                    response_id=resume_response_id,
                )
            else:
                provider_result = provider.generate(prompt)
            if provider_result.provider_name != provider.provider_name:
                raise Gate2LiveProviderError(
                    "provider_identity_mismatch",
                    f"后台Provider返回来源标记与阶段 {self.stage_label}配置不一致",
                    response_id=provider_result.response_id,
                    api_status=provider_result.api_status,
                    usage=provider_result.usage,
                    latency_ms=provider_result.latency_ms,
                    cost_usd=provider_result.cost_usd,
                    background_mode=True,
                    poll_count=provider_result.poll_count,
                    raw_output=provider_result.raw_output,
                )
            self.budget_guard.record_actual_cost(
                Decimal(str(provider_result.cost_usd))
            )
            if self.offline_only and provider_result.cost_usd != 0:
                raise Gate2BudgetError("离线模拟Provider的实际费用必须为0美元")
            parsed_output = self.output_model.model_validate(
                provider_result.raw_output
            )
        except ValidationError as exc:
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code="schema_invalid",
                        message=str(exc)[:800],
                    )
                ]
            )
            status = DryRunStatus.SCHEMA_FAILED
        except Gate2BudgetError as exc:
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code="actual_budget_exceeded",
                        message=str(exc)[:800],
                    )
                ]
            )
            status = DryRunStatus.FAILED_VALIDATION
        except Gate2LiveProviderError as exc:
            provider_failure = exc
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code=exc.code,
                        message=str(exc)[:800],
                        field_path=None,
                    )
                ]
            )
            status = DryRunStatus.PROVIDER_FAILED
        else:
            validation = self.validator.validate(request, parsed_output)
            status = (
                DryRunStatus.VALIDATED
                if validation.hard_passed and validation.quality_passed
                else DryRunStatus.FAILED_VALIDATION
            )

        record = self._offline_support._make_record(
            request=request,
            prompt_sha256=prompt.prompt_sha256,
            provider_result=provider_result,
            parsed_output=parsed_output,
            validation=validation,
            provider_name=provider.provider_name,
        )
        record = record.model_copy(
            update={
                "schema_version": self.schema_version,
                "schema_sha256": self.schema_sha256_factory(),
                "validator_sha256": self.validator_sha256_factory(),
            }
        )
        if provider_failure is not None:
            record = record.model_copy(
                update={
                    "first_raw_output": provider_failure.raw_output,
                    "usage": provider_failure.usage,
                    "latency_ms": provider_failure.latency_ms,
                    "cost_usd": provider_failure.cost_usd,
                    "response_id": provider_failure.response_id,
                    "api_status": provider_failure.api_status,
                    "incomplete_reason": provider_failure.incomplete_reason,
                    "background_mode": provider_failure.background_mode,
                    "poll_count": provider_failure.poll_count,
                }
            )
        record = record.model_copy(
            update={
                "human_review": {
                    "status": "PENDING",
                    "reviewer": None,
                    "scores": None,
                    "notes": None,
                }
            }
        )
        evidence_directory = self._offline_support._write_if_requested(
            record,
            evidence_root,
        )
        return Gate2DryRunResult(
            status=status,
            request=request,
            output=parsed_output,
            validation=validation,
            evidence_record=record,
            evidence_directory=evidence_directory,
        )

    def _assert_component_versions(self, request: Gate2ExperimentRequest) -> None:
        if request.metadata.schema_version != self.schema_version:
            raise Gate2ExecutionBlocked("请求的输出 Schema 版本与运行器不一致")
        if request.metadata.validator_version != self.validator.version:
            raise Gate2ExecutionBlocked("请求的实验 Validator 版本与运行器不一致")
        if request.metadata.prompt_version != self.prompt_builder.version:
            raise Gate2ExecutionBlocked("请求的实验 Prompt 版本与运行器不一致")
