from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching import MeihuaInput, cast_meihua
from abalo_iching.interpretation.enums import QuestionDomain
from abalo_iching.interpretation.fake_provider import build_conservative_fake_output
from abalo_iching.interpretation.knowledge import select_knowledge
from abalo_iching.interpretation.models import InterpretationRequest
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer


@pytest.fixture
def phase2_chart():
    return cast_meihua(
        MeihuaInput(
            100,
            27,
            368,
            datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
            "Asia/Shanghai",
            "phase2-test",
        )
    )


@pytest.fixture
def phase2_request(phase2_chart):
    return InterpretationRequest(
        question_id="phase2-test",
        question_domain=QuestionDomain.CAREER,
        normalized_question="当前合作方案是否值得继续验证？",
        decision_goal="决定是否继续低风险验证",
        time_horizon="未来三个月",
        real_world_context="方案尚未签署不可撤回承诺。",
        chart=phase2_chart,
    )


@pytest.fixture
def phase2_knowledge(phase2_chart):
    return select_knowledge(phase2_chart)


@pytest.fixture
def phase2_synthesis(phase2_chart, phase2_knowledge):
    return ConclusionSynthesizer().synthesize(phase2_chart, phase2_knowledge)


@pytest.fixture
def valid_interpretation(phase2_request, phase2_synthesis):
    return build_conservative_fake_output(phase2_request, phase2_synthesis)
