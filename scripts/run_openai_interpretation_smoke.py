"""Optional live smoke test guarded by both an environment key and explicit confirmation."""

from __future__ import annotations

import argparse
import os
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
from abalo_iching.interpretation.models import InterpretationRequest
from abalo_iching.interpretation.openai_provider import OpenAIInterpretationProvider
from abalo_iching.interpretation.service import InterpretationService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-live-call", action="store_true")
    args = parser.parse_args()
    if not args.confirm_live_call:
        print("LIVE_CALL_NOT_RUN: pass --confirm-live-call and set OPENAI_API_KEY to opt in.")
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        print("LIVE_CALL_NOT_RUN: OPENAI_API_KEY is not configured.")
        return 2
    chart = cast_meihua(
        MeihuaInput(
            100,
            27,
            368,
            datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
            "Asia/Shanghai",
            "fixed-live-smoke",
        )
    )
    request = InterpretationRequest(
        question_id="fixed-live-smoke",
        question_domain=QuestionDomain.CAREER,
        normalized_question="是否继续验证当前固定测试方案？",
        decision_goal="验证结构化解释适配器",
        time_horizon="当前测试阶段",
        real_world_context="固定测试数据，不包含真实用户资料。",
        chart=chart,
    )
    result = InterpretationService(OpenAIInterpretationProvider()).interpret(request)
    metadata = result.interpretation.model_metadata
    print("LIVE_CALL_SUCCESS=true")
    print(f"response_id={metadata.response_id}")
    print(f"model={metadata.model}")
    print(f"input_tokens={metadata.input_tokens}")
    print(f"output_tokens={metadata.output_tokens}")
    print(f"total_tokens={metadata.total_tokens}")
    print(f"latency_ms={metadata.latency_ms}")
    print("validation=PASS")
    print(f"narrative_release_status={result.interpretation.narrative_release.narrative_release_status.value}")
    print(f"is_preview={str(result.is_preview).lower()}")
    print(f"should_charge={str(result.should_charge).lower()}")
    print(f"persist_as_formal_report_allowed={str(result.persist_as_formal_report_allowed).lower()}")
    print("notice=内部评测结果，不构成正式报告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
