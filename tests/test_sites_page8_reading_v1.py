from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from abalo_iching.application.sites_meihua_service_v3 import (
    CONTRACT_VERSION_V3,
    process_sites_meihua_v3_request,
)
from abalo_iching.application.sites_page8_reading_v1 import (
    PAGE8_READING_VERSION,
    PAGE8_SCENE_ORDER,
    Page8LayerInterpretationV1,
    Page8SceneId,
    build_page8_reading_v1,
)


FIXED_NOW = datetime(2026, 8, 3, 1, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def _deterministic_result() -> dict:
    response = process_sites_meihua_v3_request(
        {
            "contract_version": CONTRACT_VERSION_V3,
            "request_id": "page8-model-test",
            "question_text": "这次合作已经反复推迟，我还应该继续投入吗？",
            "question_domain": "PROJECT_COOPERATION",
            "decision_goal": "PLAN_NEXT_STEP",
            "time_horizon": "NEXT_30_DAYS",
            "decision_stage": "ALREADY_ACTING",
            "key_uncertainty": "OTHER_RESPONSE",
            "decision_risk_profile": "STANDARD",
            "numbers": [7, 8, 9],
            "locale": "zh-CN",
            "client_timestamp": "2026-08-03T00:58:00+08:00",
            "user_acknowledgements": {
                "deterministic_only": True,
                "narrative_unverified": True,
                "question_text_not_evidence": True,
            },
        },
        clock=lambda: FIXED_NOW,
    )
    assert response["status"] == "SUCCESS"
    return response["deterministic_result"]


def _layers() -> list[Page8LayerInterpretationV1]:
    evidence = {
        Page8SceneId.BASE_HEXAGRAM: ["EV10"],
        Page8SceneId.MUTUAL_HEXAGRAM: ["EV11"],
        Page8SceneId.CHANGED_HEXAGRAM: ["EV12"],
        Page8SceneId.MOVING_LINE: ["EV13"],
        Page8SceneId.BODY_USE_STRENGTH: ["EV02", "EV03", "EV06"],
    }
    return [
        Page8LayerInterpretationV1(
            scene_id=scene_id,
            layer_summary=f"{scene_id.value} 这一层只说明卦象结构提供的观察角度。",
            reality_connection="它只与用户明确写下的合作反复推迟这一事实相连接，不补写其他信息。",
            uncertainty_boundary="这不能证明现实结果，也不能替代仍未知的负责人答复。",
            reality_refs=["RW01"],
            evidence_refs=evidence[scene_id],
            interpretation_hypothesis=True,
        )
        for scene_id in PAGE8_SCENE_ORDER
    ]


def test_page8_model_has_exact_five_scene_order_and_reserves_page9() -> None:
    reading = build_page8_reading_v1(
        user_question="这次合作已经反复推迟，我还应该继续投入吗？",
        deterministic_result=_deterministic_result(),
        interpretations=_layers(),
    )

    assert reading.template_version == PAGE8_READING_VERSION
    assert [scene.scene_id for scene in reading.scenes] == list(PAGE8_SCENE_ORDER)
    assert [scene.title for scene in reading.scenes] == ["本卦", "互卦", "变卦", "动爻", "体用与旺衰"]
    assert reading.page9_reserved is True
    assert reading.scenes[0].deterministic.facts[0].label == "上卦"
    assert reading.scenes[3].deterministic.canonical_label == "爻辞原文"
    assert "吉凶总评" in reading.scenes[4].purpose


def test_each_scene_requires_its_specific_chart_evidence() -> None:
    with pytest.raises(ValidationError):
        Page8LayerInterpretationV1(
            scene_id=Page8SceneId.MUTUAL_HEXAGRAM,
            layer_summary="这一层说明互卦内部结构提供的观察角度。",
            reality_connection="这里只连接用户明确提供的现实事实，不补写未知信息。",
            uncertainty_boundary="这不能证明现实结果，也不能替代现实答复。",
            reality_refs=["RW01"],
            evidence_refs=["EV10"],
            interpretation_hypothesis=True,
        )


def test_page8_deterministic_blocks_do_not_mix_in_user_question() -> None:
    question = "这次合作已经反复推迟，我还应该继续投入吗？"
    reading = build_page8_reading_v1(
        user_question=question,
        deterministic_result=_deterministic_result(),
        interpretations=_layers(),
    )

    for scene in reading.scenes:
        deterministic_text = scene.deterministic.model_dump_json()
        assert question not in deterministic_text
        assert "RW01" not in deterministic_text
