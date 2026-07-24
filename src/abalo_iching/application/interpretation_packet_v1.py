"""Read-only interpretation packet for the personalized owner preview.

The packet exposes deterministic chart facts and canonical source text to the
language model.  It never casts a chart, changes a rule, or turns an
interpretive hypothesis into a chart fact.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from abalo_iching.interpretation.knowledge import load_canonical_texts
from abalo_iching.meihua.enums import BodyUseRelation, MovingLineStage, SeasonalStrength
from abalo_iching.meihua.models import Hexagram, MeihuaChart
from abalo_iching.personalization_gate2.models import (
    ChartEvidence,
    KnowledgeReviewStatus,
    StrictModel,
)


INTERPRETATION_PACKET_VERSION = "SITES_INTERPRETATION_PACKET_V1"


class InterpretationPacketSourceV1(StrictModel):
    source_id: str
    source_version: str
    source_name: str
    source_reference: str


class InterpretationPacketHexagramV1(StrictModel):
    evidence_ref: str = Field(pattern=r"^EV\d{2}$")
    role: Literal["BASE", "MUTUAL", "CHANGED"]
    king_wen_number: int = Field(ge=1, le=64)
    name: str
    symbol: str
    structural_role: str
    canonical_judgment_text: str
    source_id: str


class InterpretationPacketMovingLineV1(StrictModel):
    evidence_ref: str = Field(pattern=r"^EV\d{2}$")
    position: int = Field(ge=1, le=6)
    line_name: str
    stage: MovingLineStage
    canonical_line_text: str
    source_id: str


class InterpretationPacketBodyUseV1(StrictModel):
    body_trigram: str
    initial_use_trigram: str
    changed_use_trigram: str
    initial_relation: BodyUseRelation
    changed_relation: BodyUseRelation
    body_strength: SeasonalStrength
    initial_relation_evidence_ref: Literal["EV02"] = "EV02"
    changed_relation_evidence_ref: Literal["EV03"] = "EV03"
    body_strength_evidence_ref: Literal["EV06"] = "EV06"


class InterpretationPacketV1(StrictModel):
    packet_version: Literal[INTERPRETATION_PACKET_VERSION]
    epistemic_boundary: Literal[
        "PACKET_ITEMS_ARE_CHART_OR_CANONICAL_FACTS;_ANY_APPLICATION_TO_REALITY_IS_AN_INTERPRETATION_HYPOTHESIS"
    ]
    hexagrams: list[InterpretationPacketHexagramV1] = Field(min_length=3, max_length=3)
    moving_line: InterpretationPacketMovingLineV1
    body_use: InterpretationPacketBodyUseV1
    sources: list[InterpretationPacketSourceV1] = Field(min_length=2, max_length=2)


_ROLE_LABELS: dict[str, tuple[str, str]] = {
    "BASE": ("本卦", "呈现当前局面的基础结构，不等于现实结局。"),
    "MUTUAL": ("互卦", "呈现本卦内部的结构变化，只作为辅助观察。"),
    "CHANGED": ("变卦", "呈现动爻改变后的结构方向，不代表未来必然发生。"),
}


def _line_display_name(chart: MeihuaChart) -> str:
    yin_yang = "九" if chart.base_hexagram.lines_bottom_up[chart.moving_line - 1] else "六"
    if chart.moving_line == 1:
        return f"初{yin_yang}"
    if chart.moving_line == 6:
        return f"上{yin_yang}"
    return f"{yin_yang}{'一二三四五六'[chart.moving_line - 1]}"


def _packet_hexagram(
    hexagram: Hexagram,
    *,
    role: Literal["BASE", "MUTUAL", "CHANGED"],
    evidence_ref: str,
    canonical_by_number: dict[int, object],
) -> InterpretationPacketHexagramV1:
    canonical = canonical_by_number[hexagram.king_wen_number]
    role_label, structural_role = _ROLE_LABELS[role]
    return InterpretationPacketHexagramV1(
        evidence_ref=evidence_ref,
        role=role,
        king_wen_number=hexagram.king_wen_number,
        name=hexagram.full_name_zh,
        symbol=hexagram.unicode_symbol,
        structural_role=f"{role_label}：{structural_role}",
        canonical_judgment_text=canonical.canonical_judgment_text,  # type: ignore[attr-defined]
        source_id=f"CANONICAL-H-{hexagram.king_wen_number}",
    )


def build_interpretation_packet_v1(chart: MeihuaChart) -> InterpretationPacketV1:
    """Build a source-versioned packet from an already-cast chart."""
    canonical_records = load_canonical_texts()
    canonical_by_number = {item.king_wen_number: item for item in canonical_records}
    base_canonical = canonical_by_number[chart.base_hexagram.king_wen_number]
    canonical_line = base_canonical.lines[chart.moving_line - 1]
    return InterpretationPacketV1(
        packet_version=INTERPRETATION_PACKET_VERSION,
        epistemic_boundary=(
            "PACKET_ITEMS_ARE_CHART_OR_CANONICAL_FACTS;_ANY_APPLICATION_TO_REALITY_IS_AN_INTERPRETATION_HYPOTHESIS"
        ),
        hexagrams=[
            _packet_hexagram(
                chart.base_hexagram,
                role="BASE",
                evidence_ref="EV10",
                canonical_by_number=canonical_by_number,
            ),
            _packet_hexagram(
                chart.mutual_hexagram,
                role="MUTUAL",
                evidence_ref="EV11",
                canonical_by_number=canonical_by_number,
            ),
            _packet_hexagram(
                chart.changed_hexagram,
                role="CHANGED",
                evidence_ref="EV12",
                canonical_by_number=canonical_by_number,
            ),
        ],
        moving_line=InterpretationPacketMovingLineV1(
            evidence_ref="EV13",
            position=chart.moving_line,
            line_name=_line_display_name(chart),
            stage=chart.moving_line_stage,
            canonical_line_text=canonical_line.canonical_line_text,
            source_id=f"CANONICAL-L-{chart.base_hexagram.king_wen_number}-{chart.moving_line}",
        ),
        body_use=InterpretationPacketBodyUseV1(
            body_trigram=chart.body_trigram.name_zh,
            initial_use_trigram=chart.initial_use_trigram.name_zh,
            changed_use_trigram=chart.changed_use_trigram.name_zh,
            initial_relation=chart.initial_body_use_relation,
            changed_relation=chart.changed_body_use_relation,
            body_strength=chart.season_context.body_strength,
        ),
        sources=[
            InterpretationPacketSourceV1(
                source_id="DETERMINISTIC-CHART",
                source_version=chart.versions.rule_version,
                source_name="观象梅花确定性规则",
                source_reference=chart.versions.engine_version,
            ),
            InterpretationPacketSourceV1(
                source_id="CANONICAL-TEXTS",
                source_version=base_canonical.canonical_data_version,
                source_name=base_canonical.source_name,
                source_reference=base_canonical.source_reference,
            ),
        ],
    )


def interpretation_packet_evidence_v1(packet: InterpretationPacketV1) -> list[ChartEvidence]:
    """Expose packet facts through the existing EVxx trace contract."""
    evidence = [
        ChartEvidence(
            ref=item.evidence_ref,
            canonical_evidence_id=f"{item.source_id}:{packet.packet_version}",
            text=(
                f"{item.structural_role} 当前为第{item.king_wen_number}卦{item.name}，"
                f"卦辞原文：{item.canonical_judgment_text}"
            ),
            knowledge_review_status=KnowledgeReviewStatus.CANONICAL_ONLY,
        )
        for item in packet.hexagrams
    ]
    evidence.append(
        ChartEvidence(
            ref=packet.moving_line.evidence_ref,
            canonical_evidence_id=(
                f"{packet.moving_line.source_id}:{packet.sources[1].source_version}"
            ),
            text=(
                f"动爻为{packet.moving_line.line_name}，位置阶段为"
                f"{packet.moving_line.stage.value}；爻辞原文："
                f"{packet.moving_line.canonical_line_text}"
            ),
            knowledge_review_status=KnowledgeReviewStatus.CANONICAL_ONLY,
        )
    )
    return evidence
