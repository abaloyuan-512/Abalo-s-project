from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.meihua.engine import cast_meihua
from abalo_iching.meihua.enums import (
    BodyUseRelation,
    EvidencePolarity,
    EvidenceStrength,
    EvidenceType,
    SeasonalStrength,
)
from abalo_iching.meihua.evidence import (
    EVIDENCE_RULE_IDS,
    RELATION_EVIDENCE_WEIGHT,
    RULE_ID_BASE_HEXAGRAM,
    RULE_ID_MOVING_LINE_STAGE,
    SEASON_EVIDENCE_WEIGHT,
)
from abalo_iching.meihua.models import MeihuaInput


@pytest.mark.parametrize(
    "relation,expected",
    [
        (BodyUseRelation.USE_GENERATES_BODY, (EvidencePolarity.POSITIVE, EvidenceStrength.STRONG)),
        (BodyUseRelation.BODY_CONTROLS_USE, (EvidencePolarity.POSITIVE, EvidenceStrength.MEDIUM)),
        (BodyUseRelation.SAME_ELEMENT, (EvidencePolarity.MIXED, EvidenceStrength.MEDIUM)),
        (BodyUseRelation.BODY_GENERATES_USE, (EvidencePolarity.NEGATIVE, EvidenceStrength.MEDIUM)),
        (BodyUseRelation.USE_CONTROLS_BODY, (EvidencePolarity.NEGATIVE, EvidenceStrength.STRONG)),
    ],
)
def test_relation_evidence_weight_is_frozen(
    relation: BodyUseRelation,
    expected: tuple[EvidencePolarity, EvidenceStrength],
) -> None:
    assert RELATION_EVIDENCE_WEIGHT[relation] == expected


@pytest.mark.parametrize(
    "state,expected",
    [
        (SeasonalStrength.PROSPEROUS, (EvidencePolarity.POSITIVE, EvidenceStrength.STRONG)),
        (SeasonalStrength.SUPPORTED, (EvidencePolarity.POSITIVE, EvidenceStrength.MEDIUM)),
        (SeasonalStrength.RESTING, (EvidencePolarity.NEUTRAL, EvidenceStrength.WEAK)),
        (SeasonalStrength.CONFINED, (EvidencePolarity.NEGATIVE, EvidenceStrength.MEDIUM)),
        (SeasonalStrength.DEAD, (EvidencePolarity.NEGATIVE, EvidenceStrength.STRONG)),
    ],
)
def test_seasonal_evidence_weight_is_frozen(
    state: SeasonalStrength,
    expected: tuple[EvidencePolarity, EvidenceStrength],
) -> None:
    assert SEASON_EVIDENCE_WEIGHT[state] == expected


def test_every_evidence_source_ref_is_a_documented_stable_rule_id() -> None:
    spec = (Path(__file__).parents[1] / "docs/specs/MEIHUA_RULE_SPEC_V1.md").read_text(encoding="utf-8")
    assert set(EVIDENCE_RULE_IDS) == set(EvidenceType)
    assert all(source_ref in spec for source_ref in EVIDENCE_RULE_IDS.values())

    chart = cast_meihua(
        MeihuaInput(
            100,
            27,
            368,
            datetime(2026, 7, 10, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
            "Asia/Shanghai",
        )
    )
    assert {item.evidence_type: item.source_ref for item in chart.evidence} == EVIDENCE_RULE_IDS
    base = next(item for item in chart.evidence if item.evidence_type is EvidenceType.BASE_HEXAGRAM)
    stage = next(item for item in chart.evidence if item.evidence_type is EvidenceType.MOVING_LINE_STAGE)
    assert (base.source_ref, base.polarity, base.strength) == (
        RULE_ID_BASE_HEXAGRAM,
        EvidencePolarity.NEUTRAL,
        EvidenceStrength.MEDIUM,
    )
    assert (stage.source_ref, stage.polarity, stage.strength) == (
        RULE_ID_MOVING_LINE_STAGE,
        EvidencePolarity.NEUTRAL,
        EvidenceStrength.WEAK,
    )
