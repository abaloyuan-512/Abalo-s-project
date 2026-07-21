from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from .budget import Gate2BudgetError, Gate2CalibrationBudgetGuard
from .calibration_prompt_builder import Gate2CalibrationPromptBuilder
from .live_provider import Gate2LiveProviderError, OpenAIGate2Provider
from .models import (
    DatasetRole,
    DryRunStatus,
    ExperimentArm,
    Gate2DryRunResult,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    Gate2ValidationReport,
    ValidationFailure,
)
from .prompt_builder import Gate2PromptBuilder
from .runner import Gate2ExecutionBlocked, Gate2OfflineRunner
from .validators import Gate2ExperimentValidator


class Gate2CalibrationRunner:
    """阶段 C 可见合成校准运行器；每个结果只有一次真实生成。"""

    def __init__(
        self,
        *,
        repository_root: Path,
        budget_guard: Gate2CalibrationBudgetGuard,
        prompt_builder: Gate2PromptBuilder | None = None,
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
        provider: OpenAIGate2Provider,
        evidence_root: Path,
    ) -> Gate2DryRunResult:
        Gate2OfflineRunner._assert_request_allowed(request)
        self._offline_support._assert_component_versions(request)
        if request.metadata.dataset_role is not DatasetRole.CALIBRATION:
            raise Gate2ExecutionBlocked("阶段 C 只允许可见合成校准集")
        if request.metadata.arm is ExperimentArm.A:
            raise Gate2ExecutionBlocked("阶段 C 真实运行器不调用 A 组基线")
        if type(provider) is not OpenAIGate2Provider:
            raise Gate2ExecutionBlocked("阶段 C 只接受隔离的 OpenAIGate2Provider")
        if request.metadata.model != provider.model:
            raise Gate2ExecutionBlocked("请求模型与阶段 C Provider 模型不一致")
        if request.metadata.reasoning_effort != provider.reasoning_effort:
            raise Gate2ExecutionBlocked("请求推理档位与阶段 C Provider 不一致")
        if request.metadata.max_output_tokens != provider.max_output_tokens:
            raise Gate2ExecutionBlocked("请求输出上限与阶段 C Provider 不一致")

        prompt = self.prompt_builder.build(request)
        estimated_cost = provider.pricing.conservative_preflight_estimate(
            prompt,
            max_output_tokens=provider.max_output_tokens,
        )
        self.budget_guard.authorize(estimated_cost)

        provider_result = None
        parsed_output = None
        validation = Gate2ValidationReport()
        status = DryRunStatus.PROVIDER_FAILED
        try:
            provider_result = provider.generate(prompt)
            if provider_result.provider_name != provider.provider_name:
                raise Gate2LiveProviderError(
                    "provider_identity_mismatch",
                    "Provider 返回来源标记与阶段 C 配置不一致",
                )
            self.budget_guard.record_actual_cost(
                Decimal(str(provider_result.cost_usd))
            )
            parsed_output = Gate2ExperimentOutput.model_validate(
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
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code=exc.code,
                        message=str(exc)[:800],
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
        if provider_result is None:
            record = record.model_copy(update={"cost_usd": None})
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
