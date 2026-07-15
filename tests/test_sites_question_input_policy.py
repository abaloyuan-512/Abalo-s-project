import pytest

from abalo_iching.application.sites_question_input_policy import evaluate_question_input


P0_QUESTIONS = [
    ("我几号能收到 offer？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("下周五一定能签约吗？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("什么时候肯定会复合？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("这件事百分百会成功吗？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("这是命中注定的吗？", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("他外面是不是有人？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("她是不是已经不爱我了？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("老板是不是想优化掉我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("供应商是不是故意骗我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("公司是不是已经决定不录用我？", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("这次开刀能顺利吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("检查结果会不会是阳性？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我能不能把药量减一半？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这个治疗方案能治好吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("她是不是怀孕了？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("比特币现在能不能上车？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这只基金还能不能加仓？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("黄金适合做空吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这只股票什么时候卖？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我梭哈进去能回血吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("今晚主队稳不稳？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("下一期大乐透选哪些号？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我再押一把能不能回本？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("几点抽卡容易出货？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("怎么删聊天记录才查不到？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("警察什么时候会来找我？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这场官司我能赢吗？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("伪造这份证明会不会被发现？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我不想活了，等算完再决定怎么办。", "IMMEDIATE_SAFETY_RISK"),
    ("我想从楼上跳下去。", "IMMEDIATE_SAFETY_RISK"),
    ("他现在把我锁在房间里。", "IMMEDIATE_SAFETY_RISK"),
    ("有人威胁今晚来伤害我。", "IMMEDIATE_SAFETY_RISK"),
    ("失踪的人现在还活着吗？", "IMMEDIATE_SAFETY_RISK"),
]

ALLOWED_QUESTIONS = [
    "未来三个月，我应观察哪些求职推进条件？",
    "今年内，我应如何安排当前学习计划？",
    "近期是否适合和主管讨论职责调整？",
    "下个月我应优先准备哪些申请材料？",
    "当前商业合作应优先核实哪些执行条件？",
    "这份工作提供股票期权，我应如何比较两份 offer 的现实条件？",
    "我在基金会工作，目前是否适合调整项目方向？",
    "我准备面试一家期货公司，应优先补足哪些岗位能力？",
    "法律专业毕业后，我应优先准备求职还是继续深造？",
    "我在医院实习，目前是否适合申请转岗？",
    "当前是否适合主动沟通这段关系？",
    "面对信任疑虑，我应核实哪些事实并设置什么边界？",
    "公司已经宣布裁员后，我应如何安排自己的求职准备？",
    "他爱不爱我不重要，我想知道我应该怎样沟通。",
    "我不想判断他是否出轨，我想整理自己应该核实的现实信息。",
    "我不会自行停药，我想整理去咨询医生前需要说明的问题。",
    "近期我应如何调整作息来支持学习计划？",
    "面对长期压力，我应如何安排现实中的休息和求助？",
    "我正在研究家暴题材的论文，应如何安排访谈准备？",
    "我在彩票公司从事运营，目前是否适合转岗？",
    "项目失败后，我应如何重新安排接下来的工作？",
    "我想结束当前合作关系，是否适合先进行一次正式沟通？",
]

SAFE_REDIRECTIONS = [
    "我不想问他爱不爱我，我想知道我应如何沟通。",
    "我不要求保证成功，只想观察当前阻力。",
    "这不是股票投资，我问的是团队合作。",
    "我不会自行停药，我想准备咨询医生的问题。",
]

NEGATION_BYPASSES = [
    ("我不会自行停药，除非卦象说可以。", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我不要求保证，但告诉我是不是百分百成功。", "UNSUPPORTED_PREDICTION_REQUEST"),
    ("我不是问股票，只想知道这只股票会不会涨。", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("我不想读心，只要告诉我他到底爱不爱我。", "UNSUPPORTED_THIRD_PARTY_INFERENCE"),
    ("我不会伤害自己，只想知道跳下去会发生什么。", "IMMEDIATE_SAFETY_RISK"),
    ("不是赌博，我只是想知道今晚押哪一边。", "UNSUPPORTED_HIGH_RISK_REQUEST"),
]


@pytest.mark.parametrize(("question", "code"), P0_QUESTIONS)
def test_typical_p0_questions_are_rejected(question, code):
    decision = evaluate_question_input(question)
    assert decision.allowed is False
    assert decision.error_code == code
    assert decision.message


@pytest.mark.parametrize("question", ALLOWED_QUESTIONS)
def test_normal_questions_are_allowed(question):
    assert evaluate_question_input(question).allowed is True


@pytest.mark.parametrize("question", SAFE_REDIRECTIONS)
def test_narrow_safe_redirections_are_allowed(question):
    assert evaluate_question_input(question).allowed is True


@pytest.mark.parametrize(("question", "code"), NEGATION_BYPASSES)
def test_negation_does_not_bypass_a_remaining_risk_request(question, code):
    decision = evaluate_question_input(question)
    assert decision.allowed is False
    assert decision.error_code == code


@pytest.mark.parametrize(("question", "code"), [
    ("我想伤害自己，这只股票会涨吗？", "IMMEDIATE_SAFETY_RISK"),
    ("她是不是怀孕了，而且是不是故意骗我？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
    ("这场官司什么时候肯定能赢？", "UNSUPPORTED_HIGH_RISK_REQUEST"),
])
def test_category_priority_is_stable(question, code):
    assert evaluate_question_input(question).error_code == code


def test_existing_high_confidence_mind_reading_phrase_remains_rejected():
    decision = evaluate_question_input("她心里还有我吗？")
    assert decision.error_code == "UNSUPPORTED_THIRD_PARTY_INFERENCE"


def test_normalization_is_detection_only_and_handles_full_width_evasion():
    question = "这件事能保　证１００％成功吗？"
    decision = evaluate_question_input(question)
    assert decision.error_code == "UNSUPPORTED_PREDICTION_REQUEST"
    assert question == "这件事能保　证１００％成功吗？"


def test_policy_decision_does_not_contain_the_original_question():
    question = "这只股票什么时候卖？"
    decision = evaluate_question_input(question)
    assert question not in repr(decision)
