"""Plain-language V2 clarity report built only from deterministic output.

The free-text question is echoed as the user's subject.  It is never parsed as
evidence and never changes the chart, conclusion, signals, or actions.
"""

from __future__ import annotations

from typing import Any, TypedDict

from .sites_question_context_v1 import DecisionStage, KeyUncertainty

CLARITY_REPORT_VERSION = "SITES_CLARITY_REPORT_V2"


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


_ANSWERS = {
    "CLEARLY_FAVORABLE": "可以推进，但先用小范围行动验证；有利不等于可以省略条件。",
    "CONDITIONALLY_FAVORABLE": "方向可以继续，但必须先补齐关键条件；条件没有出现前，不要扩大投入。",
    "MIXED_OR_UNSETTLED": "现在不适合下最终结论。先暂停加码，用一次低成本验证换取更清楚的事实。",
    "CLEARLY_UNFAVORABLE": "当前更适合收缩、设边界，而不是继续加码；先处理阻力，再决定是否重启。",
    "INSUFFICIENT_EVIDENCE": "现在的信息不足以支持继续或停止。先补一项关键事实，再做决定。",
}

_MEANINGS = {
    "CLEARLY_FAVORABLE": "这不是让你盲目乐观，而是说明当前支持因素相对集中。最好的用法，是顺势做一小步，并让现实结果决定是否扩大。",
    "CONDITIONALLY_FAVORABLE": "卦象给出的不是无条件肯定，而是“满足条件后可行”。此刻最重要的不是更用力，而是确认条件是否真的落地。",
    "MIXED_OR_UNSETTLED": "支持与阻力同时存在，继续猜测不会让局面更清楚。你需要的不是更强的信念，而是一条能被观察到的新事实。",
    "CLEARLY_UNFAVORABLE": "当前结构对你的消耗或约束偏强。先保护资源、降低不可逆成本，比勉强证明自己能坚持更重要。",
    "INSUFFICIENT_EVIDENCE": "卦象本身没有给出足够清晰的方向。把“暂时不知道”当作有效结论，先去补最关键的信息。",
}

_PRIORITIES = {
    "CLEARLY_FAVORABLE": "边推进，边核实",
    "CONDITIONALLY_FAVORABLE": "先看条件是否兑现",
    "MIXED_OR_UNSETTLED": "先换取事实，不急着定性",
    "CLEARLY_UNFAVORABLE": "先止损，再判断",
    "INSUFFICIENT_EVIDENCE": "先补信息，再决定",
}

_RELATION_SIGNAL = {
    "USE_GENERATES_BODY": ("外部开始主动提供资源、回应或实际帮助", "支持停留在口头，迟迟没有资源或行动"),
    "BODY_CONTROLS_USE": ("你能用现有能力把下一步推动到可验收状态", "推进完全依赖你持续加码，且没有形成可复用成果"),
    "SAME_ELEMENT": ("双方节奏、责任与投入逐渐对齐", "互动很多，但责任不清、行动反复"),
    "BODY_GENERATES_USE": ("你的投入换来了对等回应与可见进展", "时间、精力或金钱持续流出，却没有相称反馈"),
    "USE_CONTROLS_BODY": ("外部约束变得明确且可协商", "压力持续增加，你的边界与选择空间不断缩小"),
}

_NEXT_ACTION = {
    KeyUncertainty.CONDITIONS: "写下继续所需的三个最低条件，先验证最关键、成本最低的一项；验证前不追加不可撤回的投入。",
    KeyUncertainty.OTHER_RESPONSE: "向对方提出一个可以明确回答的问题，并约定一种可验收的行动；只根据实际回复和行动更新判断。",
    KeyUncertainty.OWN_COMMITMENT: "列出已经投入的时间、精力和金钱，再写下自己的保留线；先冻结任何超过保留线的新承诺。",
    KeyUncertainty.TIMING: "设一个阶段性复盘点；在到达复盘点前只做可逆动作，不作无法撤回的承诺。",
}

_STAGE_PREFIX = {
    DecisionStage.EXPLORING: "你还在了解阶段，",
    DecisionStage.PREPARING: "你正在准备行动，",
    DecisionStage.ALREADY_ACTING: "你已经在推进，",
    DecisionStage.WAITING_FEEDBACK: "你正在等待反馈，",
}


def build_clarity_report(
    deterministic_result: dict[str, Any],
    stage: DecisionStage,
    uncertainty: KeyUncertainty,
) -> ClarityReport:
    """Translate serialized rule facts into a cautious decision aid."""
    conclusion = deterministic_result["deterministic_conclusion"]
    level = conclusion["conclusion_level"]
    body_use = deterministic_result["body_use"]
    initial_relation = body_use["initial_relation"]
    changed_relation = body_use["changed_relation"]
    initial_continue, initial_pause = _RELATION_SIGNAL[initial_relation]
    changed_continue, changed_pause = _RELATION_SIGNAL[changed_relation]
    conditions = list(conclusion.get("required_conditions") or [])
    continue_signals = [initial_continue, changed_continue]
    pause_signals = [initial_pause, changed_pause]
    if conditions:
        continue_signals.append(f"关键条件得到确认：{conditions[0]}")
        pause_signals.append(f"关键条件仍未得到确认：{conditions[0]}")
    else:
        continue_signals.append("行动后出现了可重复、可核实的正向反馈")
        pause_signals.append("同类阻力连续出现，且成本仍在上升")
    mentor = deterministic_result["mentor_report"]
    reasoning = mentor["reasoning"]
    evidence_path = [
        {"title": "起始关系", "text": reasoning[0]["text"]},
        {"title": "变化方向", "text": reasoning[1]["text"]},
        {"title": "承接能力", "text": reasoning[-1]["text"]},
    ]
    return {
        "template_version": CLARITY_REPORT_VERSION,
        "answer": _ANSWERS[level],
        "what_it_means": _MEANINGS[level],
        "priority": _PRIORITIES[level],
        "continue_signals": continue_signals,
        "pause_signals": pause_signals,
        "next_action": f"{_STAGE_PREFIX[stage]}{_NEXT_ACTION[uncertainty]}",
        "evidence_path": evidence_path,
        "boundary_note": "以上方向只来自确定性卦象结构与本次结构化选择。你的问题原文仅用于确认所问与呈现结果，不参与排盘，也不被当作卦象证据。",
    }
