from __future__ import annotations

import hashlib
import json
from typing import Literal, TypeAlias

from pydantic import Field, model_validator

from .calibration_cases import VisibleCalibrationCase, build_request
from .calibration_prompt_builder import Gate2CalibrationPromptBuilder
from .models import (
    EV_PATTERN,
    RW_PATTERN,
    TRACE_PATTERN,
    ExperimentArm,
    Gate2ExperimentOutput,
    Gate2ExperimentRequest,
    Gate2PromptPackage,
    LinkMode,
    RunMetadata,
    SourceKind,
    StrictModel,
)
from .validators import Gate2ExperimentValidator, gate2_validator_source_sha256


STAGE_C2_SCHEMA_VERSION = "gate2_schema_v2"
STAGE_C2_PROMPT_VERSION = "personalization_gate2_calibration_v4"
STAGE_C2_VALIDATOR_VERSION = "personalization_gate2_validator_v3"
STAGE_C2_EXTERNAL_MODEL_CALLS = 1
STAGE_C2_REAL_RETEST_AUTHORIZED = True
STAGE_C2_RETEST_REASONING_EFFORT = "medium"
STAGE_C2_RETEST_MAX_OUTPUT_TOKENS = 10_000

C2_SOURCE_TRACE_INSTRUCTIONS = """
阶段 C.2 source_trace 结构约束：
1. REALITY_FACT：trace_id 与 source_ref 必须是同一个 RWxx；link_mode 必须为 NOT_APPLICABLE；reality_refs 与 evidence_refs 必须都是空数组；interpretation_hypothesis 必须为 false。
2. CHART_FACT：trace_id 与 source_ref 必须是同一个 EVxx；link_mode 必须为 NOT_APPLICABLE；reality_refs 与 evidence_refs 必须都是空数组；interpretation_hypothesis 必须为 false。
3. REALITY_ONLY 的 INTERPRETIVE_LINK：trace_id 与 source_ref 必须是同一个 ILxx；reality_refs 必须非空；evidence_refs 必须为空数组；interpretation_hypothesis 必须为 true。
4. REALITY_AND_CHART 的 INTERPRETIVE_LINK：trace_id 与 source_ref 必须是同一个 ILxx；reality_refs 与 evidence_refs 都必须非空；interpretation_hypothesis 必须为 true。
5. 事实项用自己的 source_ref 表示来源身份，不得再把自己的 RWxx 或 EVxx 重复写入 reality_refs 或 evidence_refs；这两个引用数组只供 INTERPRETIVE_LINK 使用。
""".strip()


class _SourceTraceIdentity(StrictModel):
    trace_id: str = Field(pattern=TRACE_PATTERN)
    source_ref: str = Field(pattern=TRACE_PATTERN)
    supports_fields: list[str] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_matching_identity(self) -> _SourceTraceIdentity:
        if self.trace_id != self.source_ref:
            raise ValueError("trace_id 与 source_ref 必须一致")
        return self


class RealityFactSourceTraceV2(_SourceTraceIdentity):
    trace_id: str = Field(pattern=RW_PATTERN)
    source_kind: Literal[SourceKind.REALITY_FACT]
    source_ref: str = Field(pattern=RW_PATTERN)
    link_mode: Literal[LinkMode.NOT_APPLICABLE]
    reality_refs: list[str] = Field(min_length=0, max_length=0)
    evidence_refs: list[str] = Field(min_length=0, max_length=0)
    interpretation_hypothesis: Literal[False]


class ChartFactSourceTraceV2(_SourceTraceIdentity):
    trace_id: str = Field(pattern=EV_PATTERN)
    source_kind: Literal[SourceKind.CHART_FACT]
    source_ref: str = Field(pattern=EV_PATTERN)
    link_mode: Literal[LinkMode.NOT_APPLICABLE]
    reality_refs: list[str] = Field(min_length=0, max_length=0)
    evidence_refs: list[str] = Field(min_length=0, max_length=0)
    interpretation_hypothesis: Literal[False]


class RealityOnlyInterpretiveSourceTraceV2(_SourceTraceIdentity):
    trace_id: str = Field(pattern=r"^IL\d{2}$")
    source_kind: Literal[SourceKind.INTERPRETIVE_LINK]
    source_ref: str = Field(pattern=r"^IL\d{2}$")
    link_mode: Literal[LinkMode.REALITY_ONLY]
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(min_length=0, max_length=0)
    interpretation_hypothesis: Literal[True]


class RealityAndChartInterpretiveSourceTraceV2(_SourceTraceIdentity):
    trace_id: str = Field(pattern=r"^IL\d{2}$")
    source_kind: Literal[SourceKind.INTERPRETIVE_LINK]
    source_ref: str = Field(pattern=r"^IL\d{2}$")
    link_mode: Literal[LinkMode.REALITY_AND_CHART]
    reality_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    interpretation_hypothesis: Literal[True]


SourceTraceV2: TypeAlias = (
    RealityFactSourceTraceV2
    | ChartFactSourceTraceV2
    | RealityOnlyInterpretiveSourceTraceV2
    | RealityAndChartInterpretiveSourceTraceV2
)


class Gate2ExperimentOutputV2(Gate2ExperimentOutput):
    source_trace: list[SourceTraceV2] = Field(min_length=1, max_length=80)


class Gate2StageC2RunMetadata(RunMetadata):
    max_output_tokens: int = Field(ge=1, le=25_000)


class Gate2StageC2ExperimentRequest(Gate2ExperimentRequest):
    metadata: Gate2StageC2RunMetadata


def gate2_output_schema_v2_sha256() -> str:
    payload = json.dumps(
        Gate2ExperimentOutputV2.model_json_schema(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class Gate2StageC2PromptBuilder:
    version = STAGE_C2_PROMPT_VERSION

    def build(self, request: Gate2ExperimentRequest) -> Gate2PromptPackage:
        base = Gate2CalibrationPromptBuilder().build(request)
        payload = dict(base.input_payload)
        payload["output_schema"] = Gate2ExperimentOutputV2.model_json_schema()
        system_instructions = (
            f"{base.system_instructions}\n\n{C2_SOURCE_TRACE_INSTRUCTIONS}"
        )
        payload_text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        prompt_sha256 = hashlib.sha256(
            f"{system_instructions}\n{payload_text}".encode("utf-8")
        ).hexdigest()
        return Gate2PromptPackage(
            prompt_version=self.version,
            system_instructions=system_instructions,
            input_payload=payload,
            prompt_sha256=prompt_sha256,
        )


class Gate2StageC2Validator(Gate2ExperimentValidator):
    version = STAGE_C2_VALIDATOR_VERSION


def gate2_validator_v3_sha256() -> str:
    payload = (
        f"{STAGE_C2_VALIDATOR_VERSION}:"
        f"{gate2_validator_source_sha256()}:"
        f"{gate2_output_schema_v2_sha256()}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_stage_c2_request(
    case: VisibleCalibrationCase,
    arm: ExperimentArm,
) -> Gate2ExperimentRequest:
    if arm is ExperimentArm.A:
        raise ValueError("阶段 C.2只评审模型输出契约，不重跑A组确定性基线")
    request = build_request(case, arm)
    metadata = request.metadata.model_copy(
        update={
            "prompt_version": STAGE_C2_PROMPT_VERSION,
            "schema_version": STAGE_C2_SCHEMA_VERSION,
            "validator_version": STAGE_C2_VALIDATOR_VERSION,
        }
    )
    return request.model_copy(update={"metadata": metadata})


def build_stage_c2_retest_request(
    case: VisibleCalibrationCase,
    arm: ExperimentArm,
) -> Gate2StageC2ExperimentRequest:
    request = build_stage_c2_request(case, arm)
    payload = request.model_dump(mode="json")
    payload["metadata"].update(
        {
            "reasoning_effort": STAGE_C2_RETEST_REASONING_EFFORT,
            "max_output_tokens": STAGE_C2_RETEST_MAX_OUTPUT_TOKENS,
        }
    )
    return Gate2StageC2ExperimentRequest.model_validate(payload)
