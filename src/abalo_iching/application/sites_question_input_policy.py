"""Deterministic P0 question-input guard for the Sites Meihua adapter."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuestionInputDecision:
    allowed: bool
    error_code: str | None = None
    message: str | None = None


_ALLOW = QuestionInputDecision(allowed=True)
_SEPARATORS = re.compile(r"[\s,，。.!！?？;；:：、…'\"“”‘’()（）\[\]【】<>《》—_\-/]+")

_IMMEDIATE_SAFETY = (
    re.compile(r"(?:不想活|不想继续活|想死|自杀|自伤|结束生命|伤害自己)"),
    re.compile(r"(?:跳楼|从[^，。]{0,12}跳下去|跳下去会发生什么)"),
    re.compile(r"(?:想|准备|打算|要).{0,12}(?:杀|伤害|袭击|报复)(?:他|她|别人|某人|家人|同事)"),
    re.compile(
        r"(?:(?:我|他|她|家人|伴侣)(?:遭遇|受到|被).{0,8}(?:家暴|控制|跟踪|威胁)|"
        r"(?:我|他|她|家人|伴侣)(?:正在|现在)(?!研究|分析|撰写).{0,8}(?:家暴|控制|跟踪|威胁))"
    ),
    re.compile(r"(?:把我锁|把我关|被锁|被关|拘禁|无法离开)"),
    re.compile(r"(?:有人|他|她|对方).*(?:现在|马上|今晚).*(?:杀我|伤害我|袭击我|绑架我)"),
    re.compile(r"(?:失踪|走失).*(?:位置|在哪|活着|生死|归期|什么时候回来)"),
    re.compile(r"(?:等|看完|算完).*(?:卦|预测|结果)?.*(?:再|才).*(?:报警|求助|就医|离开|决定怎么办)"),
)

_SAFE_REDIRECTIONS = (
    re.compile(r"^(?:我)?不想问(?:他|她|对方).*(?:爱不爱我|心里有没有我)(?:我想知道|只想知道)(?:我|自己)?(?:应|应该)?(?:如何|怎样)(?:沟通|行动)$"),
    re.compile(r"^(?:我)?不想判断(?:他|她|对方).*(?:是否|是不是|有没有)(?:出轨|欺骗|隐瞒).*(?:我想|只想).*(?:整理|核实).*(?:现实信息|事实|信号)$"),
    re.compile(r"^(?:他|她|对方).*爱不爱我不重要(?:我想知道|只想知道)(?:我|自己)?(?:应|应该)?(?:如何|怎样)(?:沟通|行动)$"),
    re.compile(r"^(?:我)?不要求保证(?:成功)?(?:我)?只想(?:观察|核实|了解).*(?:阻力|条件|信号)$"),
    re.compile(r"^(?:这)?不是股票投资(?:我)?问的是(?:团队|商业|项目).*(?:合作|安排|条件)$"),
    re.compile(r"^(?:我)?不会自行(?:停药|停止服药|停止用药)(?:我)?想(?:整理|准备).*(?:咨询|询问|看)医生.*(?:问题|说明|材料)$"),
)

_MEDICAL_OBJECT = re.compile(r"手术|开刀|检查|药|药量|剂量|治疗|怀孕|阳性|疾病|病情|症状|胎儿")
_MEDICAL_TARGET = re.compile(
    r"顺利|成功|结果|阳性|停药|停止服药|停止用药|减一半|减量|加量|加药|减药|换药|"
    r"调整剂量|治好|治愈|有效|诊断|确诊|是否怀孕|是不是怀孕|有没有怀孕|安全不安全|安全吗"
)

_FINANCIAL_ASSET = re.compile(r"股票|基金|期货|外汇|加密货币|虚拟货币|比特币|以太坊|币圈|证券|黄金")
_FINANCIAL_ACTION = re.compile(
    r"涨|跌|买入|买|卖出|卖|做多|做空|加仓|减仓|补仓|清仓|杠杆|上车|梭哈|"
    r"交易时点|入场|止损|赚钱|收益|回本|回血|翻倍"
)
_STRONG_FINANCIAL_INTENT = re.compile(r"(?:梭哈|满仓).*(?:进去|买入|回本|回血|赚钱|翻倍)")

_GAMBLING = (
    re.compile(r"(?:彩票|双色球|大乐透|六合彩).*(?:号码|哪些号|选号|中奖|开奖|买什么|选什么)"),
    re.compile(r"(?:体育博彩|赌球|赛马|下注|赌博|押).*(?:输赢|稳不稳|哪一边|赢|回本|追损|翻本)"),
    re.compile(r"(?:主队|客队).*(?:稳不稳|下注|押|赢)"),
    re.compile(r"(?:抽卡|抽奖|盲盒).*(?:几点|什么时候|容易|出货|中奖|结果|号码|回本)"),
)

_LEGAL_OR_CRIME = (
    re.compile(r"(?:法院|官司|诉讼|仲裁|判决|刑期|量刑).*(?:结果|输赢|赢|会判|判多久|几年)"),
    re.compile(r"(?:警方|警察|调查人员|执法人员).*(?:几号|哪天|几点|什么时候|何时).*(?:来|找我|调查|抓)"),
    re.compile(r"(?:聊天记录|证据|赃物|材料|证件|合同|证明|记录).*(?:删除|删|销毁|藏匿|转移|伪造|制作假|查不到|不被发现|被发现)"),
    re.compile(r"(?:删除|删|销毁|藏匿|转移|伪造|制作假).*(?:聊天记录|证据|赃物|材料|证件|合同|证明|记录)"),
    re.compile(r"(?:规避|躲避|逃避)(?:调查|侦查|警方|警察|执法|追查)"),
    re.compile(r"(?:违法|犯罪|作案|诈骗|偷窃).*(?:成功|会不会被发现|如何不被发现|避免被发现)"),
)

_THIRD_PARTY_SUBJECT = re.compile(r"他|她|对方|老板|公司|供应商|面试官|伴侣|某人")
_THIRD_PARTY_JUDGMENT = re.compile(r"是不是|是否|有没有|到底|爱不爱|想不想|已经决定|故意|心里")
_THIRD_PARTY_FACT = re.compile(r"爱|不爱|有我|没有我|有人|讨厌|优化掉|裁掉|骗|欺骗|出轨|不录用|拒绝录用|隐瞒|秘密")

_TIME_QUERY = re.compile(r"几号|哪天|哪一天|几点|什么时候|何时")
_SPECIFIC_TIME = re.compile(r"下周[一二三四五六日天]|月底前|月末前|\d{1,2}月\d{1,2}[日号]|(?:[一二两三四五六七八九十]|\d+)(?:天|日|小时)内")
_RESULT_TARGET = re.compile(r"收到.*(?:offer|录用|通知)|签约|复合|成功|发生|回来|录用|有结果|开奖|来找我")
_CERTAINTY = re.compile(r"一定|肯定|百分百|百分之百|100%|保证|注定|命中注定|必然|绝对不会失败")


def _detection_copy(question_text: str) -> str:
    normalized = unicodedata.normalize("NFKC", question_text).lower()
    return _SEPARATORS.sub("", normalized)


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) is not None for pattern in patterns)


def _is_safe_redirection(text: str) -> bool:
    return any(pattern.fullmatch(text) is not None for pattern in _SAFE_REDIRECTIONS)


def evaluate_question_input(question_text: str) -> QuestionInputDecision:
    """Return a high-confidence P0 decision without retaining or mutating input."""
    text = _detection_copy(question_text)

    if _matches_any(text, _IMMEDIATE_SAFETY):
        return QuestionInputDecision(
            False,
            "IMMEDIATE_SAFETY_RISK",
            "请不要等待预测结果。如存在迫近危险，请立即联系当地紧急服务，并尽快联系可信任的人或合适的专业支持。",
        )
    if _is_safe_redirection(text):
        return _ALLOW
    if _MEDICAL_OBJECT.search(text) and _MEDICAL_TARGET.search(text):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_HIGH_RISK_REQUEST",
            "这个问题需要由合适的医疗专业人员根据现实信息判断，本服务不会提供诊断、治疗或用药结论。",
        )
    if (
        _FINANCIAL_ASSET.search(text) and _FINANCIAL_ACTION.search(text)
    ) or _STRONG_FINANCIAL_INTENT.search(text):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_HIGH_RISK_REQUEST",
            "本服务不提供金融交易、具体标的或收益预测。请依据可靠信息并咨询具备资质的专业人士。",
        )
    if _matches_any(text, _GAMBLING):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_HIGH_RISK_REQUEST",
            "本服务不提供赌博、博彩、彩票或带真实利益抽奖的结果预测。",
        )
    if _matches_any(text, _LEGAL_OR_CRIME):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_HIGH_RISK_REQUEST",
            "本服务不预测法律结果，也不协助违法或规避执法。法律问题请依据事实咨询合适的专业人士。",
        )
    if (
        _THIRD_PARTY_SUBJECT.search(text)
        and _THIRD_PARTY_JUDGMENT.search(text)
        and _THIRD_PARTY_FACT.search(text)
    ):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_THIRD_PARTY_INFERENCE",
            "本服务不能判断他人的内心、隐私或未核实事实。请改为关注自己的行动、边界和可观察信号。",
        )
    if (
        _TIME_QUERY.search(text) and _RESULT_TARGET.search(text)
    ) or (
        _SPECIFIC_TIME.search(text) and _CERTAINTY.search(text) and _RESULT_TARGET.search(text)
    ) or (
        _CERTAINTY.search(text) and _RESULT_TARGET.search(text)
    ) or re.search(r"(?:命中注定|这是注定的|是否注定)", text):
        return QuestionInputDecision(
            False,
            "UNSUPPORTED_PREDICTION_REQUEST",
            "本服务不提供具体日期、时刻、保证或宿命式结果。请改为询问当前条件、行动或观察信号。",
        )
    return _ALLOW
