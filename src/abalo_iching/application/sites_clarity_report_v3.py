"""Question-aligned clarity report for the Sites experience.

The report remains a deterministic presentation layer.  It may use the finite
structured intake to choose language, but it never parses free text as evidence
and never changes the chart or conclusion.
"""

from __future__ import annotations

from typing import Any, TypedDict

from .sites_question_context_v1 import DecisionStage, KeyUncertainty
from .sites_structured_question_v1 import DecisionGoal, QuestionDomain, TimeHorizon

CLARITY_REPORT_VERSION = "SITES_CLARITY_REPORT_V3"


class ClarityReport(TypedDict):
    template_version: str
    answer: str
    what_it_means: str
    priority: str
    continue_signals: list[str]
    pause_signals: list[str]
    next_action: str
    evidence_path: list[dict[str, str]]
    boundary_note: str


_TOPICS: dict[QuestionDomain, str] = {
    QuestionDomain.WORK_CAREER: "这份工作或职业选择",
    QuestionDomain.PROJECT_COOPERATION: "这项项目或合作",
    QuestionDomain.RELATIONSHIP_COMMUNICATION: "这段关系或沟通",
    QuestionDomain.PERSONAL_PLANNING: "这项个人计划",
}

_ANSWER_TEMPLATES: dict[str, str] = {
    "CLEARLY_FAVORABLE": "{topic}可以继续推进，但先用小范围行动验证，不必一次押满。",
    "CONDITIONALLY_FAVORABLE": "{topic}可以继续，但先补齐关键条件，再决定是否加码。",
    "MIXED_OR_UNSETTLED": "{topic}暂时不要下最终结论；先缩小投入，用一个可验证动作换取事实。",
    "CLEARLY_UNFAVORABLE": "{topic}当前更适合收缩投入、设清边界，先处理阻力再决定是否继续。",
    "INSUFFICIENT_EVIDENCE": "{topic}目前还看不清；先补一项关键事实，再做继续或停止的判断。",
}

_LEVEL_MEANINGS: dict[str, str] = {
    "CLEARLY_FAVORABLE": "当前支持因素相对集中，但有利不等于可以跳过现实条件。",
    "CONDITIONALLY_FAVORABLE": "卦象给出的不是无条件肯定，而是“条件出现后可行”。",
    "MIXED_OR_UNSETTLED": "支持与阻力同时存在，继续猜测不会让局面更清楚。",
    "CLEARLY_UNFAVORABLE": "当前结构对你的消耗或约束偏强，先保护可用资源更重要。",
    "INSUFFICIENT_EVIDENCE": "卦象没有给出足够清晰的方向，“暂时不知道”本身就是有效结论。",
}

_DOMAIN_FOCUS: dict[QuestionDomain, str] = {
    QuestionDomain.WORK_CAREER: "回到现实，重点看职责、资源与评价标准是否真正匹配。",
    QuestionDomain.PROJECT_COOPERATION: "回到现实，重点看双方分工、资源与交付能否形成闭环。",
    QuestionDomain.RELATIONSHIP_COMMUNICATION: "回到现实，重点看回应是否稳定、边界是否被尊重、说法能否落到行动。",
    QuestionDomain.PERSONAL_PLANNING: "回到现实，重点看时间、精力与资源能否承受这项计划。",
}

_GOAL_MEANINGS: dict[DecisionGoal, str] = {
    DecisionGoal.IDENTIFY_OBSTACLES: "此刻先识别最关键的阻力，不必急着证明最后结果。",
    DecisionGoal.PLAN_NEXT_STEP: "最有价值的不是一次决定到底，而是设计一个能带回新信息的下一步。",
    DecisionGoal.PREPARE_COMMUNICATION: "把沟通变成一个能够得到明确答复、并能观察后续行动的问题。",
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: "关键不是更用力，而是先写清你愿意给出的投入与不可越过的边界。",
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: "把判断标准从感受换成可观察、可重复、可核实的行动。",
}

_PRIORITIES: dict[str, str] = {
    "CLEARLY_FAVORABLE": "边推进，边核实",
    "CONDITIONALLY_FAVORABLE": "先看条件是否兑现",
    "MIXED_OR_UNSETTLED": "先换取事实，不急着定性",
    "CLEARLY_UNFAVORABLE": "先止损，再判断",
    "INSUFFICIENT_EVIDENCE": "先补信息，再决定",
}

_CONTINUE_SIGNALS: dict[QuestionDomain, tuple[str, str, str]] = {
    QuestionDomain.WORK_CAREER: ("职责与授权说得清楚", "关键资源或支持已经落实", "评价标准稳定且可核验"),
    QuestionDomain.PROJECT_COOPERATION: ("双方分工明确到人", "承诺的资源已经到位", "阶段节点按约兑现"),
    QuestionDomain.RELATIONSHIP_COMMUNICATION: ("对方有稳定而主动的回应", "你的边界被理解并尊重", "说法与实际行动保持一致"),
    QuestionDomain.PERSONAL_PLANNING: ("时间、精力与预算可以承受", "最小行动已经完成", "复盘后目标比之前更清楚"),
}

_PAUSE_SIGNALS: dict[QuestionDomain, tuple[str, str, str]] = {
    QuestionDomain.WORK_CAREER: ("责任增加但授权和资源没有增加", "评价标准反复变化", "持续投入却没有明确反馈"),
    QuestionDomain.PROJECT_COOPERATION: ("责任仍然模糊", "只有你一方持续加码", "阶段节点连续没有兑现"),
    QuestionDomain.RELATIONSHIP_COMMUNICATION: ("关系长期只靠你维持", "明确边界反复被越过", "承诺始终没有对应行动"),
    QuestionDomain.PERSONAL_PLANNING: ("关键依赖条件仍不清楚", "实际成本已经越过保留线", "重复投入却没有带回新信息"),
}

_STAGE_PREFIX: dict[DecisionStage, str] = {
    DecisionStage.EXPLORING: "你还在了解阶段，",
    DecisionStage.PREPARING: "你正在准备行动，",
    DecisionStage.ALREADY_ACTING: "你已经在推进，",
    DecisionStage.WAITING_FEEDBACK: "你正在等待反馈，",
}

_NEXT_ACTIONS: dict[QuestionDomain, dict[KeyUncertainty, str]] = {
    QuestionDomain.WORK_CAREER: {
        KeyUncertainty.CONDITIONS: "列出继续争取所需的三项最低条件，先确认其中最关键的一项是否真实存在。",
        KeyUncertainty.OTHER_RESPONSE: "向关键决策者提出一个可明确回答的问题，并只根据实际答复更新判断。",
        KeyUncertainty.OWN_COMMITMENT: "写下你愿意投入的时间与精力上限，在获得对等资源前不越过这条线。",
        KeyUncertainty.TIMING: "先完成一个可逆的小动作，用得到的反馈判断是否进入下一步。",
    },
    QuestionDomain.PROJECT_COOPERATION: {
        KeyUncertainty.CONDITIONS: "写下继续合作所需的三项最低条件，先验证成本最低、最关键的一项。",
        KeyUncertainty.OTHER_RESPONSE: "请对方确认一个可验收节点；只在实际回复和行动出现后，再决定是否追加投入。",
        KeyUncertainty.OWN_COMMITMENT: "列出已经投入的时间、精力与金钱，并先冻结超过保留线的新承诺。",
        KeyUncertainty.TIMING: "把下一笔投入拆成可撤回的一小步，完成复盘后再决定是否扩大。",
    },
    QuestionDomain.RELATIONSHIP_COMMUNICATION: {
        KeyUncertainty.CONDITIONS: "写下这段关系继续向前所需的三个基本条件，先观察最重要的一项是否出现。",
        KeyUncertainty.OTHER_RESPONSE: "清楚表达一次需要与边界，然后只观察对方的实际回应，不替对方补答案。",
        KeyUncertainty.OWN_COMMITMENT: "写下你愿意继续付出的上限，在对等回应出现前不再扩大投入。",
        KeyUncertainty.TIMING: "先进行一次低压力、可结束的沟通，再根据真实反馈决定是否继续。",
    },
    QuestionDomain.PERSONAL_PLANNING: {
        KeyUncertainty.CONDITIONS: "列出计划启动所需的三个最低条件，先补最关键且最容易验证的一项。",
        KeyUncertainty.OTHER_RESPONSE: "找到一个会受这项计划影响的人或资源方，取得一次明确反馈。",
        KeyUncertainty.OWN_COMMITMENT: "写下可承受的时间、精力与预算上限，只先投入其中最小的一部分。",
        KeyUncertainty.TIMING: "先完成一个最小版本，用实际体验判断现在是否适合继续。",
    },
}

_HORIZON_SUFFIX: dict[TimeHorizon, str] = {
    TimeHorizon.CURRENT: "先只处理眼前这一步。",
    TimeHorizon.NEXT_30_DAYS: "在这段观察范围内，只用阶段反馈更新判断。",
    TimeHorizon.NEXT_QUARTER: "把判断拆成阶段复盘，不一次承诺全部投入。",
    TimeHorizon.NEXT_6_MONTHS: "保留调整空间，让每个阶段的事实决定下一阶段。",
}


def build_clarity_report(
    deterministic_result: dict[str, Any],
    domain: QuestionDomain,
    goal: DecisionGoal,
    horizon: TimeHorizon,
    stage: DecisionStage,
    uncertainty: KeyUncertainty,
) -> ClarityReport:
    """Translate rule facts and finite display context into a decision aid."""
    conclusion = deterministic_result["deterministic_conclusion"]
    level = conclusion["conclusion_level"]
    topic = _TOPICS[domain]
    mentor = deterministic_result["mentor_report"]
    reasoning = mentor["reasoning"]
    evidence_path = [
        {"title": "起始关系", "text": reasoning[0]["text"]},
        {"title": "变化方向", "text": reasoning[1]["text"]},
        {"title": "承接能力", "text": reasoning[-1]["text"]},
    ]
    return {
        "template_version": CLARITY_REPORT_VERSION,
        "answer": _ANSWER_TEMPLATES[level].format(topic=topic),
        "what_it_means": f"{_LEVEL_MEANINGS[level]}{_DOMAIN_FOCUS[domain]}{_GOAL_MEANINGS[goal]}",
        "priority": _PRIORITIES[level],
        "continue_signals": list(_CONTINUE_SIGNALS[domain]),
        "pause_signals": list(_PAUSE_SIGNALS[domain]),
        "next_action": f"{_STAGE_PREFIX[stage]}{_NEXT_ACTIONS[domain][uncertainty]}{_HORIZON_SUFFIX[horizon]}",
        "evidence_path": evidence_path,
        "boundary_note": "卦象依据只来自确定性排盘与版本化规则。结构化处境只用于选择表达与现实核验项；问题原文只用于确认所问和呈现结果，绝不参与排盘，也不被伪装成卦象证据。",
    }
