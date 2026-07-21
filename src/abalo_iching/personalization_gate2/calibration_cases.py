from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from abalo_iching import MeihuaInput, cast_meihua
from abalo_iching.meihua import chart_to_dict

from .live_provider import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
)
from .calibration_prompt_builder import CALIBRATION_PROMPT_VERSION
from .models import (
    ChartContext,
    ChartEvidence,
    DatasetRole,
    ExperimentArm,
    ExperimentRunManifest,
    Gate2ExperimentRequest,
    KnowledgeReviewStatus,
    OUTPUT_SCHEMA_VERSION,
    RunManifestEntry,
    RunMetadata,
    SyntheticRealityContext,
)
from .validators import Gate2ExperimentValidator


CALIBRATION_SET_VERSION = "personalization_gate2_visible_calibration_v1"
CONTRACT_VERSION = "personalization_gate2_contract_v1"
MANIFEST_VERSION = "personalization_gate2_stage_c_manifest_v1"
SYNTHETIC_CAST_AT = datetime(
    2026,
    7,
    21,
    12,
    0,
    tzinfo=ZoneInfo("Asia/Shanghai"),
)


@dataclass(frozen=True)
class VisibleCalibrationCase:
    case_id: str
    reality_payload: dict[str, object]
    real_numbers: tuple[int, int, int]
    mismatched_numbers: tuple[int, int, int]


VISIBLE_CALIBRATION_CASES = (
    VisibleCalibrationCase(
        case_id="G2CAL-001",
        reality_payload={
            "synthetic_data_confirmed": True,
            "question_text": "一个内部改进方案已经准备了两周，直属负责人认可方向，但最终负责人还没有看到。团队资源即将重新分配，我应该继续完善，还是现在正式提出？",
            "question_domain": "工作",
            "decision_goal": "决定现在提交方案，还是继续内部准备",
            "explicit_facts": [
                {"ref": "RW01", "text": "改进方案已经准备了两周。"},
                {"ref": "RW02", "text": "直属负责人认可方案方向。"},
                {"ref": "RW03", "text": "最终负责人还没有看到方案。"},
            ],
            "unknowns": [
                {"text": "最终负责人是否支持该方案尚不明确。"},
                {"text": "资源重新分配后还能保留多少执行空间尚不明确。"},
            ],
            "options": [
                {"ref": "RW04", "text": "选择一是继续完善后再提交。"},
                {"ref": "RW05", "text": "选择二是现在提交并请求正式回应。"},
            ],
            "hard_constraints": [
                {"ref": "RW06", "text": "团队资源即将重新分配。"},
            ],
            "actions_already_taken": [
                {"ref": "RW07", "text": "已经完成方案主体并与直属负责人讨论。"},
            ],
            "observable_responses": [
                {"ref": "RW08", "text": "直属负责人明确表示认可方向。"},
            ],
        },
        real_numbers=(100, 27, 368),
        mismatched_numbers=(1, 3, 2),
    ),
    VisibleCalibrationCase(
        case_id="G2CAL-002",
        reality_payload={
            "synthetic_data_confirmed": True,
            "question_text": "两位合作者已经完成一次小规模试做，结果达到最低要求，但双方对长期分工还没有书面确认。现在要不要扩大投入？",
            "question_domain": "合作",
            "decision_goal": "决定是否从小规模试做转入更大投入",
            "explicit_facts": [
                {"ref": "RW01", "text": "双方已经完成一次小规模试做。"},
                {"ref": "RW02", "text": "试做结果达到事先约定的最低要求。"},
                {"ref": "RW03", "text": "长期分工尚未书面确认。"},
            ],
            "unknowns": [
                {"text": "双方对长期责任边界是否真正一致尚不明确。"},
                {"text": "扩大投入后的收益分配尚不明确。"},
            ],
            "options": [
                {"ref": "RW04", "text": "选择一是立即扩大投入。"},
                {"ref": "RW05", "text": "选择二是先确认长期分工再决定投入。"},
            ],
            "hard_constraints": [
                {"ref": "RW06", "text": "扩大投入会占用双方下一阶段的主要资源。"},
            ],
            "actions_already_taken": [
                {"ref": "RW07", "text": "双方已经用一次试做验证基本协作能力。"},
            ],
            "observable_responses": [
                {"ref": "RW08", "text": "双方都确认试做达到最低要求。"},
            ],
        },
        real_numbers=(1, 3, 2),
        mismatched_numbers=(100, 27, 368),
    ),
)


def _chart(numbers: tuple[int, int, int], case_id: str):
    return cast_meihua(
        MeihuaInput(
            *numbers,
            SYNTHETIC_CAST_AT,
            "Asia/Shanghai",
            case_id,
        )
    )


def _chart_mapping_id(chart: object) -> str:
    payload = json.dumps(
        chart_to_dict(chart),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"CHART-{hashlib.sha256(payload).hexdigest()[:20]}"


def _chart_context(
    numbers: tuple[int, int, int],
    *,
    case_id: str,
    mismatched: bool,
) -> ChartContext:
    chart = _chart(numbers, case_id)
    evidence = [
        ChartEvidence(
            ref=f"EV{index:02d}",
            canonical_evidence_id=(
                f"{chart.versions.rule_version}:{item.evidence_id}"
            ),
            text=item.fact,
            knowledge_review_status=KnowledgeReviewStatus.CANONICAL_ONLY,
        )
        for index, item in enumerate(chart.evidence, start=1)
    ]
    return ChartContext(
        chart_mapping_id=_chart_mapping_id(chart),
        is_mismatched_control=mismatched,
        evidence=evidence,
    )


def _deterministic_baseline(case: VisibleCalibrationCase) -> str:
    chart = _chart(case.real_numbers, case.case_id)
    payload = {
        "base_hexagram": chart.base_hexagram.full_name_zh,
        "mutual_hexagram": chart.mutual_hexagram.full_name_zh,
        "changed_hexagram": chart.changed_hexagram.full_name_zh,
        "moving_line": chart.moving_line,
        "body_trigram": chart.body_trigram.name_zh,
        "initial_use_trigram": chart.initial_use_trigram.name_zh,
        "changed_use_trigram": chart.changed_use_trigram.name_zh,
        "evidence": [item.fact for item in chart.evidence],
        "exact_date_feature_enabled": chart.timing.exact_date_feature_enabled,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def build_request(
    case: VisibleCalibrationCase,
    arm: ExperimentArm,
) -> Gate2ExperimentRequest:
    chart_context = None
    deterministic_output = None
    if arm is ExperimentArm.A:
        deterministic_output = _deterministic_baseline(case)
    elif arm is ExperimentArm.C:
        chart_context = _chart_context(
            case.real_numbers,
            case_id=case.case_id,
            mismatched=False,
        )
    elif arm is ExperimentArm.D:
        chart_context = _chart_context(
            case.mismatched_numbers,
            case_id=f"{case.case_id}-MISMATCH",
            mismatched=True,
        )

    metadata = RunMetadata(
        case_id=case.case_id,
        arm=arm,
        dataset_role=DatasetRole.CALIBRATION,
        contract_version=CONTRACT_VERSION,
        prompt_version=(
            "NOT_APPLICABLE"
            if arm is ExperimentArm.A
            else CALIBRATION_PROMPT_VERSION
        ),
        schema_version=OUTPUT_SCHEMA_VERSION,
        validator_version=Gate2ExperimentValidator.version,
        model=("NOT_APPLICABLE" if arm is ExperimentArm.A else DEFAULT_MODEL),
        reasoning_effort=(
            "NOT_APPLICABLE" if arm is ExperimentArm.A else DEFAULT_REASONING_EFFORT
        ),
        max_output_tokens=(1 if arm is ExperimentArm.A else DEFAULT_MAX_OUTPUT_TOKENS),
        store=False,
        tools=[],
    )
    return Gate2ExperimentRequest(
        metadata=metadata,
        reality=SyntheticRealityContext.model_validate(case.reality_payload),
        chart_context=chart_context,
        deterministic_v16_output=deterministic_output,
    )


def build_manifest() -> ExperimentRunManifest:
    entries = []
    for case in VISIBLE_CALIBRATION_CASES:
        real = _chart_context(
            case.real_numbers,
            case_id=case.case_id,
            mismatched=False,
        )
        mismatch = _chart_context(
            case.mismatched_numbers,
            case_id=f"{case.case_id}-MISMATCH",
            mismatched=True,
        )
        entries.append(
            RunManifestEntry(
                case_id=case.case_id,
                arm_order=(
                    ExperimentArm.A,
                    ExperimentArm.B,
                    ExperimentArm.C,
                    ExperimentArm.D,
                ),
                real_chart_mapping_id=real.chart_mapping_id,
                mismatched_chart_mapping_id=mismatch.chart_mapping_id,
            )
        )
    return ExperimentRunManifest(
        manifest_version=MANIFEST_VERSION,
        locked_payload_included=False,
        entries=entries,
    )
