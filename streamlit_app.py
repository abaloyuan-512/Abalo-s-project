#!/usr/bin/env python3
"""Streamlit 版 AI 易经梅花数理排盘系统。"""

import os
from typing import Generator

import streamlit as st
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

GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def mod_to_trigram(number: int) -> str:
    return TRIGRAM_BY_INDEX[number % 8]


def relation_between(body_element: str, use_element: str) -> str:
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


def stream_llm_divination(prompt: str, api_key: str) -> Generator[str, None, None]:
    model = os.getenv("ICHING_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)
    stream = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "你是严谨、务实、避免套话的中文易学分析助手。"},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta


def main() -> None:
    st.set_page_config(page_title="AI 易经梅花数理排盘系统", page_icon="☯️", layout="centered")
    st.title("☯️ AI 易经梅花数理排盘系统")
    st.markdown(
        """
        <div style="background:linear-gradient(120deg,#f7f1e3,#fffaf0);padding:14px 16px;border-radius:12px;border:1px solid #e8dcc8;">
        这是一个结合了<strong>梅花数理</strong>与现代大模型（<strong>GPT-4o/GPT-5</strong>）的深度智能化解卦工具。<br>
        请输入卦象参数与所求之事，系统将先完成本地排盘，再进行 AI 流式解卦。
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        upper_num = st.number_input("上卦数字", min_value=1, value=9, step=1)
    with col2:
        lower_num = st.number_input("下卦数字", min_value=1, value=10, step=1)
    with col3:
        moving_line = st.number_input("动爻（1-6）", min_value=1, max_value=6, value=2, step=1)

    question = st.text_area("请输入你当前心中所求之事", placeholder="例如：我最近是否适合换工作？", height=110)

    api_key = st.text_input(
        "OpenAI API Key（未填则尝试读取环境变量 OPENAI_API_KEY）",
        type="password",
        placeholder="sk-...",
    )

    if st.button("开始排盘并起卦", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("请先输入“心中所求之事”，再开始排盘。")
            return

        upper_trigram = mod_to_trigram(int(upper_num))
        lower_trigram = mod_to_trigram(int(lower_num))

        if 1 <= int(moving_line) <= 3:
            body_trigram, use_trigram = upper_trigram, lower_trigram
        else:
            body_trigram, use_trigram = lower_trigram, upper_trigram

        body_element = FIVE_ELEMENTS[body_trigram]
        use_element = FIVE_ELEMENTS[use_trigram]
        relation = relation_between(body_element, use_element)

        st.success("排盘成功！以下是本卦与体用分析结果：")
        st.info(
            f"本卦上卦：{upper_trigram}｜本卦下卦：{lower_trigram}\n\n"
            f"体卦：{body_trigram}（{body_element}）｜用卦：{use_trigram}（{use_element}）\n\n"
            f"体用关系：{relation}"
        )

        prompt = build_divination_prompt(
            question=question.strip(),
            upper_trigram=upper_trigram,
            lower_trigram=lower_trigram,
            body_trigram=body_trigram,
            use_trigram=use_trigram,
            body_element=body_element,
            use_element=use_element,
            relation=relation,
        )

        effective_key = api_key.strip() or os.getenv("OPENAI_API_KEY", "")
        if not effective_key:
            st.error("未检测到 API Key。请在页面输入，或在环境变量中配置 OPENAI_API_KEY 后重试。")
            return

        st.markdown("### 🤖 AI 流式解卦")
        with st.container(border=True):
            try:
                st.write_stream(stream_llm_divination(prompt, effective_key))
            except Exception as exc:
                st.error(f"调用大模型失败：{exc}")


if __name__ == "__main__":
    main()
