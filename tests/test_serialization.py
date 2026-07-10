import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.models import MeihuaInput
from abalo_iching.meihua.serialization import chart_from_dict, chart_from_json, chart_to_dict, chart_to_json


def _chart():
    return cast_meihua(
        MeihuaInput(
            100,
            27,
            368,
            datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
            "Asia/Shanghai",
            "serialize-case",
        )
    )


def test_json_serialization_round_trip() -> None:
    chart = _chart()
    payload = chart_to_json(chart)
    restored = chart_from_json(payload)
    assert chart_to_dict(restored) == chart_to_dict(chart)
    assert json.loads(payload)["timing"]["candidate_dates"] == []


def test_dict_round_trip() -> None:
    chart = _chart()
    assert chart_to_dict(chart_from_dict(chart_to_dict(chart))) == chart_to_dict(chart)


def test_engine_output_contains_no_api_key_field_or_secret_placeholder() -> None:
    serialized = chart_to_json(_chart()).lower()
    assert "api_key" not in serialized
    assert "openai" not in serialized
    assert "sk-" not in serialized


def test_only_calendar_adapter_imports_lunar_python() -> None:
    source_root = Path(__file__).parents[1] / "src" / "abalo_iching" / "meihua"
    importing_files = []
    for path in source_root.glob("*.py"):
        if "lunar_python" in path.read_text(encoding="utf-8"):
            importing_files.append(path.name)
    assert importing_files == ["calendar_provider.py"]


def test_chart_to_dict_requires_chart() -> None:
    try:
        chart_to_dict({})
    except TypeError as exc:
        assert "MeihuaChart" in str(exc)
    else:
        raise AssertionError("chart_to_dict accepted a non-chart")
