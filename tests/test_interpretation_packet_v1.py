from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from abalo_iching.application.interpretation_packet_v1 import (
    INTERPRETATION_PACKET_VERSION,
    build_interpretation_packet_v1,
    interpretation_packet_evidence_v1,
)
from abalo_iching.meihua import MeihuaInput, cast_meihua, chart_to_dict


CAST_AT = datetime(2026, 7, 24, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_packet_exposes_versioned_chart_and_canonical_facts_without_mutating_chart():
    chart = cast_meihua(MeihuaInput(6, 3, 4, CAST_AT, "Asia/Shanghai", "packet-test"))
    before = chart_to_dict(chart)

    packet = build_interpretation_packet_v1(chart)

    assert chart_to_dict(chart) == before
    assert packet.packet_version == INTERPRETATION_PACKET_VERSION
    assert [item.role for item in packet.hexagrams] == ["BASE", "MUTUAL", "CHANGED"]
    assert [item.name for item in packet.hexagrams] == [
        chart.base_hexagram.full_name_zh,
        chart.mutual_hexagram.full_name_zh,
        chart.changed_hexagram.full_name_zh,
    ]
    assert packet.moving_line.position == chart.moving_line
    assert packet.moving_line.canonical_line_text
    assert packet.body_use.initial_relation == chart.initial_body_use_relation
    assert packet.body_use.changed_relation == chart.changed_body_use_relation
    assert packet.sources[0].source_version == chart.versions.rule_version
    assert packet.sources[1].source_version == "MEIHUA_CANONICAL_TEXTS_V1"


def test_packet_evidence_uses_reserved_refs_and_canonical_only_status():
    chart = cast_meihua(MeihuaInput(1, 1, 1, CAST_AT, "Asia/Shanghai", "packet-evidence"))
    packet = build_interpretation_packet_v1(chart)

    evidence = interpretation_packet_evidence_v1(packet)

    assert [item.ref for item in evidence] == ["EV10", "EV11", "EV12", "EV13"]
    assert all(item.knowledge_review_status.value == "CANONICAL_ONLY" for item in evidence)
    assert chart.base_hexagram.full_name_zh in evidence[0].text
    assert packet.moving_line.canonical_line_text in evidence[-1].text
