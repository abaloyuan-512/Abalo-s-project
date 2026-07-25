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
from abalo_iching.meihua.enums import BodyUseRelation, MovingLineStage, SeasonalStrength
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
    MovingLineStage.GERMINATION: "变化刚露出苗头，许多条件还没有定形。先看清最早出现的信号，再决定要不要增加投入。",
    MovingLineStage.EARLY_FORMATION: "事情正在成形，方向已经隐约可见，但仍来得及调整。先把角色、说法和第一步讲清楚。",
    MovingLineStage.INTERNAL_THRESHOLD: "变化发生在事情内部最容易卡住的位置，原来的安排可能已经不够用了。先处理内部分歧、资源分配和承诺边界，再向外推进。",
    MovingLineStage.EXTERNAL_TURNING_POINT: "变化开始从内部显到外部，可能带来公开选择、关系转折或行动升级。此时要认真看对方和现实给出的回应。",
    MovingLineStage.CORE_DECISION: "这条爻处在整卦很关键的位置，常与拍板、分配资源和承担责任有关。后面能不能推进，很大程度取决于决定是否清楚、作决定的人能否负责。",
    MovingLineStage.CLOSING_OR_EXCESS: "事情已经走到收尾或容易做过头的位置。重点不再是继续加码，而是知道何时停、怎样交接、哪些成果值得保留。",
}

_PLAIN_STAGE_LABELS: dict[MovingLineStage, str] = {
    MovingLineStage.GERMINATION: "刚有苗头",
    MovingLineStage.EARLY_FORMATION: "正在成形",
    MovingLineStage.INTERNAL_THRESHOLD: "内部调整的关口",
    MovingLineStage.EXTERNAL_TURNING_POINT: "由内转外的关口",
    MovingLineStage.CORE_DECISION: "关键决定的位置",
    MovingLineStage.CLOSING_OR_EXCESS: "收尾或容易过度的位置",
}

_PLAIN_RELATION_LABELS: dict[BodyUseRelation, str] = {
    BodyUseRelation.USE_GENERATES_BODY: "用生体（外部条件在帮助你）",
    BodyUseRelation.BODY_CONTROLS_USE: "体克用（你仍有主动调整空间）",
    BodyUseRelation.SAME_ELEMENT: "比和（双方五行相同，较容易同频）",
    BodyUseRelation.BODY_GENERATES_USE: "体生用（你正在为这件事付出）",
    BodyUseRelation.USE_CONTROLS_BODY: "用克体（外部条件对你形成压力）",
}

_PLAIN_STRENGTH_LABELS: dict[SeasonalStrength, str] = {
    SeasonalStrength.PROSPEROUS: "旺（眼下力量充足）",
    SeasonalStrength.SUPPORTED: "相（眼下能得到助力）",
    SeasonalStrength.RESTING: "休（眼下平稳，但余力有限）",
    SeasonalStrength.CONFINED: "囚（眼下受到限制）",
    SeasonalStrength.DEAD: "死（眼下助力很弱）",
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
    stage = _PLAIN_STAGE_LABELS[chart.moving_line_stage]
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
            _canonical_hexagram("本卦", chart.base_hexagram, "由上卦和下卦上下相叠而成，表示这件事眼下最主要的样子。"),
            _canonical_hexagram("互卦", chart.mutual_hexagram, "从本卦中间四爻重新组合而来，帮助你看事情内部怎样发展。"),
            _canonical_hexagram("变卦", chart.changed_hexagram, "把动爻由阳变阴或由阴变阳后得到，表示局面发生变化后的方向。"),
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
                "title": "动爻（变化发生在哪里）",
                "current_value": f"{line_display_name} · {stage}",
                "meaning": "一卦共有六条爻。动爻就是其中发生变化的那一条；它一变，本卦便随之成为变卦。",
                "current_effect": f"这次变化落在{line_display_name}，也就是{stage}。{_STAGE_EFFECTS[chart.moving_line_stage]}",
            },
            {
                "title": "体用关系（你与这件事的关系）",
                "current_value": f"开始时：{_PLAIN_RELATION_LABELS[initial_relation]} → 变化后：{_PLAIN_RELATION_LABELS[changed_relation]}",
                "meaning": "“体”可以理解为你和你能调动的力量；“用”是所问的事情、对方或外部条件。两者的关系，帮助我们看谁在支持谁、谁在消耗谁。",
                "current_effect": f"开始时，{_RELATION_EFFECTS[initial_relation]} 变化后，{_RELATION_EFFECTS[changed_relation]}",
            },
            {
                "title": "旺衰（眼下有多少余力）",
                "current_value": f"体卦为{_PLAIN_STRENGTH_LABELS[body_strength]}",
                "meaning": "旺衰不是给事情判好坏，而是看你眼下有多少余力。余力足，可以多承担一些；余力弱，就更要借助外部支持并守住边界。",
                "current_effect": _STRENGTH_MEANINGS[body_strength],
            },
        ],
        "classic_counsel": dict(_CLASSIC_COUNSEL[synthesis.conclusion_level]),
        "knowledge_notice": knowledge.unreviewed_notice,
    }
