"""Opt-in wording experiment; never changes chart rules or the frozen default."""

from __future__ import annotations

import hashlib
import json

from abalo_iching.application.sites_direct_reading_v3 import (
    DirectReadingPreparedRequest,
    SYSTEM_PROMPT,
)

PROMPT_SUFFIX = "_CONCISE_SPEED_V1"
READING_PROFILE = "concise-medium-v1"
_OLD_STYLE = (
    "使用自然、有传统文化气息的中文；完整优先，避免在不同章节重复同一解释，全文控制在约1800至2600汉字内。"
)
_NEW_STYLE = (
    "使用自然、易懂的中文，少用生涩术语，不写开场白或套话。九章正文合计约1000至1400汉字，"
    "完整优先，不得省略任何指定章节或卦象依据。判断章先直接回答用户的问题和成立条件；"
    "本卦、互卦、动爻、变卦各解释一个不同的关键点，并明确它与所问的联系，"
    "不要在各章重复总判断。行动建议尽量具体到下一步，但不得编造现实背景。"
    "避免把卦义换几种说法反复讲述，不重复用户问题，不用空泛鼓励凑字数。"
    "保留原有标题、准确的动爻爻辞和最后两句观象寄语。"
)


def prepare_concise_reading(
    prepared: DirectReadingPreparedRequest,
) -> DirectReadingPreparedRequest:
    """Copy a prepared request, preserving facts, context, and release gates."""
    if prepared.prompt_version.endswith(PROMPT_SUFFIX):
        return prepared
    if _OLD_STYLE not in SYSTEM_PROMPT or _OLD_STYLE not in prepared.system_prompt:
        raise ValueError("baseline prompt changed; revalidate the speed profile")
    system_prompt = prepared.system_prompt.replace(_OLD_STYLE, _NEW_STYLE, 1)
    prompt_json = json.dumps(
        [system_prompt, prepared.user_prompt],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return prepared.model_copy(update={
        "system_prompt": system_prompt,
        "prompt_version": prepared.prompt_version + PROMPT_SUFFIX,
        "prompt_sha256": hashlib.sha256(prompt_json.encode("utf-8")).hexdigest().upper(),
    })
