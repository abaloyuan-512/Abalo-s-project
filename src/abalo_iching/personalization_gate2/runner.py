from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from .budget import Gate2BudgetError, Gate2BudgetGuard
from .evidence import Gate2EvidenceWriter
from .fake_provider import FakeGate2Provider
from .models import (
    DatasetRole,
    DryRunStatus,
    ExperimentArm,
    Gate2DryRunResult,
    Gate2EvidenceRecord,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    Gate2ProviderResult,
    Gate2Usage,
    Gate2ValidationReport,
    ValidationFailure,
    gate2_output_schema_sha256,
)
from .prompt_builder import Gate2PromptBuilder
from .provider_protocol import Gate2Provider
from .validators import Gate2ExperimentValidator, gate2_validator_source_sha256


_SENSITIVE_INPUT_PATTERNS = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("phone", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")),
    ("windows_path", re.compile(r"\b[A-Za-z]:\\[^\s\"']+")),
)


class Gate2ExecutionBlocked(RuntimeError):
    pass


class Gate2OfflineRunner:
    """Gate 2 阶段 A/B 的无网络运行器。

    它只接受 CALIBRATION 合成案例和 Fake Provider；每个 B/C/D 结果恰好调用一次，
    不自动修复，也不接入正式服务。
    """

    def __init__(
        self,
        *,
        repository_root: Path,
        prompt_builder: Gate2PromptBuilder | None = None,
        validator: Gate2ExperimentValidator | None = None,
        budget_guard: Gate2BudgetGuard | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or Gate2PromptBuilder()
        self.validator = validator or Gate2ExperimentValidator()
        self.budget_guard = budget_guard or Gate2BudgetGuard()
        self.evidence_writer = Gate2EvidenceWriter(repository_root=repository_root)

    def run(
        self,
        request: Gate2ExperimentRequest,
        *,
        provider: Gate2Provider | None = None,
        evidence_root: Path | None = None,
    ) -> Gate2DryRunResult:
        self._assert_request_allowed(request)
        if request.metadata.arm is ExperimentArm.A:
            return self._run_baseline(request, evidence_root=evidence_root)
        if provider is None:
            raise Gate2ExecutionBlocked("B/C/D 干跑必须显式提供 Fake Provider")
        if not isinstance(provider, FakeGate2Provider):
            raise Gate2ExecutionBlocked("阶段 A/B 运行器只接受内置 FakeGate2Provider")

        self.budget_guard.authorize(
            provider_name=provider.provider_name,
            estimated_cost_usd=Decimal("0"),
        )
        prompt = self.prompt_builder.build(request)
        provider_result: Gate2ProviderResult | None = None
        parsed_output: Gate2ExperimentOutput | None = None
        validation = Gate2ValidationReport()
        status = DryRunStatus.SCHEMA_FAILED

        try:
            provider_result = provider.generate(prompt)
            if provider_result.provider_name != "FAKE":
                raise Gate2BudgetError("Fake Provider 返回了非 FAKE 来源标记")
            self.budget_guard.record_actual_cost(Decimal(str(provider_result.cost_usd)))
            parsed_output = Gate2ExperimentOutput.model_validate(provider_result.raw_output)
        except Gate2BudgetError:
            raise
        except ValidationError as exc:
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code="schema_invalid",
                        message=str(exc)[:800],
                        field_path=None,
                    )
                ]
            )
        except Exception as exc:
            validation = Gate2ValidationReport(
                hard_failures=[
                    ValidationFailure(
                        code="provider_failure",
                        message=f"Fake Provider 运行失败：{exc}"[:800],
                        field_path=None,
                    )
                ]
            )
        else:
            validation = self.validator.validate(request, parsed_output)
            status = (
                DryRunStatus.VALIDATED
                if validation.hard_passed and validation.quality_passed
                else DryRunStatus.FAILED_VALIDATION
            )

        record = self._make_record(
            request=request,
            prompt_sha256=prompt.prompt_sha256,
            provider_result=provider_result,
            parsed_output=parsed_output,
            validation=validation,
            provider_name=provider.provider_name,
        )
        evidence_directory = self._write_if_requested(record, evidence_root)
        return Gate2DryRunResult(
            status=status,
            request=request,
            output=parsed_output,
            validation=validation,
            evidence_record=record,
            evidence_directory=evidence_directory,
        )

    def _run_baseline(
        self,
        request: Gate2ExperimentRequest,
        *,
        evidence_root: Path | None,
    ) -> Gate2DryRunResult:
        validation = Gate2ValidationReport()
        record = Gate2EvidenceRecord(
            case_id=request.metadata.case_id,
            arm=ExperimentArm.A,
            dataset_role=request.metadata.dataset_role,
            synthetic_data_confirmed=True,
            chart_mapping_id="NO_CHART",
            contract_version=request.metadata.contract_version,
            prompt_version="NOT_APPLICABLE",
            prompt_sha256=None,
            schema_version=request.metadata.schema_version,
            schema_sha256=gate2_output_schema_sha256(),
            validator_version=request.metadata.validator_version,
            validator_sha256=gate2_validator_source_sha256(),
            reality_reference_map={
                item.ref: item.text for item in request.reality.reality_facts()
            },
            evidence_reference_map={},
            provider_name="NONE",
            model="NOT_APPLICABLE",
            reasoning_effort="NOT_APPLICABLE",
            store=False,
            tools=[],
            first_raw_output={"deterministic_v16_output": request.deterministic_v16_output},
            parsed_output=None,
            validation=validation,
            usage=Gate2Usage(),
            latency_ms=0,
            cost_usd=0.0,
            response_id=None,
        )
        evidence_directory = self._write_if_requested(record, evidence_root)
        return Gate2DryRunResult(
            status=DryRunStatus.BASELINE,
            request=request,
            output=None,
            validation=validation,
            evidence_record=record,
            evidence_directory=evidence_directory,
        )

    def _make_record(
        self,
        *,
        request: Gate2ExperimentRequest,
        prompt_sha256: str,
        provider_result: Gate2ProviderResult | None,
        parsed_output: Gate2ExperimentOutput | None,
        validation: Gate2ValidationReport,
        provider_name: str,
    ) -> Gate2EvidenceRecord:
        chart_mapping_id = (
            request.chart_context.chart_mapping_id if request.chart_context else "NO_CHART"
        )
        return Gate2EvidenceRecord(
            case_id=request.metadata.case_id,
            arm=request.metadata.arm,
            dataset_role=request.metadata.dataset_role,
            synthetic_data_confirmed=True,
            chart_mapping_id=chart_mapping_id,
            contract_version=request.metadata.contract_version,
            prompt_version=request.metadata.prompt_version,
            prompt_sha256=prompt_sha256,
            schema_version=request.metadata.schema_version,
            schema_sha256=gate2_output_schema_sha256(),
            validator_version=request.metadata.validator_version,
            validator_sha256=gate2_validator_source_sha256(),
            reality_reference_map={
                item.ref: item.text for item in request.reality.reality_facts()
            },
            evidence_reference_map={
                item.ref: item.canonical_evidence_id
                for item in (request.chart_context.evidence if request.chart_context else [])
            },
            provider_name=provider_name,
            model=provider_result.model if provider_result else request.metadata.model,
            reasoning_effort=request.metadata.reasoning_effort,
            store=False,
            tools=[],
            first_raw_output=provider_result.raw_output if provider_result else None,
            parsed_output=parsed_output,
            validation=validation,
            usage=provider_result.usage if provider_result else Gate2Usage(),
            latency_ms=provider_result.latency_ms if provider_result else 0,
            cost_usd=provider_result.cost_usd if provider_result else 0.0,
            response_id=provider_result.response_id if provider_result else None,
        )

    def _write_if_requested(
        self,
        record: Gate2EvidenceRecord,
        evidence_root: Path | None,
    ) -> str | None:
        if evidence_root is None:
            return None
        return str(self.evidence_writer.write(record, evidence_root))

    @staticmethod
    def _assert_request_allowed(request: Gate2ExperimentRequest) -> None:
        if request.metadata.dataset_role is DatasetRole.LOCKED:
            raise Gate2ExecutionBlocked("阶段 A/B 不得创建、读取或运行锁定测试集")
        if not request.reality.synthetic_data_confirmed:
            raise Gate2ExecutionBlocked("阶段 A/B 只允许合成案例")
        serialized = json.dumps(request.model_dump(mode="json"), ensure_ascii=False)
        for name, pattern in _SENSITIVE_INPUT_PATTERNS:
            if pattern.search(serialized):
                raise Gate2ExecutionBlocked(f"合成输入疑似包含受保护信息：{name}")
