"""Closed enumerations used by the Phase 1 deterministic engine."""

from enum import Enum


class Element(str, Enum):
    WOOD = "木"
    FIRE = "火"
    EARTH = "土"
    METAL = "金"
    WATER = "水"


class BodyUseRelation(str, Enum):
    USE_GENERATES_BODY = "USE_GENERATES_BODY"
    BODY_CONTROLS_USE = "BODY_CONTROLS_USE"
    SAME_ELEMENT = "SAME_ELEMENT"
    BODY_GENERATES_USE = "BODY_GENERATES_USE"
    USE_CONTROLS_BODY = "USE_CONTROLS_BODY"


class MovingLineStage(str, Enum):
    GERMINATION = "GERMINATION"
    EARLY_FORMATION = "EARLY_FORMATION"
    INTERNAL_THRESHOLD = "INTERNAL_THRESHOLD"
    EXTERNAL_TURNING_POINT = "EXTERNAL_TURNING_POINT"
    CORE_DECISION = "CORE_DECISION"
    CLOSING_OR_EXCESS = "CLOSING_OR_EXCESS"


class SeasonalStrength(str, Enum):
    PROSPEROUS = "PROSPEROUS"
    SUPPORTED = "SUPPORTED"
    RESTING = "RESTING"
    CONFINED = "CONFINED"
    DEAD = "DEAD"


class EvidenceType(str, Enum):
    BASE_HEXAGRAM = "BASE_HEXAGRAM"
    INITIAL_BODY_USE_RELATION = "INITIAL_BODY_USE_RELATION"
    CHANGED_BODY_USE_RELATION = "CHANGED_BODY_USE_RELATION"
    MUTUAL_LOWER_RELATION = "MUTUAL_LOWER_RELATION"
    MUTUAL_UPPER_RELATION = "MUTUAL_UPPER_RELATION"
    BODY_SEASONAL_STRENGTH = "BODY_SEASONAL_STRENGTH"
    INITIAL_USE_SEASONAL_STRENGTH = "INITIAL_USE_SEASONAL_STRENGTH"
    CHANGED_USE_SEASONAL_STRENGTH = "CHANGED_USE_SEASONAL_STRENGTH"
    MOVING_LINE_STAGE = "MOVING_LINE_STAGE"


class EvidencePolarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class TimingLevel(str, Enum):
    STAGE_ONLY = "STAGE_ONLY"
    TIMING_UNAVAILABLE = "TIMING_UNAVAILABLE"


RELATION_LABELS_ZH = {
    BodyUseRelation.USE_GENERATES_BODY: "用生体",
    BodyUseRelation.BODY_CONTROLS_USE: "体克用",
    BodyUseRelation.SAME_ELEMENT: "比和",
    BodyUseRelation.BODY_GENERATES_USE: "体生用",
    BodyUseRelation.USE_CONTROLS_BODY: "用克体",
}

MOVING_LINE_STAGE_LABELS_ZH = {
    MovingLineStage.GERMINATION: "萌芽阶段",
    MovingLineStage.EARLY_FORMATION: "初步成形",
    MovingLineStage.INTERNAL_THRESHOLD: "内部临界",
    MovingLineStage.EXTERNAL_TURNING_POINT: "外部转折",
    MovingLineStage.CORE_DECISION: "核心决断",
    MovingLineStage.CLOSING_OR_EXCESS: "末端或过度",
}

SEASONAL_STRENGTH_LABELS_ZH = {
    SeasonalStrength.PROSPEROUS: "旺",
    SeasonalStrength.SUPPORTED: "相",
    SeasonalStrength.RESTING: "休",
    SeasonalStrength.CONFINED: "囚",
    SeasonalStrength.DEAD: "死",
}

SEASONAL_STRENGTH_RANK = {
    SeasonalStrength.PROSPEROUS: 2,
    SeasonalStrength.SUPPORTED: 1,
    SeasonalStrength.RESTING: 0,
    SeasonalStrength.CONFINED: -1,
    SeasonalStrength.DEAD: -2,
}
