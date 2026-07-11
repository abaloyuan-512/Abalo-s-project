import json

import pytest

from abalo_iching.interpretation.models import ServiceResult
from abalo_iching.interpretation.serialization import (
    interpretation_from_json,
    interpretation_content_from_json,
    interpretation_content_to_json,
    interpretation_to_json,
    service_result_from_json,
    service_result_to_json,
)
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider
from abalo_iching.interpretation.service import InterpretationService
from abalo_iching.meihua.exceptions import InputValidationError
from abalo_iching.meihua.serialization import chart_from_untrusted_json, chart_to_json


def test_interpretation_json_round_trip(valid_interpretation):
    assert interpretation_content_from_json(interpretation_content_to_json(valid_interpretation)) == valid_interpretation


def test_service_result_json_round_trip(phase2_request, valid_interpretation):
    result = InterpretationService(FakeInterpretationProvider([valid_interpretation])).interpret(phase2_request)
    assert service_result_from_json(service_result_to_json(result)) == result


def test_untrusted_chart_is_recomputed_and_accepted_only_when_exact(phase2_chart):
    assert chart_from_untrusted_json(chart_to_json(phase2_chart)) == phase2_chart


@pytest.mark.parametrize("path,value", [
    (("moving_line",), 6),
    (("base_hexagram", "king_wen_number"), 1),
    (("timing", "exact_date_feature_enabled"), True),
    (("timing", "candidate_dates"), ["2026-08-08"]),
])
def test_untrusted_chart_rejects_forged_derived_fields(phase2_chart, path, value):
    payload = json.loads(chart_to_json(phase2_chart))
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(InputValidationError, match="forged or inconsistent"):
        chart_from_untrusted_json(json.dumps(payload, ensure_ascii=False))


def test_serialized_interpretation_contains_no_key_or_complete_internal_prompt(valid_interpretation):
    payload = interpretation_content_to_json(valid_interpretation).lower()
    assert "api_key" not in payload
    assert "你是梅花易数结构化解释层" not in payload
