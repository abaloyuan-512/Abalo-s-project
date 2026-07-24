"""Deterministic structured-question templates for Sites Contract V2."""

from __future__ import annotations

from enum import StrEnum

TEMPLATE_VERSION = "SITES_STRUCTURED_QUESTION_TEMPLATE_V1"


class QuestionDomain(StrEnum):
    WORK_CAREER = "WORK_CAREER"
    PROJECT_COOPERATION = "PROJECT_COOPERATION"
    RELATIONSHIP_COMMUNICATION = "RELATIONSHIP_COMMUNICATION"
    PERSONAL_PLANNING = "PERSONAL_PLANNING"


class DecisionGoal(StrEnum):
    IDENTIFY_OBSTACLES = "IDENTIFY_OBSTACLES"
    PLAN_NEXT_STEP = "PLAN_NEXT_STEP"
    PREPARE_COMMUNICATION = "PREPARE_COMMUNICATION"
    ADJUST_COMMITMENT_BOUNDARIES = "ADJUST_COMMITMENT_BOUNDARIES"
    OBSERVE_VERIFY_SIGNALS = "OBSERVE_VERIFY_SIGNALS"


class TimeHorizon(StrEnum):
    CURRENT = "CURRENT"
    NEXT_30_DAYS = "NEXT_30_DAYS"
    NEXT_QUARTER = "NEXT_QUARTER"
    NEXT_6_MONTHS = "NEXT_6_MONTHS"


class DecisionRiskProfile(StrEnum):
    """Display-safety context only; never participates in chart calculation."""

    STANDARD = "STANDARD"
    HIGH_IRREVERSIBLE = "HIGH_IRREVERSIBLE"


ALLOWED_GOALS: dict[QuestionDomain, frozenset[DecisionGoal]] = {
    QuestionDomain.WORK_CAREER: frozenset({
        DecisionGoal.IDENTIFY_OBSTACLES,
        DecisionGoal.PLAN_NEXT_STEP,
        DecisionGoal.PREPARE_COMMUNICATION,
        DecisionGoal.OBSERVE_VERIFY_SIGNALS,
    }),
    QuestionDomain.PROJECT_COOPERATION: frozenset(DecisionGoal),
    QuestionDomain.RELATIONSHIP_COMMUNICATION: frozenset({
        DecisionGoal.PLAN_NEXT_STEP,
        DecisionGoal.PREPARE_COMMUNICATION,
        DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES,
        DecisionGoal.OBSERVE_VERIFY_SIGNALS,
    }),
    QuestionDomain.PERSONAL_PLANNING: frozenset({
        DecisionGoal.IDENTIFY_OBSTACLES,
        DecisionGoal.PLAN_NEXT_STEP,
        DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES,
        DecisionGoal.OBSERVE_VERIFY_SIGNALS,
    }),
}

_DOMAIN_LABELS = {
    QuestionDomain.WORK_CAREER: "工作与职业发展",
    QuestionDomain.PROJECT_COOPERATION: "项目与合作推进",
    QuestionDomain.RELATIONSHIP_COMMUNICATION: "关系与沟通",
    QuestionDomain.PERSONAL_PLANNING: "个人规划",
}

_HORIZON_LABELS = {
    TimeHorizon.CURRENT: "当前阶段",
    TimeHorizon.NEXT_30_DAYS: "未来30天",
    TimeHorizon.NEXT_QUARTER: "未来一个季度",
    TimeHorizon.NEXT_6_MONTHS: "未来6个月",
}

_GOAL_TEMPLATES = {
    DecisionGoal.IDENTIFY_OBSTACLES: "我当前最需要识别哪些阻力与支持条件？",
    DecisionGoal.PLAN_NEXT_STEP: "我应如何规划下一步自身可控行动？",
    DecisionGoal.PREPARE_COMMUNICATION: "我应如何准备一次现实沟通，并观察哪些反馈？",
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: "我应如何调整自己的投入与边界？",
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: "我应重点观察和核实哪些现实信号？",
}


def parse_structured_fields(
    question_domain: object,
    decision_goal: object,
    time_horizon: object,
) -> tuple[QuestionDomain, DecisionGoal, TimeHorizon]:
    """Parse the three public enums and reject every unknown value."""
    if not all(isinstance(value, str) for value in (question_domain, decision_goal, time_horizon)):
        raise ValueError("structured fields must be strings")
    try:
        return (
            QuestionDomain(question_domain),
            DecisionGoal(decision_goal),
            TimeHorizon(time_horizon),
        )
    except ValueError as exc:
        raise ValueError("unknown structured field value") from exc


def parse_decision_risk_profile(value: object) -> DecisionRiskProfile:
    if value is None:
        return DecisionRiskProfile.STANDARD
    if not isinstance(value, str):
        raise ValueError("decision risk profile must be a string")
    try:
        return DecisionRiskProfile(value)
    except ValueError as exc:
        raise ValueError("unknown decision risk profile") from exc


def generate_structured_question(
    question_domain: QuestionDomain,
    decision_goal: DecisionGoal,
    time_horizon: TimeHorizon,
) -> tuple[str, str]:
    """Return the one canonical question for an allowed finite combination."""
    if decision_goal not in ALLOWED_GOALS.get(question_domain, frozenset()):
        raise ValueError("question domain and decision goal are not an allowed combination")
    question = (
        f"在“{_DOMAIN_LABELS[question_domain]}”情境下，围绕“{_HORIZON_LABELS[time_horizon]}”，"
        f"{_GOAL_TEMPLATES[decision_goal]}"
    )
    return question, TEMPLATE_VERSION
