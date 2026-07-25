"""Question-aligned clarity report for the Sites experience.

The report remains a deterministic presentation layer.  It may use the finite
structured intake to choose language, but it never parses free text as evidence
and never changes the chart or conclusion.
"""

from __future__ import annotations

from typing import Any, TypedDict

from .sites_question_context_v1 import DecisionStage, KeyUncertainty
from .sites_structured_question_v1 import (
    DecisionGoal,
    DecisionRiskProfile,
    QuestionDomain,
    TimeHorizon,
)

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
    "CLEARLY_FAVORABLE": "{topic}目前有继续往前走的空间，但仍要把条件和责任说清楚。",
    "CONDITIONALLY_FAVORABLE": "{topic}并非不能继续，关键在于所需条件能否真正到位。",
    "MIXED_OR_UNSETTLED": "{topic}眼下有支持也有阻力，先别急着把整件事一次定死。",
    "CLEARLY_UNFAVORABLE": "{topic}目前带来的牵制和消耗偏多，先守住边界，再谈是否继续。",
    "INSUFFICIENT_EVIDENCE": "{topic}现在还缺少足够依据，先弄清最关键的一件事实。",
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
    DecisionGoal.IDENTIFY_OBSTACLES: "先找出最卡住的一处，处理它，比同时担心所有问题更有用。",
    DecisionGoal.PLAN_NEXT_STEP: "这次先看眼前最该确认的那一步；等它有了实际回应，再决定后面怎么走。",
    DecisionGoal.PREPARE_COMMUNICATION: "沟通时把问题问具体，也留意对方之后有没有实际行动。",
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: "先写清自己愿意付出多少、什么情况必须停下来，避免越走越累。",
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: "少猜一点，多看现实里反复出现的回应和行动。",
}

# Each base hexagram receives its own plain-language emphasis.  These are
# presentation notes, not additional casting rules or good/bad judgments.
_HEXAGRAM_FOCUS: dict[int, str] = {
    1: "主动担当，也要让力量用在正处", 2: "顺势承接，先认清自己的位置和边界",
    3: "事情刚起步，先把混乱一件件理顺", 4: "信息还不完整，先问明白、学明白",
    5: "条件未齐时耐心等待，同时做好准备", 6: "分歧已经出现，先把事实和规则讲清",
    7: "把人和资源组织好，行动才不会散", 8: "确认彼此是否真心靠近、愿意同行",
    9: "先做小幅积累，不急着一口气完成", 10: "每一步都要谨慎，尤其要尊重边界",
    11: "上下能够相通时，把顺势落实为合作", 12: "沟通受阻时先疏通关系，不要硬推",
    13: "先找到共同目标，再谈分工与投入", 14: "手里资源越多，越要说明责任怎么承担",
    15: "放低姿态、保持分寸，反而更容易走稳", 16: "有了势头也要先做好准备，别只凭兴奋",
    17: "顺应变化，但别在跟随中丢掉原则", 18: "先修补积累已久的问题，再开启下一步",
    19: "机会正在靠近，宜主动接触并观察回应", 20: "先看清全貌和细节，再决定是否出手",
    21: "面对卡点要明确处理，不能一直绕开", 22: "形式可以帮助表达，但不能盖过实际内容",
    23: "旧结构正在脱落，先保住最重要的部分", 24: "偏离之后及时回到正轨，宜从小处重新开始",
    25: "按真实情况行事，不凭侥幸也不过度设想", 26: "先把能力和资源蓄足，再承担更大的事",
    27: "留意自己在吸收什么，也留意说出什么", 28: "负担已经偏重，先给结构减压",
    29: "风险可能反复出现，靠稳住步骤穿过去", 30: "把事情照亮看清，也确认自己依靠什么",
    31: "双方正在互相影响，回应是否真诚很重要", 32: "看一件事能否长久，要看是否经得起重复",
    33: "暂退不是放弃，而是避开不利位置", 34: "力量正在增强，更需要克制和正确用力",
    35: "局面有向前的机会，要让成果被看见", 36: "环境不利时先保护自己，不必处处显露",
    37: "先理清各自角色、责任和相处规则", 38: "看见彼此差异，先求能合作的部分",
    39: "前路受阻时换一条路，并主动寻求帮助", 40: "先解除最紧的束缚，让局面重新松动",
    41: "有所减少，是为了保住更重要的部分", 42: "增加投入要让双方都真正受益",
    43: "该说清时要果断说清，同时避免用力过猛", 44: "面对突然出现的人或机会，先守住边界",
    45: "人和资源聚在一起后，更需要共同秩序", 46: "稳稳向上，一步一步积累可信成果",
    47: "资源受限时先保住心力，不与困境硬耗", 48: "回到长期可用的基础，看它是否真正维护好了",
    49: "改变旧办法之前，先争取理解与信任", 50: "不只换表面做法，更要更新承载事情的结构",
    51: "突然变化来临时先稳住，再处理后续", 52: "知道什么时候停下来，才能重新看清",
    53: "事情适合循序渐进，不宜跳过中间步骤", 54: "关系位置尚未安稳，承诺之前先看是否对等",
    55: "局面正盛时也要为转折和收束做准备", 56: "身处暂时位置，行事宜清醒、简洁、留有余地",
    57: "用持续而温和的方式进入问题深处", 58: "坦诚交流能够打开局面，但承诺要落到行动",
    59: "先化开隔阂和僵局，再重新凝聚人心", 60: "设定合适的节制，既不能失控也不能过苛",
    61: "真诚与信任是核心，也要经得起事实核对", 62: "先把小事做稳，暂不承担过大的动作",
    63: "事情虽已成形，越到后来越要防止松懈", 64: "事情尚未完成，最后几步更要分清次序",
}

_PRIORITIES: dict[str, str] = {
    "CLEARLY_FAVORABLE": "边推进，边核实",
    "CONDITIONALLY_FAVORABLE": "先看条件是否兑现",
    "MIXED_OR_UNSETTLED": "先换取事实，不急着定性",
    "CLEARLY_UNFAVORABLE": "先止损，再判断",
    "INSUFFICIENT_EVIDENCE": "先补信息，再决定",
}

_CONTINUE_SIGNALS: dict[QuestionDomain, tuple[str, str, str]] = {
    QuestionDomain.WORK_CAREER: ("你的职责与授权范围，以及需要承担的结果，都已经说清楚。", "完成工作所需的人力、时间、预算或上级支持已经实际到位。", "评价标准在行动前已经明确，并且可以用事实核对。"),
    QuestionDomain.PROJECT_COOPERATION: ("双方分工已经明确到具体负责人和可验收的交付结果。", "对方承诺的人力、预算、信息或渠道已经实际到位。", "约定的阶段节点能够按时完成，并且结果可以验收。"),
    QuestionDomain.RELATIONSHIP_COMMUNICATION: ("对方有稳定而主动的回应，而不是只在你推动时出现。", "你表达的需要和边界被听见，也在后续行动中得到尊重。", "双方说过的话能够落实为持续而一致的行动。"),
    QuestionDomain.PERSONAL_PLANNING: ("现有时间、精力与预算都在你能长期承受的范围内。", "计划依赖的人、资源与长期责任已经明确。", "复盘后，目标、优先级和下一步比开始时更清楚。"),
}

_PAUSE_SIGNALS: dict[QuestionDomain, tuple[str, str, str]] = {
    QuestionDomain.WORK_CAREER: ("责任不断增加，但对应的权限、人力或时间没有同步增加。", "评价标准在推进过程中反复改变，让你无法判断怎样才算完成。", "你持续投入，却迟迟得不到明确反馈、资源承诺或下一步安排。"),
    QuestionDomain.PROJECT_COOPERATION: ("谁负责、交付什么、何时完成仍然没有明确约定。", "只有你一方不断增加时间、资金或资源，对方没有对等行动。", "已经约定的节点连续落空，也没有新的可执行补救安排。"),
    QuestionDomain.RELATIONSHIP_COMMUNICATION: ("这段关系长期只靠你联系、解释或维持，对方很少主动回应。", "你已经说清的边界被反复越过，而且没有看到对方调整。", "对方多次作出承诺，却始终没有相应行动。"),
    QuestionDomain.PERSONAL_PLANNING: ("计划启动所需的前提还没确认，例如时间、预算、必要资源或他人配合。", "实际投入已经超过你事先设定的时间、精力或预算上限。", "你反复投入相同的努力，却没有获得新的事实或反馈来修正判断。"),
}

_PLAIN_RELATION_EFFECTS: dict[str, str] = {
    "USE_GENERATES_BODY": "外部条件正在给你提供支持，但要以已经出现的资源、回应或行动为准。",
    "BODY_CONTROLS_USE": "你仍有一定主动权，可以调整节奏、投入或边界；这份主动权需要现实能力和资源来兑现。",
    "SAME_ELEMENT": "你与这件事目前较为同频，互动可能增加；是否真正有利，仍要看配合质量和实际结果。",
    "BODY_GENERATES_USE": "你正在持续向这件事投入，需要确认付出是否得到相称回应，避免长期单方面支撑。",
    "USE_CONTROLS_BODY": "外部条件对你形成较强约束，宜先找出压力来源，并保护时间、资源和可承受边界。",
}

_PLAIN_STRENGTH_EFFECTS: dict[str, str] = {
    "PROSPEROUS": "当前可动用的力量较充足，更有余力承接任务和推动变化；仍需把优势落实成行动。",
    "SUPPORTED": "当前能得到一定助力，具备承接和调整空间；推进前仍要确认关键资源是否真实到位。",
    "RESTING": "当前力量较平稳，但余量有限；适合保留调整空间，用新反馈决定是否增加投入。",
    "CONFINED": "当前可动用的力量受到限制；推进更依赖外部支持、清楚节奏和明确边界。",
    "DEAD": "当前助力很弱，单靠意愿容易造成消耗；宜先降低不可逆成本，补足资源后再判断。",
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
        KeyUncertainty.OWN_COMMITMENT: "列出已经投入的时间、精力与金钱，并先暂停超过保留线的新承诺。",
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
        KeyUncertainty.OWN_COMMITMENT: "写下可承受的时间、精力与预算上限，先确认长期责任是否与你的边界一致。",
        KeyUncertainty.TIMING: "先确认决定所依赖的关键条件是否已经具备，再判断现在是否适合继续。",
    },
}

_HIGH_IRREVERSIBLE_CONTINUE_SIGNALS = (
    "直接受影响的人已经明确表达意愿，而不是由你替对方假设。",
    "长期责任、资源安排与需要专业核实的现实条件已经说清楚。",
    "关键分歧已有双方认可的处理方式，不依赖一方单独承担后果。",
)

_HIGH_IRREVERSIBLE_PAUSE_SIGNALS = (
    "核心当事人的意愿仍然空白、回避或彼此冲突。",
    "长期责任与代价尚未分配清楚，主要由一方补齐答案。",
    "需要医疗、法律、财务等专业判断的现实条件尚未核实。",
)

_HIGH_IRREVERSIBLE_NEXT_ACTIONS: dict[KeyUncertainty, str] = {
    KeyUncertainty.CONDITIONS: "列出作出决定前不能缺少的共同意愿、长期责任与专业现实条件，并逐项确认。",
    KeyUncertainty.OTHER_RESPONSE: "与直接受影响的人完成一次完整对谈，明确记录彼此意愿、责任与不能接受的边界。",
    KeyUncertainty.OWN_COMMITMENT: "先写清你愿意承担和不能独自承担的长期责任，再确认对方是否愿意共同承担。",
    KeyUncertainty.TIMING: "先核实共同意愿与关键现实条件；它们没有说清前，不把不可逆决定继续往下推进。",
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
    risk_profile: DecisionRiskProfile = DecisionRiskProfile.STANDARD,
) -> ClarityReport:
    """Translate rule facts and finite display context into a decision aid."""
    conclusion = deterministic_result["deterministic_conclusion"]
    level = conclusion["conclusion_level"]
    topic = _TOPICS[domain]
    body_use = deterministic_result["body_use"]
    body_strength = deterministic_result["seasonal_strength"]["body"]
    base = deterministic_result["base_hexagram"]
    changed = deterministic_result["changed_hexagram"]
    base_focus = _HEXAGRAM_FOCUS[base["king_wen_number"]]
    changed_focus = _HEXAGRAM_FOCUS[changed["king_wen_number"]]
    evidence_path = [
        {"title": "一开始怎么看", "text": f"事情刚开始时，{_PLAIN_RELATION_EFFECTS[body_use['initial_relation']]}"},
        {"title": "事情会怎么变", "text": f"动爻发生变化后，{_PLAIN_RELATION_EFFECTS[body_use['changed_relation']]}"},
        {"title": "你现在有多少余力", "text": _PLAIN_STRENGTH_EFFECTS[body_strength]},
    ]
    high_irreversible = risk_profile is DecisionRiskProfile.HIGH_IRREVERSIBLE
    continue_signals = (
        _HIGH_IRREVERSIBLE_CONTINUE_SIGNALS
        if high_irreversible
        else _CONTINUE_SIGNALS[domain]
    )
    pause_signals = (
        _HIGH_IRREVERSIBLE_PAUSE_SIGNALS
        if high_irreversible
        else _PAUSE_SIGNALS[domain]
    )
    next_action = (
        _HIGH_IRREVERSIBLE_NEXT_ACTIONS[uncertainty]
        if high_irreversible
        else _NEXT_ACTIONS[domain][uncertainty]
    )
    domain_focus = (
        "回到现实，先确认共同意愿、长期责任与需要专业核实的条件。"
        if high_irreversible
        else _DOMAIN_FOCUS[domain]
    )
    return {
        "template_version": CLARITY_REPORT_VERSION,
        "answer": f"{base['name']}把重点放在“{base_focus}”。{_ANSWER_TEMPLATES[level].format(topic=topic)}",
        "what_it_means": (
            f"本卦是{base['name']}，先提醒你：{base_focus}。"
            f"动爻之后变为{changed['name']}，局面的下一层重点转向：{changed_focus}。"
            f"{_LEVEL_MEANINGS[level]}{domain_focus}{_GOAL_MEANINGS[goal]}"
        ),
        "priority": _PRIORITIES[level],
        "continue_signals": list(continue_signals),
        "pause_signals": list(pause_signals),
        "next_action": f"{_STAGE_PREFIX[stage]}{next_action}{_HORIZON_SUFFIX[horizon]}",
        "evidence_path": evidence_path,
        "boundary_note": "这份解读先由三个数字排定卦象，再结合你选择的现实处境安排说明重点。你写下的问题帮助我们把卦意说到具体事情上；真正做决定时，请继续以现实中的回应、资源与行动为准。",
    }
