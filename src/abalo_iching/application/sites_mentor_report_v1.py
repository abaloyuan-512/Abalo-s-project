"""Deterministic, plain-language product guidance for the Sites result page.

This module does not add divination rules or infer real-world facts.  It only
translates the existing chart roles, body/use assessment and structured user
goal into a cautious, reversible reflection guide.
"""

from __future__ import annotations

from typing import TypedDict

from abalo_iching.interpretation.enums import ConclusionLevel, RelationPhase
from abalo_iching.interpretation.models import RelationAssessment, SynthesisResult
from abalo_iching.meihua.enums import (
    BodyUseRelation,
    MOVING_LINE_STAGE_LABELS_ZH,
    SEASONAL_STRENGTH_LABELS_ZH,
)
from abalo_iching.meihua.models import MeihuaChart

from .sites_structured_question_v1 import DecisionGoal, TimeHorizon

MENTOR_REPORT_TEMPLATE_VERSION = "SITES_MENTOR_REPORT_V1"


class MentorTextItem(TypedDict):
    title: str
    text: str


class MentorActionItem(TypedDict):
    title: str
    action: str
    why: str


class MentorReport(TypedDict):
    template_version: str
    opening: str
    reading_guide: list[MentorTextItem]
    reasoning: list[MentorTextItem]
    action_plan: list[MentorActionItem]
    cautions: list[str]
    review_questions: list[str]
    boundary_note: str


_OPENING = {
    ConclusionLevel.CLEARLY_FAVORABLE: (
        "当前结构里，支持因素相对集中。可以带着审慎的信心推进，但仍要用现实反馈确认，"
        "不要把“较顺”理解成结果已经确定。"
    ),
    ConclusionLevel.CONDITIONALLY_FAVORABLE: (
        "这组结构显示事情有推进空间，不过顺利与否取决于若干现实条件。你不需要急着一次做完，"
        "先确认关键条件，再逐步加大投入会更稳妥。"
    ),
    ConclusionLevel.MIXED_OR_UNSETTLED: (
        "当前更像处在尚未定型的阶段：不同力量同时存在，所以暂时看不清并不等于结果不好。"
        "最有价值的做法，是用小步骤取得新信息，让局面逐渐清楚。"
    ),
    ConclusionLevel.CLEARLY_UNFAVORABLE: (
        "当前结构提示阻力和消耗值得优先照顾。这不是在否定你的选择，也不代表事情必然失败；"
        "更合适的节奏是先降低不可逆成本，补足条件后再决定是否继续。"
    ),
    ConclusionLevel.INSUFFICIENT_EVIDENCE: (
        "现有结构不足以支持明确方向。与其勉强得到答案，不如先收集现实信息，"
        "等关键条件清楚后再判断。"
    ),
}

_RELATION_TEXT = {
    BodyUseRelation.USE_GENERATES_BODY: (
        "用生体",
        "议题一方对你这一方呈支持关系，可理解为外部条件有机会提供资源、回应或助力。",
    ),
    BodyUseRelation.BODY_CONTROLS_USE: (
        "体克用",
        "你对议题一方具有主动管理空间，但这种主动性要靠真实的能力、资源和持续执行来兑现。",
    ),
    BodyUseRelation.SAME_ELEMENT: (
        "体用比和",
        "双方处在同类关系中，互动可能较多，但单凭比和不能判定有利或不利，仍要看现实配合。",
    ),
    BodyUseRelation.BODY_GENERATES_USE: (
        "体生用",
        "你这一方正在向议题持续投入精力、时间或资源，因此需要留意投入是否得到相称回应。",
    ),
    BodyUseRelation.USE_CONTROLS_BODY: (
        "用克体",
        "议题一方对你形成较强约束或压力，优先辨认压力来源和可调整边界，比硬推更重要。",
    ),
}

_HORIZON_LABELS = {
    TimeHorizon.CURRENT: "当前阶段",
    TimeHorizon.NEXT_30_DAYS: "未来30天",
    TimeHorizon.NEXT_QUARTER: "未来一个季度",
    TimeHorizon.NEXT_6_MONTHS: "未来6个月",
}

_GOAL_ACTIONS: dict[DecisionGoal, list[MentorActionItem]] = {
    DecisionGoal.IDENTIFY_OBSTACLES: [
        {"title": "把阻力写具体", "action": "列出最多三项正在拖慢事情的现实因素，并区分哪些可控、哪些不可控。", "why": "具体化能把模糊担忧变成可处理的问题。"},
        {"title": "同时寻找支持", "action": "确认现有资源、愿意协助的人和已经出现的正向反馈。", "why": "只盯阻力容易放大压力，支持条件决定下一步能走多远。"},
        {"title": "先验证一个关键点", "action": "选择影响最大、验证成本最低的一项条件，在时间窗口内取得事实反馈。", "why": "一次验证一个关键点，更容易看清真正的瓶颈。"},
    ],
    DecisionGoal.PLAN_NEXT_STEP: [
        {"title": "选择最小可逆行动", "action": "把下一步缩小到一次沟通、一份草案或一个小范围尝试，避免一开始作出难以撤回的承诺。", "why": "小步行动既能推进，也能保留根据反馈调整的空间。"},
        {"title": "预先定义观察信号", "action": "行动前写下什么反馈代表可以继续，什么反馈代表需要调整或暂停。", "why": "先定标准可以减少事后用情绪解释结果。"},
        {"title": "设置复盘节点", "action": "在所选时间窗口内安排一次明确复盘，只根据新事实决定是否扩大投入。", "why": "阶段性复盘能防止尚未看清时持续加码。"},
    ],
    DecisionGoal.PREPARE_COMMUNICATION: [
        {"title": "先整理事实", "action": "分别写下已确认事实、自己的感受和仍需核实的猜测。", "why": "把三者分开，沟通会更客观，也更不容易让对方感到被定性。"},
        {"title": "提出清晰请求", "action": "用一句话说明你希望对方回应或共同决定的具体事项。", "why": "清楚的请求比笼统表达更容易得到可验证反馈。"},
        {"title": "观察回应质量", "action": "关注对方是否回应事实、是否愿意承担下一步，以及言行是否一致。", "why": "实际回应比对动机的猜测更可靠。"},
    ],
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: [
        {"title": "盘点真实投入", "action": "列出正在投入的时间、精力、金钱与情绪成本。", "why": "看清成本，才能判断当前边界是否可持续。"},
        {"title": "设定保留线", "action": "明确哪些资源必须为自己保留，以及出现什么情况就暂停追加投入。", "why": "边界能保护判断能力，不等于消极或放弃。"},
        {"title": "用小调整测试关系", "action": "先减少一项非必要投入，观察对方或环境是否出现更对等的回应。", "why": "小调整可以验证结构，而不必立刻作出极端决定。"},
    ],
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: [
        {"title": "列出支持信号", "action": "记录三项可观察的正向事实，例如资源到位、明确回复或持续行动。", "why": "可观察事实能防止把愿望当作进展。"},
        {"title": "列出风险信号", "action": "记录三项需要警惕的事实，例如反复拖延、承诺与行动不一致或成本持续上升。", "why": "提前定义风险信号，能在压力中保持客观。"},
        {"title": "限定观察周期", "action": "在所选时间窗口内设定一次检查点，到时只根据累计事实更新判断。", "why": "无限等待会增加消耗，明确周期有助于形成决定。"},
    ],
}

_GOAL_QUESTIONS = {
    DecisionGoal.IDENTIFY_OBSTACLES: ["目前最大的阻力，有哪一部分是我可以直接影响的？", "如果只补足一个条件，哪个条件最能改变局面？"],
    DecisionGoal.PLAN_NEXT_STEP: ["哪一步既能带来新信息，又不会让我承担过高成本？", "我会用什么现实反馈决定继续、调整或暂停？"],
    DecisionGoal.PREPARE_COMMUNICATION: ["哪些是我确认过的事实，哪些只是我的推测？", "我希望这次沟通最终得到一个怎样的明确回应？"],
    DecisionGoal.ADJUST_COMMITMENT_BOUNDARIES: ["当前哪一项投入最消耗我，却没有得到相称反馈？", "什么边界能让我继续参与，同时保护自己的稳定？"],
    DecisionGoal.OBSERVE_VERIFY_SIGNALS: ["什么事实出现时，我会愿意更有信心地继续？", "什么事实连续出现时，我需要停止自我说服？"],
}


def _relation_item(assessment: RelationAssessment) -> MentorTextItem:
    phase_label = "起始状态" if assessment.phase is RelationPhase.INITIAL else "变化方向"
    relation_label, explanation = _RELATION_TEXT[assessment.relation]
    strength = {"STRONG": "较强", "MEDIUM": "中等", "WEAK": "较弱"}[assessment.strength.value]
    conditions = "" if not assessment.conditions else f" 需要同时留意：{'；'.join(assessment.conditions)}"
    return {
        "title": f"{phase_label}：{relation_label}",
        "text": f"{explanation} 当前这条关系的规则强度为{strength}。{conditions}",
    }


def build_mentor_report(
    chart: MeihuaChart,
    synthesis: SynthesisResult,
    decision_goal: DecisionGoal,
    time_horizon: TimeHorizon,
) -> MentorReport:
    """Build a safe product explanation from already-computed facts only."""
    stage = MOVING_LINE_STAGE_LABELS_ZH[chart.moving_line_stage]
    body_strength = SEASONAL_STRENGTH_LABELS_ZH[chart.season_context.body_strength]
    horizon = _HORIZON_LABELS[time_horizon]
    reasoning = [_relation_item(item) for item in synthesis.relation_assessments]
    reasoning.append({
        "title": f"承接能力与阶段：体卦{body_strength}、{stage}",
        "text": (
            f"旺衰只用于修正关系强弱，不会把原本的关系方向翻转。动爻位于{stage}，"
            f"因此更适合把{horizon}看作观察和调整的阶段，而不是具体日期预测。"
        ),
    })
    cautions = [
        "卦象提供的是结构化观察角度，不是对未来、他人想法或事件结果的保证。",
        "重要决定请同时核对现实事实、专业意见和你能承受的成本；不要只凭本页作出不可逆选择。",
        "如果现实反馈与这里的结构不一致，应以现实反馈为准，并及时更新行动。",
    ]
    if synthesis.required_conditions:
        cautions.insert(0, f"本次结论依赖的条件：{'；'.join(synthesis.required_conditions)}")
    return {
        "template_version": MENTOR_REPORT_TEMPLATE_VERSION,
        "opening": _OPENING[synthesis.conclusion_level],
        "reading_guide": [
            {"title": f"先看本卦：{chart.base_hexagram.full_name_zh}", "text": "本卦用于呈现问题在起卦时的起始结构，是后续判断的出发点。"},
            {"title": f"再看互卦：{chart.mutual_hexagram.full_name_zh}", "text": "互卦用于辅助观察事情内部如何展开；当前未启用经人工批准的卦义知识，因此不额外推演人物动机。"},
            {"title": f"最后看变卦：{chart.changed_hexagram.full_name_zh}", "text": "变卦呈现动爻变化后的结构，用来比较前后关系是否改变，不代表未来必然走向。"},
        ],
        "reasoning": reasoning,
        "action_plan": [dict(item) for item in _GOAL_ACTIONS[decision_goal]],
        "cautions": cautions,
        "review_questions": list(_GOAL_QUESTIONS[decision_goal]),
        "boundary_note": "以上解释由固定规则和结构化问题自动生成，不使用真实模型，也没有读取你的自由文本、隐私背景或未说明的现实情况。",
    }
