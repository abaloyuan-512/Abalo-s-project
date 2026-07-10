"""Generate fact-only, versioned evidence records."""

from .enums import (
    MOVING_LINE_STAGE_LABELS_ZH,
    RELATION_LABELS_ZH,
    SEASONAL_STRENGTH_LABELS_ZH,
    BodyUseRelation,
    EvidencePolarity,
    EvidenceStrength,
    EvidenceType,
    MovingLineStage,
    SeasonalStrength,
)
from .models import BodyUseAssignment, Evidence, Hexagram, SeasonContext

_EVIDENCE_VERSION = "MEIHUA_EVIDENCE_V1"

RULE_ID_BASE_HEXAGRAM = "MEIHUA-V1-RULE-BASE-HEXAGRAM"
RULE_ID_BODY_USE = "MEIHUA-V1-RULE-BODY-USE"
RULE_ID_SEASONAL_STRENGTH = "MEIHUA-V1-RULE-SEASONAL-STRENGTH"
RULE_ID_MOVING_LINE_STAGE = "MEIHUA-V1-RULE-MOVING-LINE-STAGE"

EVIDENCE_RULE_IDS = {
    EvidenceType.BASE_HEXAGRAM: RULE_ID_BASE_HEXAGRAM,
    EvidenceType.INITIAL_BODY_USE_RELATION: RULE_ID_BODY_USE,
    EvidenceType.CHANGED_BODY_USE_RELATION: RULE_ID_BODY_USE,
    EvidenceType.MUTUAL_LOWER_RELATION: RULE_ID_BODY_USE,
    EvidenceType.MUTUAL_UPPER_RELATION: RULE_ID_BODY_USE,
    EvidenceType.BODY_SEASONAL_STRENGTH: RULE_ID_SEASONAL_STRENGTH,
    EvidenceType.INITIAL_USE_SEASONAL_STRENGTH: RULE_ID_SEASONAL_STRENGTH,
    EvidenceType.CHANGED_USE_SEASONAL_STRENGTH: RULE_ID_SEASONAL_STRENGTH,
    EvidenceType.MOVING_LINE_STAGE: RULE_ID_MOVING_LINE_STAGE,
}

RELATION_EVIDENCE_WEIGHT = {
    BodyUseRelation.USE_GENERATES_BODY: (EvidencePolarity.POSITIVE, EvidenceStrength.STRONG),
    BodyUseRelation.BODY_CONTROLS_USE: (EvidencePolarity.POSITIVE, EvidenceStrength.MEDIUM),
    BodyUseRelation.SAME_ELEMENT: (EvidencePolarity.MIXED, EvidenceStrength.MEDIUM),
    BodyUseRelation.BODY_GENERATES_USE: (EvidencePolarity.NEGATIVE, EvidenceStrength.MEDIUM),
    BodyUseRelation.USE_CONTROLS_BODY: (EvidencePolarity.NEGATIVE, EvidenceStrength.STRONG),
}

SEASON_EVIDENCE_WEIGHT = {
    SeasonalStrength.PROSPEROUS: (EvidencePolarity.POSITIVE, EvidenceStrength.STRONG),
    SeasonalStrength.SUPPORTED: (EvidencePolarity.POSITIVE, EvidenceStrength.MEDIUM),
    SeasonalStrength.RESTING: (EvidencePolarity.NEUTRAL, EvidenceStrength.WEAK),
    SeasonalStrength.CONFINED: (EvidencePolarity.NEGATIVE, EvidenceStrength.MEDIUM),
    SeasonalStrength.DEAD: (EvidencePolarity.NEGATIVE, EvidenceStrength.STRONG),
}


def _relation_evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    relation: BodyUseRelation,
    subject: str,
) -> Evidence:
    polarity, strength = RELATION_EVIDENCE_WEIGHT[relation]
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=EVIDENCE_RULE_IDS[evidence_type],
        polarity=polarity,
        strength=strength,
        fact=f"{subject}关系为{RELATION_LABELS_ZH[relation]}",
        rule_statement="按木火土金水相生相克表，以体为参照计算关系。",
        data_version=_EVIDENCE_VERSION,
    )


def _season_evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    state: SeasonalStrength,
    subject: str,
    season: SeasonContext,
) -> Evidence:
    polarity, strength = SEASON_EVIDENCE_WEIGHT[state]
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=EVIDENCE_RULE_IDS[evidence_type],
        polarity=polarity,
        strength=strength,
        fact=f"{subject}在{season.month_branch}月为{SEASONAL_STRENGTH_LABELS_ZH[state]}",
        rule_statement="以节气月令主五行，按旺相休囚死固定关系分类。",
        data_version=_EVIDENCE_VERSION,
    )


def build_evidence(
    base_hexagram: Hexagram,
    body_use: BodyUseAssignment,
    initial_relation: BodyUseRelation,
    changed_relation: BodyUseRelation,
    mutual_lower_relation: BodyUseRelation,
    mutual_upper_relation: BodyUseRelation,
    moving_line: int,
    moving_stage: MovingLineStage,
    season: SeasonContext,
) -> tuple[Evidence, ...]:
    records = [
        Evidence(
            evidence_id="E01",
            evidence_type=EvidenceType.BASE_HEXAGRAM,
            source_ref=RULE_ID_BASE_HEXAGRAM,
            polarity=EvidencePolarity.NEUTRAL,
            strength=EvidenceStrength.MEDIUM,
            fact=f"本卦为第{base_hexagram.king_wen_number}卦{base_hexagram.full_name_zh}",
            rule_statement="下卦三爻在前、上卦三爻在后组成六爻。",
            data_version=_EVIDENCE_VERSION,
        ),
        _relation_evidence("E02", EvidenceType.INITIAL_BODY_USE_RELATION, initial_relation, "初始体用"),
        _relation_evidence("E03", EvidenceType.CHANGED_BODY_USE_RELATION, changed_relation, "变化后体用"),
        _relation_evidence("E04", EvidenceType.MUTUAL_LOWER_RELATION, mutual_lower_relation, "互卦下卦对体卦"),
        _relation_evidence("E05", EvidenceType.MUTUAL_UPPER_RELATION, mutual_upper_relation, "互卦上卦对体卦"),
        _season_evidence("E06", EvidenceType.BODY_SEASONAL_STRENGTH, season.body_strength, "体卦五行", season),
        _season_evidence(
            "E07", EvidenceType.INITIAL_USE_SEASONAL_STRENGTH, season.initial_use_strength, "初始用卦五行", season
        ),
        _season_evidence(
            "E08", EvidenceType.CHANGED_USE_SEASONAL_STRENGTH, season.changed_use_strength, "变化后用卦五行", season
        ),
        Evidence(
            evidence_id="E09",
            evidence_type=EvidenceType.MOVING_LINE_STAGE,
            source_ref=RULE_ID_MOVING_LINE_STAGE,
            polarity=EvidencePolarity.NEUTRAL,
            strength=EvidenceStrength.WEAK,
            fact=f"第{moving_line}爻对应{MOVING_LINE_STAGE_LABELS_ZH[moving_stage]}",
            rule_statement="动爻只映射确定性阶段标签，不生成吉凶或日期。",
            data_version=_EVIDENCE_VERSION,
        ),
    ]
    return tuple(records)
