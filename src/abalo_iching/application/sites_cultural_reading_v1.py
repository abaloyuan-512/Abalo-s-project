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
    MovingLineStage,
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
    plain_note: str
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
    BodyUseRelation.USE_GENERATES_BODY: "这件事或外部条件正在给你提供支持。支持是否真实，要看资源、回应和后续行动是否确实出现。",
    BodyUseRelation.BODY_CONTROLS_USE: "你对这件事仍有一定主动权，可以安排节奏、调整投入或设定边界；但主动权要靠真实能力、资源和持续执行才能兑现。",
    BodyUseRelation.SAME_ELEMENT: "你与这件事目前较为同频，互动和协作的机会可能增加；是否真正有利，仍取决于配合质量和实际结果。",
    BodyUseRelation.BODY_GENERATES_USE: "你正在持续为这件事投入时间、精力或资源。需要观察这些付出是否换来了相称的回应，避免只靠单方面支撑。",
    BodyUseRelation.USE_CONTROLS_BODY: "这件事或外部条件正在对你形成较强约束。宜先找出压力来自哪里，并保护时间、资源和可承受的边界。",
}

_STRENGTH_MEANINGS: dict[SeasonalStrength, str] = {
    SeasonalStrength.PROSPEROUS: "当前时令对你所代表的力量支持较足，通常更有余力承接任务和推动变化；仍应把优势落实为具体行动。",
    SeasonalStrength.SUPPORTED: "当前时令能提供一定帮助，你有承接和调整的空间；推进前仍需确认关键资源是否到位。",
    SeasonalStrength.RESTING: "当前力量较为平稳，但余量有限。适合保留调整空间，用后续反馈决定是否增加投入。",
    SeasonalStrength.CONFINED: "当前可动用的力量受到限制。推进时更依赖外部资源、清楚节奏和可守住的边界，不宜同时承担过多。",
    SeasonalStrength.DEAD: "当前时令提供的助力很弱，单靠意愿容易造成消耗。宜先降低不可逆成本，补足资源后再判断是否继续。",
}

_STAGE_EFFECTS: dict[MovingLineStage, str] = {
    MovingLineStage.GERMINATION: "变化刚刚出现，许多条件还没有定形。此时最重要的是辨认最初信号，先用小动作验证，不必急着扩大投入。",
    MovingLineStage.EARLY_FORMATION: "变化正在形成，方向已有轮廓但仍可调整。宜把规则、角色和第一步说清，避免含混的开始变成后续负担。",
    MovingLineStage.INTERNAL_THRESHOLD: "变化已经触及内部临界点，原有安排开始难以维持。宜先处理内部矛盾、资源分配和承诺边界，再向外推进。",
    MovingLineStage.EXTERNAL_TURNING_POINT: "变化已经从内部走向外部，容易出现公开选择、关系转折或行动升级。宜观察真实反馈，并为不同回应预留退路。",
    MovingLineStage.CORE_DECISION: "这一爻处在全卦较高而居中的关键位置，常对应主导判断、资源调配或重要拍板。本次变化落在这里，说明后续能否推进，很大程度取决于决定是否明确、负责者能否承担后果；宜先把决定权、条件和责任说清，再作承诺。",
    MovingLineStage.CLOSING_OR_EXCESS: "变化已经来到收束或过度的位置。此时重点不是继续加码，而是判断何时止步、如何交接，以及哪些成果应当保留。",
}

_CANONICAL_GLOSSARY: tuple[tuple[str, str], ...] = (
    ("利涉大川", "适合渡过大河，常用来比喻承担重大的行动或难关"),
    ("利君子貞", "有利于君子守正而行"),
    ("利君子贞", "有利于君子守正而行"),
    ("利見大人", "适宜求见有德有位、能够担当的人"),
    ("利见大人", "适宜求见有德有位、能够担当的人"),
    ("不利有攸往", "不宜贸然前往或展开行动"),
    ("利有攸往", "适宜有所前往或采取行动"),
    ("有攸往", "有所前往或采取行动"),
    ("元亨", "大为通达"),
    ("小亨", "小事可以通达"),
    ("貞吉", "守正则吉"),
    ("贞吉", "守正则吉"),
    ("利貞", "适宜守正"),
    ("利贞", "适宜守正"),
    ("悔亡", "悔恨消退"),
    ("无不利", "没有不利"),
    ("無不利", "没有不利"),
    ("无咎", "没有灾咎"),
    ("無咎", "没有灾咎"),
    ("勿用", "暂不施行"),
    ("征凶", "贸然前往会有不利"),
    ("亨", "通达"),
    ("吉", "吉善、顺遂"),
    ("凶", "不利"),
    ("吝", "有所遗憾或艰难"),
)

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
        "plain_note": _literal_judgment_note(canonical.canonical_judgment_text),
        "source_name": canonical.source_name,
        "source_reference": canonical.source_reference,
        "reading_role": reading_role,
    }


def _literal_judgment_note(canonical_text: str) -> str:
    """Return versioned lexical notes without applying the text to the user's question."""
    notes: list[str] = []
    matched_text = canonical_text
    for phrase, explanation in _CANONICAL_GLOSSARY:
        if phrase in matched_text:
            notes.append(f"{phrase}：{explanation}")
            matched_text = matched_text.replace(phrase, "")
    if not notes:
        return "字义小注：这段原文的逐句释义仍在人工校订，本页暂不把未经核对的解释当作正式内容。"
    return f"字义小注：{'；'.join(notes)}。"


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
                "explanation": "第一数按照三数起卦法取八数之余，定为本卦上卦。",
            },
            {
                "input_number": chart.input.second_number,
                "role": "下卦",
                "resolved_number": chart.lower_trigram.number,
                "result_name": chart.lower_trigram.name_zh,
                "result_symbol": chart.lower_trigram.symbol,
                "explanation": "第二数按照三数起卦法取八数之余，定为本卦下卦。",
            },
            {
                "input_number": chart.input.third_number,
                "role": "动爻",
                "resolved_number": chart.moving_line,
                "result_name": line_display_name,
                "result_symbol": chart.base_hexagram.unicode_symbol,
                "explanation": "第三数按照三数起卦法取六数之余，确定本卦哪一爻发生变化。",
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
                "current_effect": f"本次动在{line_display_name}，对应{stage}。{_STAGE_EFFECTS[chart.moving_line_stage]}",
            },
            {
                "title": "体用关系",
                "current_value": f"起始{RELATION_LABELS_ZH[initial_relation]} → 变化后{RELATION_LABELS_ZH[changed_relation]}",
                "meaning": "可以把“体”理解为你和你目前能调用的力量，把“用”理解为所问的事情、对方或外部条件。体用关系用来观察两边是在互相支持、彼此牵制，还是处于相近状态。",
                "current_effect": f"起始：{_RELATION_EFFECTS[initial_relation]} 变化后：{_RELATION_EFFECTS[changed_relation]}",
            },
            {
                "title": "旺衰",
                "current_value": f"体卦{SEASONAL_STRENGTH_LABELS_ZH[body_strength]}",
                "meaning": "旺衰用来说明你所代表的力量在当前时令中是充足、平稳还是受限。它影响你能不能承受和落实眼前的变化，但不会把原有关系完全颠倒。",
                "current_effect": _STRENGTH_MEANINGS[body_strength],
            },
        ],
        "classic_counsel": dict(_CLASSIC_COUNSEL[synthesis.conclusion_level]),
        "knowledge_notice": knowledge.unreviewed_notice,
    }
