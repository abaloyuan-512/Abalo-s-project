from __future__ import annotations

from decimal import Decimal

from .background_provider import (
    STAGE_C1_MAX_OUTPUT_TOKENS,
    STAGE_C1_REASONING_EFFORT,
)
from .calibration_cases import VisibleCalibrationCase, build_request
from .models import ExperimentArm, Gate2ExperimentRequest


STAGE_C1_CONFIG_VERSION = "personalization_gate2_stage_c1_candidate_v1"
PROPOSED_AUTHORIZED_SPEND_USD = Decimal("0.45")
PROPOSED_MAX_GENERATION_CALLS = 1
PAID_RETEST_AUTHORIZED = True
PAID_RETEST_AUTHORIZATION_CONSUMED = True


def build_stage_c1_request(
    case: VisibleCalibrationCase,
    arm: ExperimentArm,
) -> Gate2ExperimentRequest:
    if arm is ExperimentArm.A:
        raise ValueError("阶段 C.1付费复测不调用A组基线")
    request = build_request(case, arm)
    metadata = request.metadata.model_copy(
        update={
            "reasoning_effort": STAGE_C1_REASONING_EFFORT,
            "max_output_tokens": STAGE_C1_MAX_OUTPUT_TOKENS,
        }
    )
    return request.model_copy(update={"metadata": metadata})
