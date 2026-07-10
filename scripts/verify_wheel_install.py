"""Build and install a normal wheel in isolation, then run the engine off-repo."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
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
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {command}")
    return result


def _copy_build_source(destination: Path) -> None:
    shutil.copy2(PROJECT_ROOT / "pyproject.toml", destination / "pyproject.toml")
    shutil.copy2(PROJECT_ROOT / "README.md", destination / "README.md")
    shutil.copytree(
        PROJECT_ROOT / "src",
        destination / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="abalo-wheel-smoke-") as temp_name:
        temp_root = Path(temp_name)
        source = temp_root / "source"
        wheelhouse = temp_root / "wheelhouse"
        environment = temp_root / "venv"
        probe_cwd = temp_root / "off-repo-cwd"
        source.mkdir()
        wheelhouse.mkdir()
        probe_cwd.mkdir()
        _copy_build_source(source)

        _run([sys.executable, "-m", "pip", "wheel", "--no-deps", ".", "--wheel-dir", str(wheelhouse)], cwd=source)
        wheels = list(wheelhouse.glob("abalo_iching-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected exactly one wheel, found: {wheels}")

        _run([sys.executable, "-m", "venv", str(environment)], cwd=temp_root)
        venv_python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        _run([str(venv_python), "-m", "pip", "install", str(wheels[0])], cwd=probe_cwd)

        probe = """
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import abalo_iching
from abalo_iching import MeihuaInput, cast_meihua
from abalo_iching.meihua.serialization import chart_to_json

chart = cast_meihua(MeihuaInput(100, 27, 368, datetime(2026, 7, 10, 12, tzinfo=ZoneInfo('Asia/Shanghai')), 'Asia/Shanghai'))
payload = chart_to_json(chart)
data = json.loads(payload)
result = {
    'module_file': abalo_iching.__file__,
    'base_hexagram_number': chart.base_hexagram.king_wen_number,
    'base_hexagram_name': chart.base_hexagram.full_name_zh,
    'exact_date_feature_enabled': data['timing']['exact_date_feature_enabled'],
    'candidate_dates': data['timing']['candidate_dates'],
    'json_has_api_key': 'api_key' in payload.lower() or 'sk-' in payload.lower(),
    'json_has_project_path': str(PROJECT_ROOT_PLACEHOLDER) in payload,
}
print(json.dumps(result, ensure_ascii=False))
""".replace("PROJECT_ROOT_PLACEHOLDER", repr(str(PROJECT_ROOT)))
        result = _run([str(venv_python), "-X", "utf8", "-I", "-c", probe], cwd=probe_cwd)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        expected = {
            "base_hexagram_number": 55,
            "base_hexagram_name": "雷火丰",
            "exact_date_feature_enabled": False,
            "candidate_dates": [],
            "json_has_api_key": False,
            "json_has_project_path": False,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(f"Wheel smoke mismatch for {key}: {payload.get(key)!r} != {value!r}")
        if str(PROJECT_ROOT) in payload["module_file"]:
            raise RuntimeError("Probe imported from repository instead of isolated wheel")
        print("WHEEL_INSTALL_SMOKE=PASS")


if __name__ == "__main__":
    main()
