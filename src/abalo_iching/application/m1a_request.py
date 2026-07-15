"""M1-A intake boundary constructed only from validated Contract V2 fields."""

from __future__ import annotations

from dataclasses import dataclass

from .sites_meihua_service_v2 import CONTRACT_VERSION_V2
from .sites_structured_question_v1 import (
    DecisionGoal,
    QuestionDomain,
    TimeHorizon,
    generate_structured_question,
)


@dataclass(frozen=True, slots=True)
class M1AIntake:
    """Narrow product-semantic input; deterministic cast data is intentionally absent."""

    question_id: str
    question_domain: QuestionDomain
    decision_goal: DecisionGoal
    time_horizon: TimeHorizon
    normalized_question: str
    question_template_version: str
    contract_version: str
    is_synthetic: bool

    def __post_init__(self) -> None:
        self.validate_m1a_boundary()

    def validate_m1a_boundary(self) -> None:
        """Re-run the authoritative Application boundary validation."""
        validate_m1a_intake_fields(
            question_id=self.question_id,
            question_domain=self.question_domain,
            decision_goal=self.decision_goal,
            time_horizon=self.time_horizon,
            normalized_question=self.normalized_question,
            question_template_version=self.question_template_version,
            contract_version=self.contract_version,
            is_synthetic=self.is_synthetic,
        )


def validate_m1a_intake_fields(
    *,
    question_id: str,
    question_domain: QuestionDomain,
    decision_goal: DecisionGoal,
    time_horizon: TimeHorizon,
    normalized_question: str,
    question_template_version: str,
    contract_version: str,
    is_synthetic: bool,
) -> None:
    """Validate M1-A fields against the single authoritative Contract V2 path."""
    if not isinstance(question_id, str) or not question_id or question_id.strip() != question_id:
        raise ValueError("question_id must be a non-empty normalized string")
    if len(question_id) > 128:
        raise ValueError("question_id must not exceed 128 characters")
    if type(question_domain) is not QuestionDomain:  # noqa: E721 - strict boundary by design
        raise TypeError("question_domain must be the Contract V2 enum")
    if type(decision_goal) is not DecisionGoal:  # noqa: E721 - strict boundary by design
        raise TypeError("decision_goal must be the Contract V2 enum")
    if type(time_horizon) is not TimeHorizon:  # noqa: E721 - strict boundary by design
        raise TypeError("time_horizon must be the Contract V2 enum")
    expected_question, expected_template_version = generate_structured_question(
        question_domain,
        decision_goal,
        time_horizon,
    )
    if normalized_question != expected_question:
        raise ValueError("normalized_question must match the server-owned V2 template")
    if question_template_version != expected_template_version:
        raise ValueError("question_template_version must match the V2 template")
    if contract_version != CONTRACT_VERSION_V2:
        raise ValueError("contract_version must match Contract V2")
    if is_synthetic is not True:
        raise ValueError("M1-A accepts synthetic inputs only")


def build_m1a_intake(
    *,
    question_id: str,
    question_domain: QuestionDomain,
    decision_goal: DecisionGoal,
    time_horizon: TimeHorizon,
    normalized_question: str,
    question_template_version: str,
    contract_version: str,
    is_synthetic: bool,
) -> M1AIntake:
    """Accept only server-validated V2 values and recheck their canonical question."""
    return M1AIntake(
        question_id=question_id,
        question_domain=question_domain,
        decision_goal=decision_goal,
        time_horizon=time_horizon,
        normalized_question=normalized_question,
        question_template_version=question_template_version,
        contract_version=contract_version,
        is_synthetic=is_synthetic,
    )
