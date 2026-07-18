"""Cultural reading payload for the Sites product experience.

This module only exposes already-computed chart facts, frozen canonical text,
and versioned explanatory copy. It does not alter casting, infer dates, parse
the user's free-text question, or introduce new divination rules.
"""

from __future__ import annotations

from typing import TypedDict

from abalo_iching.interpretation.enums import ConclusionLevel
from abalo_iching.interpretation.knowledge import load_canonical_texts
from abalo_iching.interpretation.models import KnowledgeSelection, SynthesisResult
from abalo_iching.meihua.enums import (
    MOVING_LINE_STAGE_LABELS_ZH,
    RELATION_LABELS_ZH,
    SEASONAL_STRENGTH_LABELS_ZH,
    BodyUseRelation,
    SeasonalStrength,
)
from abalo_iching.meihua.models import Hexagram, MeihuaChart

CULTURAL_READING_VERSION = "SITES_CULTURAL_READING_V1"


class NumberPathItem(TypedDict):
    input_number: int
    role: str
    resolved_number: int
    result_name: str
    result_symbol: str
    explanation: str


class CanonicalHexagramItem(TypedDict):
    role: str
    king_wen_number: int
    name: str
    symbol: str
    canonical_text: str
    source_name: str
    source_reference: str
    reading_role: str


class MovingLineItem(TypedDict):
    position: int
    line_name: str
    canonical_text: str
    source_name: str
    source_reference: str
    stage: str


class TermExplanation(TypedDict):
    title: str
    current_value: str
    meaning: str
    current_effect: str


class ClassicCounsel(TypedDict):
    quote: str
    source: str


class CulturalReading(TypedDict):
    template_version: str
    number_path: list[NumberPathItem]
    hexagrams: list[CanonicalHexagramItem]
    moving_line: MovingLineItem
    terms: list[TermExplanation]
    classic_counsel: ClassicCounsel
    knowledge_notice: str | None


_RELATION_EFFECTS: dict[BodyUseRelation, str] = {
    BodyUseRelation.USE_GENERATES_BODY: "议题一方对体方形成生助；这份支持仍要在现实资源、回应或行动中得到确认。",
    BodyUseRelation.BODY_CONTROLS_USE: "体方具有主动管理空间，但能否掌握局面取决于真实能力、资源与执行。",
    BodyUseRelation.SAME_ELEMENT: "双方属于同类关系，互动可能增多；比和本身不等于必然有利，仍需看配合质量。",
    BodyUseRelation.BODY_GENERATES_USE: "体方正在向议题持续输出，需要留意投入是否得到相称回应。",
    BodyUseRelation.USE_CONTROLS_BODY: "议题一方对体方形成约束或压力，宜先识别压力来源并保护可用边界。",
}

_STRENGTH_MEANINGS: dict[SeasonalStrength, str] = {
    SeasonalStrength.PROSPEROUS: "当令而有力，承接与发挥能力相对充足。",
    SeasonalStrength.SUPPORTED: "得到时令扶助，具备一定承接空间。",
    SeasonalStrength.RESTING: "力量平缓，宜保留余地并观察后续反馈。",
    SeasonalStrength.CONFINED: "发挥受限，推进时更需要资源、节奏与边界。",
    SeasonalStrength.DEAD: "时令助力很弱，宜降低不可逆成本，不宜只凭意愿强推。",
}

_CLASSIC_COUNSEL: dict[ConclusionLevel, ClassicCounsel] = {
    ConclusionLevel.CLEARLY_FAVORABLE: {"quote": "天行健，君子以自强不息。", "source": "《周易·象传·乾》"},
    ConclusionLevel.CONDITIONALLY_FAVORABLE: {"quote": "穷则变，变则通，通则久。", "source": "《周易·系辞下》"},
    ConclusionLevel.MIXED_OR_UNSETTLED: {"quote": "君子藏器于身，待时而动。", "source": "《周易·系辞下》"},
    ConclusionLevel.CLEARLY_UNFAVORABLE: {"quote": "知止不殆，可以长久。", "source": "《道德经》第四十四章"},
    ConclusionLevel.INSUFFICIENT_EVIDENCE: {"quote": "知之为知之，不知为不知，是知也。", "source": "《论语·为政》"},
}


def _line_display_name(chart: MeihuaChart) -> str:
    yin_yang = "九" if chart.base_hexagram.lines_bottom_up[chart.moving_line - 1] else "六"
    if chart.moving_line == 1:
        return f"初{yin_yang}"
    if chart.moving_line == 6:
        return f"上{yin_yang}"
    return f"{yin_yang}{'一二三四五六'[chart.moving_line - 1]}"


def _canonical_hexagram(role: str, hexagram: Hexagram, reading_role: str) -> CanonicalHexagramItem:
    canonical = {item.king_wen_number: item for item in load_canonical_texts()}[hexagram.king_wen_number]
    return {
        "role": role,
        "king_wen_number": hexagram.king_wen_number,
        "name": hexagram.full_name_zh,
        "symbol": hexagram.unicode_symbol,
        "canonical_text": canonical.canonical_judgment_text,
        "source_name": canonical.source_name,
        "source_reference": canonical.source_reference,
        "reading_role": reading_role,
    }


def build_cultural_reading(
    chart: MeihuaChart,
    synthesis: SynthesisResult,
    knowledge: KnowledgeSelection,
) -> CulturalReading:
    """Build a transparent cultural explanation from authoritative chart facts."""
    initial_relation = chart.initial_body_use_relation
    changed_relation = chart.changed_body_use_relation
    body_strength = chart.season_context.body_strength
    stage = MOVING_LINE_STAGE_LABELS_ZH[chart.moving_line_stage]
    canonical_line = knowledge.canonical_line
    line_display_name = _line_display_name(chart)
    return {
        "template_version": CULTURAL_READING_VERSION,
        "number_path": [
            {
                "input_number": chart.input.first_number,
                "role": "上卦",
                "resolved_number": chart.upper_trigram.number,
                "result_name": chart.upper_trigram.name_zh,
                "result_symbol": chart.upper_trigram.symbol,
                "explanation": "第一数依冻结规则取八数之余，定为本卦上卦。",
            },
            {
                "input_number": chart.input.second_number,
                "role": "下卦",
                "resolved_number": chart.lower_trigram.number,
                "result_name": chart.lower_trigram.name_zh,
                "result_symbol": chart.lower_trigram.symbol,
                "explanation": "第二数依冻结规则取八数之余，定为本卦下卦。",
            },
            {
                "input_number": chart.input.third_number,
                "role": "动爻",
                "resolved_number": chart.moving_line,
                "result_name": line_display_name,
                "result_symbol": chart.base_hexagram.unicode_symbol,
                "explanation": "第三数依冻结规则取六数之余，确定本卦哪一爻发生变化。",
            },
        ],
        "hexagrams": [
            _canonical_hexagram("本卦", chart.base_hexagram, "呈现起卦时的主要结构，是整份解读的出发点。"),
            _canonical_hexagram("互卦", chart.mutual_hexagram, "由本卦中间四爻相参而成，辅助观察事情内部如何展开。"),
            _canonical_hexagram("变卦", chart.changed_hexagram, "由动爻变化后形成，用来比较结构前后如何改变。"),
        ],
        "moving_line": {
            "position": chart.moving_line,
            "line_name": line_display_name,
            "canonical_text": canonical_line.canonical_line_text,
            "source_name": canonical_line.source_name,
            "source_reference": canonical_line.source_reference,
            "stage": stage,
        },
        "terms": [
            {
                "title": "动爻",
                "current_value": f"{line_display_name} · {stage}",
                "meaning": "动爻是本卦中发生变化的一爻；它决定变卦，也标示当前变化落在事情的哪个阶段。",
                "current_effect": f"本次动在{line_display_name}，规则阶段为{stage}。它只提供阶段线索，不生成具体日期。",
            },
            {
                "title": "体用关系",
                "current_value": f"起始{RELATION_LABELS_ZH[initial_relation]} → 变化后{RELATION_LABELS_ZH[changed_relation]}",
                "meaning": "体代表承接事情的主体，用代表所问议题或外部条件；体用关系用来比较双方的生、克与同类互动。",
                "current_effect": f"起始：{_RELATION_EFFECTS[initial_relation]} 变化后：{_RELATION_EFFECTS[changed_relation]}",
            },
            {
                "title": "旺衰",
                "current_value": f"体卦{SEASONAL_STRENGTH_LABELS_ZH[body_strength]}",
                "meaning": "旺衰表示五行在当前节气中的承接强弱，只修正关系力度，不会把原来的关系方向翻转。",
                "current_effect": _STRENGTH_MEANINGS[body_strength],
            },
        ],
        "classic_counsel": dict(_CLASSIC_COUNSEL[synthesis.conclusion_level]),
        "knowledge_notice": knowledge.unreviewed_notice,
    }
