#!/usr/bin/env python3
"""简易梅花易数起卦工具：根据三个数字计算上下卦、体用与生克关系，并调用大模型解卦。"""

import os

from openai import OpenAI

TRIGRAM_BY_INDEX = {
    1: "乾",
    2: "兑",
    3: "离",
    4: "震",
    5: "巽",
    6: "坎",
    7: "艮",
    0: "坤",  # 余数为 0 视为 8，即坤
}

FIVE_ELEMENTS = {
    "乾": "金",
    "兑": "金",
    "离": "火",
    "震": "木",
    "巽": "木",
    "坎": "水",
    "艮": "土",
    "坤": "土",
}

# 五行相生（键生值）
GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

# 五行相克（键克值）
CONTROLS = {
    "木": "土",
    "土": "水",
    "水": "火",
    "火": "金",
    "金": "木",
}


def mod_to_trigram(number: int) -> str:
    """按“1 模 8 为乾...0 为坤”的规则返回八卦名。"""
    return TRIGRAM_BY_INDEX[number % 8]


def relation_between(body_element: str, use_element: str) -> str:
    """判断体用五行关系：比和/生/克。"""
    if body_element == use_element:
        return "比和"

    if GENERATES[body_element] == use_element:
        return "生（体生用）"
    if GENERATES[use_element] == body_element:
        return "生（用生体）"

    if CONTROLS[body_element] == use_element:
        return "克（体克用）"
    if CONTROLS[use_element] == body_element:
        return "克（用克体）"

    return "关系未定义"


def build_divination_prompt(
    question: str,
    upper_trigram: str,
    lower_trigram: str,
    body_trigram: str,
    use_trigram: str,
    body_element: str,
    use_element: str,
    relation: str,
) -> str:
    """组合结构化解卦提示词。"""
    return f"""
你是一位擅长梅花易数与体用生克分析的专业解卦顾问。

请严格根据以下已知信息解读，必须一事一议，聚焦用户当前问题：
- 用户所求之事：{question}
- 本卦上卦：{upper_trigram}
- 本卦下卦：{lower_trigram}
- 体卦：{body_trigram}（五行：{body_element}）
- 用卦：{use_trigram}（五行：{use_element}）
- 体用关系：{relation}

输出要求：
1) 先给【结论】（2-3句，明确吉凶倾向与核心判断）。
2) 再给【推理】（结合体用生克旺衰、主客关系，解释原因）。
3) 再给【行动建议】（3条以内、可执行，紧扣用户问题）。
4) 再给【时间与风险提示】（指出短期观察点、潜在风险与转机条件）。

禁止：
- 空泛套话
- 机械重复输入信息
- 与用户问题无关的泛化内容
""".strip()


def stream_llm_divination(prompt: str) -> None:
    """调用大模型接口并流式打印解卦结果。"""
    model = os.getenv("ICHING_MODEL", "gpt-4o-mini")
    client = OpenAI()

    stream = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "你是严谨、务实、避免套话的中文易学分析助手。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=True,
    )

    print("\n=== 大模型解卦分析 ===")
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
    print()


def main() -> None:
    print("请输入三个整数：上卦数、下卦数、动爻（1-6）")

    upper_num = int(input("上卦数：").strip())
    lower_num = int(input("下卦数：").strip())
    moving_line = int(input("动爻：").strip())
    question = input("请输入你当前心中所求之事：").strip()

    upper_trigram = mod_to_trigram(upper_num)
    lower_trigram = mod_to_trigram(lower_num)

    # 动爻 1-3 在下卦，4-6 在上卦
    if 1 <= moving_line <= 3:
        body_trigram = upper_trigram
        use_trigram = lower_trigram
    elif 4 <= moving_line <= 6:
        body_trigram = lower_trigram
        use_trigram = upper_trigram
    else:
        raise ValueError("动爻必须在 1 到 6 之间")

    body_element = FIVE_ELEMENTS[body_trigram]
    use_element = FIVE_ELEMENTS[use_trigram]
    relation = relation_between(body_element, use_element)

    print("\n=== 起卦结果 ===")
    print(f"本卦上卦：{upper_trigram}")
    print(f"本卦下卦：{lower_trigram}")
    print(f"体卦：{body_trigram}（{body_element}）")
    print(f"用卦：{use_trigram}（{use_element}）")
    print(f"体用关系：{relation}")

    prompt = build_divination_prompt(
        question,
        upper_trigram,
        lower_trigram,
        body_trigram,
        use_trigram,
        body_element,
        use_element,
        relation,
    )
    stream_llm_divination(prompt)


if __name__ == "__main__":
    main()
