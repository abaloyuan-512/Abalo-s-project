"""Immutable data contract for deterministic Meihua charts."""

from dataclasses import dataclass
from datetime import datetime

from .enums import (
    BodyUseRelation,
    Element,
    EvidencePolarity,
    EvidenceStrength,
    EvidenceType,
    MovingLineStage,
    SeasonalStrength,
    TimingLevel,
)


@dataclass(frozen=True, slots=True)
class MeihuaInput:
    first_number: int
    second_number: int
    third_number: int
    cast_at: datetime
    timezone_name: str
    question_id: str | None = None


@dataclass(frozen=True, slots=True)
class Trigram:
    number: int
    name_zh: str
    symbol: str
    element: Element
    lines_bottom_up: tuple[int, int, int]
    data_version: str


@dataclass(frozen=True, slots=True)
class Hexagram:
    king_wen_number: int
    name_zh: str
    full_name_zh: str
    unicode_symbol: str
    upper_trigram: Trigram
    lower_trigram: Trigram
    lines_bottom_up: tuple[int, int, int, int, int, int]
    data_version: str


@dataclass(frozen=True, slots=True)
class BodyUseAssignment:
    body_trigram: Trigram
    initial_use_trigram: Trigram
    changed_use_trigram: Trigram


@dataclass(frozen=True, slots=True)
class ElementSeasonStrength:
    element: Element
    state: SeasonalStrength
    label_zh: str
    rank: int


@dataclass(frozen=True, slots=True)
class SeasonContext:
    current_solar_term: str
    current_solar_term_started_at: datetime
    month_branch: str
    month_start_solar_term: str
    month_element: Element
    element_strengths: tuple[ElementSeasonStrength, ...]
    body_strength: SeasonalStrength
    initial_use_strength: SeasonalStrength
    changed_use_strength: SeasonalStrength

    def strength_for(self, element: Element) -> SeasonalStrength:
        for item in self.element_strengths:
            if item.element is element:
                return item.state
        raise KeyError(element)


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    evidence_type: EvidenceType
    source_ref: str
    polarity: EvidencePolarity
    strength: EvidenceStrength
    fact: str
    rule_statement: str
    data_version: str


@dataclass(frozen=True, slots=True)
class TimingContext:
    exact_date_feature_enabled: bool = False
    level: TimingLevel = TimingLevel.STAGE_ONLY
    candidate_dates: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuleVersions:
    rule_version: str
    trigram_data_version: str
    hexagram_data_version: str
    calendar_provider: str
    engine_version: str


@dataclass(frozen=True, slots=True)
class MeihuaChart:
    input: MeihuaInput
    upper_trigram: Trigram
    lower_trigram: Trigram
    moving_line: int
    base_hexagram: Hexagram
    mutual_hexagram: Hexagram
    changed_hexagram: Hexagram
    body_use_assignment: BodyUseAssignment
    initial_body_use_relation: BodyUseRelation
    changed_body_use_relation: BodyUseRelation
    mutual_lower_to_body_relation: BodyUseRelation
    mutual_upper_to_body_relation: BodyUseRelation
    moving_line_stage: MovingLineStage
    season_context: SeasonContext
    evidence: tuple[Evidence, ...]
    timing: TimingContext
    versions: RuleVersions

    @property
    def body_trigram(self) -> Trigram:
        return self.body_use_assignment.body_trigram

    @property
    def initial_use_trigram(self) -> Trigram:
        return self.body_use_assignment.initial_use_trigram

    @property
    def changed_use_trigram(self) -> Trigram:
        return self.body_use_assignment.changed_use_trigram
