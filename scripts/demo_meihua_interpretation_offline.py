"""Run the Phase 2 pipeline with a deterministic fake provider; never calls OpenAI."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abalo_iching import MeihuaInput, cast_meihua
from abalo_iching.interpretation.enums import QuestionDomain
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider, build_conservative_fake_output
from abalo_iching.interpretation.knowledge import select_knowledge
from abalo_iching.interpretation.models import InterpretationRequest
from abalo_iching.interpretation.serialization import service_result_to_json
from abalo_iching.interpretation.service import InterpretationService
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer


def main() -> None:
    chart = cast_meihua(
        MeihuaInput(
            100,
            27,
            368,
            datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
            "Asia/Shanghai",
            "phase2-offline-demo",
        )
    )
    request = InterpretationRequest(
        question_id="phase2-offline-demo",
        question_domain=QuestionDomain.CAREER,
        normalized_question="当前合作方案是否值得继续推进？",
        decision_goal="决定是否进入下一轮低风险验证",
        time_horizon="未来三个月",
        real_world_context="目前只有初步方案，尚未签署不可撤回承诺。",
        chart=chart,
    )
    knowledge = select_knowledge(chart)
    synthesis = ConclusionSynthesizer().synthesize(chart, knowledge)
    fake_output = build_conservative_fake_output(request, synthesis)
    result = InterpretationService(FakeInterpretationProvider([fake_output])).interpret(request)
    print("provider=FAKE")
    print("not_a_live_openai_result=true")
    print(service_result_to_json(result))


if __name__ == "__main__":
    main()
