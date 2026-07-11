"""Build a normal wheel, install it cleanly, and run Phase 2 from an off-repository cwd."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    print(f"$ {' '.join(command)}")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    return result


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="abalo-phase2-wheel-") as temp_name:
        root = Path(temp_name)
        source = root / "source"
        wheelhouse = root / "wheelhouse"
        environment = root / "venv"
        off_repo = root / "off-repo"
        source.mkdir()
        wheelhouse.mkdir()
        off_repo.mkdir()
        shutil.copy2(PROJECT_ROOT / "pyproject.toml", source / "pyproject.toml")
        shutil.copy2(PROJECT_ROOT / "README.md", source / "README.md")
        shutil.copytree(
            PROJECT_ROOT / "src",
            source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
        )
        run([sys.executable, "-m", "pip", "wheel", "--no-deps", ".", "--wheel-dir", str(wheelhouse)], source)
        wheel = next(wheelhouse.glob("abalo_iching-*.whl"))
        run([sys.executable, "-m", "venv", str(environment)], root)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run([str(python), "-m", "pip", "install", str(wheel)], off_repo)
        probe = r'''
from datetime import datetime
from zoneinfo import ZoneInfo
from abalo_iching import MeihuaInput, cast_meihua
from abalo_iching.interpretation.enums import QuestionDomain
from abalo_iching.interpretation.fake_provider import FakeInterpretationProvider, build_conservative_fake_output
from abalo_iching.interpretation.knowledge import load_canonical_texts, select_knowledge
from abalo_iching.interpretation.models import InterpretationRequest
from abalo_iching.interpretation.prompt_builder import load_system_prompt
from abalo_iching.interpretation.service import InterpretationService
from abalo_iching.interpretation.synthesis import ConclusionSynthesizer

canonical = load_canonical_texts()
assert len(canonical) == 64 and sum(len(item.lines) for item in canonical) == 384
assert "你不是排盘程序" not in load_system_prompt()
assert "不是排盘程序" in load_system_prompt()
chart = cast_meihua(MeihuaInput(100, 27, 368, datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")), "Asia/Shanghai"))
request = InterpretationRequest(question_id="wheel", question_domain=QuestionDomain.CAREER, normalized_question="是否继续验证方案？", decision_goal="验证离仓运行", time_horizon="当前阶段", chart=chart)
synthesis = ConclusionSynthesizer().synthesize(chart, select_knowledge(chart))
output = build_conservative_fake_output(request, synthesis)
result = InterpretationService(FakeInterpretationProvider([output])).interpret(request)
assert result.not_a_live_openai_result is True
assert result.interpretation.program_content.conclusion_level is synthesis.conclusion_level
assert result.interpretation.program_content.timing.level.value == "STAGE_ONLY"
assert "timing" not in type(result.interpretation.ai_content).model_fields
assert "summary" not in result.interpretation.ai_content.model_dump_json()
assert result.interpretation.narrative_release.narrative_release_status.value == "UNVERIFIED"
assert result.should_charge is False and result.persist_as_formal_report_allowed is False
print("PHASE2_WHEEL_INSTALL_SMOKE=PASS canonical=64 lines=384 provider=FAKE")
'''
        run([str(python), "-X", "utf8", "-I", "-c", probe], off_repo)


if __name__ == "__main__":
    main()
