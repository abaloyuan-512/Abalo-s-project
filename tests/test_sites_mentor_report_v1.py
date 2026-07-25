from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application.sites_meihua_service_v2 import process_sites_meihua_v2_request

FIXED_NOW = datetime(2026, 7, 17, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def request(goal: str = "PLAN_NEXT_STEP") -> dict[str, object]:
    return {
        "contract_version": "SITES_MEIHUA_API_CONTRACT_V2",
        "request_id": f"mentor-report-{goal.lower()}",
        "question_domain": "PROJECT_COOPERATION",
        "decision_goal": goal,
        "time_horizon": "NEXT_30_DAYS",
        "numbers": [7, 8, 9],
        "locale": "zh-CN",
        "client_timestamp": "2026-07-17T10:00:00+08:00",
        "user_acknowledgements": {
            "deterministic_only": True,
            "narrative_unverified": True,
            "structured_question_confirmed": True,
        },
    }


def report(goal: str = "PLAN_NEXT_STEP") -> dict[str, object]:
    response = process_sites_meihua_v2_request(request(goal), clock=lambda: FIXED_NOW)
    assert response["status"] == "SUCCESS"
    return response["deterministic_result"]["mentor_report"]


def test_report_explains_chart_before_prescribing_action() -> None:
    value = report()
    assert value["template_version"] == "SITES_MENTOR_REPORT_V1"
    assert [item["title"].split("：", maxsplit=1)[0] for item in value["reading_guide"]] == [
        "先看本卦",
        "再看互卦",
        "最后看变卦",
    ]
    assert len(value["reasoning"]) >= 3
    assert len(value["action_plan"]) == 3
    assert all(item["why"].strip() for item in value["action_plan"])


@pytest.mark.parametrize(
    "goal",
    [
        "IDENTIFY_OBSTACLES",
        "PLAN_NEXT_STEP",
        "PREPARE_COMMUNICATION",
        "ADJUST_COMMITMENT_BOUNDARIES",
        "OBSERVE_VERIFY_SIGNALS",
    ],
)
def test_each_product_goal_gets_specific_reversible_guidance(goal: str) -> None:
    value = report(goal)
    assert len(value["action_plan"]) == 3
    assert len(value["review_questions"]) == 2
    assert any("现实" in item or "事实" in item for item in value["cautions"])


def test_report_keeps_epistemic_and_safety_boundaries_visible() -> None:
    text = str(report())
    for required in ["不代表未来必然走向", "现实反馈", "不可逆", "不使用真实模型"]:
        assert required in text
    for forbidden in ["保证成功", "注定", "必须分手", "一定会", "对方内心"]:
        assert forbidden not in text
