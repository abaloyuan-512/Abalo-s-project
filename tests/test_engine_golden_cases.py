import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.enums import EvidenceType, TimingLevel
from abalo_iching.meihua.models import MeihuaInput

FIXTURE = Path(__file__).parent / "fixtures" / "golden_cases_v1.json"
CAST_AT = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


def _cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def test_fixture_has_four_fixed_plus_sixteen_manual_cases() -> None:
    cases = _cases()
    assert len(cases) == 20
    assert [item["id"] for item in cases[:4]] == ["fixed-01", "fixed-02", "fixed-03", "fixed-04"]
    assert len([item for item in cases if item["id"].startswith("manual-")]) == 16
    assert {item["expected"]["moving_line"] for item in cases} == set(range(1, 7))
    assert {item["expected"]["initial_relation"] for item in cases} == {
        "USE_GENERATES_BODY",
        "BODY_CONTROLS_USE",
        "SAME_ELEMENT",
        "BODY_GENERATES_USE",
        "USE_CONTROLS_BODY",
    }


def test_all_manual_golden_cases() -> None:
    for case in _cases():
        first, second, third = case["input"]
        expected = case["expected"]
        chart = cast_meihua(
            MeihuaInput(first, second, third, CAST_AT, "Asia/Shanghai", question_id=case["id"])
        )
        assert chart.upper_trigram.name_zh == expected["upper"], case["id"]
        assert chart.lower_trigram.name_zh == expected["lower"], case["id"]
        assert chart.moving_line == expected["moving_line"], case["id"]
        assert [chart.base_hexagram.king_wen_number, chart.base_hexagram.full_name_zh] == expected["base"], case["id"]
        assert [
            chart.mutual_hexagram.upper_trigram.name_zh,
            chart.mutual_hexagram.lower_trigram.name_zh,
            chart.mutual_hexagram.king_wen_number,
            chart.mutual_hexagram.full_name_zh,
        ] == expected["mutual"], case["id"]
        assert [
            chart.changed_hexagram.upper_trigram.name_zh,
            chart.changed_hexagram.lower_trigram.name_zh,
            chart.changed_hexagram.king_wen_number,
            chart.changed_hexagram.full_name_zh,
        ] == expected["changed"], case["id"]
        assert chart.body_trigram.name_zh == expected["body"], case["id"]
        assert chart.initial_use_trigram.name_zh == expected["initial_use"], case["id"]
        assert chart.changed_use_trigram.name_zh == expected["changed_use"], case["id"]
        assert chart.initial_body_use_relation.value == expected["initial_relation"], case["id"]
        assert chart.changed_body_use_relation.value == expected["changed_relation"], case["id"]


def test_chart_contains_fact_evidence_versions_and_closed_timing() -> None:
    chart = cast_meihua(MeihuaInput(100, 27, 368, CAST_AT, "Asia/Shanghai"))
    assert {item.evidence_type for item in chart.evidence} == set(EvidenceType)
    assert len({item.evidence_id for item in chart.evidence}) == len(chart.evidence) == 9
    assert chart.timing.exact_date_feature_enabled is False
    assert chart.timing.level is TimingLevel.STAGE_ONLY
    assert chart.timing.candidate_dates == ()
    assert chart.versions.rule_version == "MEIHUA_RULE_SPEC_V1"
    assert chart.versions.calendar_provider == "lunar_python/1.4.8"
