from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from abalo_iching.application.sites_cultural_reading_v1 import (
    _PLAIN_RELATION_LABELS,
    _PLAIN_STRENGTH_LABELS,
    _RELATION_EFFECTS,
    _STRENGTH_MEANINGS,
)
from abalo_iching.meihua.calendar_provider import LunarPythonCalendarProvider
from abalo_iching.meihua.relations import relation_between_body_and_use
from abalo_iching.meihua.seasonal_strength import seasonal_strength_for
from abalo_iching.meihua.trigrams import trigram_from_name


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "outputs" / "v008_canary_real_result.json"
PAGE_PATH = ROOT / "outputs" / "v008_canary_page8_page9.md"
PROVENANCE_PATH = ROOT / "outputs" / "v008_canary_provenance.json"
TAIL_HEADINGS = [
    "判断",
    "适合做什么",
    "不适合做什么",
    "反向风险",
    "哪些现实信号会改变判断",
]


def _parse(text: str) -> dict[str, str]:
    parts = [part for part in re.split(r"(?=^## )", text, flags=re.MULTILINE) if part]
    return {part.splitlines()[0].removeprefix("## ").strip(): part.rstrip() for part in parts}


def main() -> int:
    evidence = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if evidence["status"] != "SUCCESS" or evidence["validation_errors"]:
        raise RuntimeError("V008_CANARY_NOT_RELEASABLE")
    reading = evidence["direct_reading"]["text"]
    facts = evidence["chart_facts"]
    base, mutual, moving, changed = (
        facts["base_hexagram"],
        facts["mutual_hexagram"],
        facts["moving_line"],
        facts["changed_hexagram"],
    )
    expected = [
        "判断",
        f"本卦：{base['name']}",
        f"互卦：{mutual['name']}",
        f"动爻：{moving['name']}",
        f"变卦：{changed['name']}",
        *TAIL_HEADINGS[1:],
    ]
    parsed = _parse(reading)
    if list(parsed) != expected:
        raise RuntimeError(f"V008_SECTION_MISMATCH:{list(parsed)!r}")

    if moving["position"] <= 3:
        body_name, initial_use_name, changed_use_name = (
            base["upper_trigram"], base["lower_trigram"], changed["lower_trigram"]
        )
    else:
        body_name, initial_use_name, changed_use_name = (
            base["lower_trigram"], base["upper_trigram"], changed["upper_trigram"]
        )
    body = trigram_from_name(body_name)
    initial_use = trigram_from_name(initial_use_name)
    changed_use = trigram_from_name(changed_use_name)
    initial_relation = relation_between_body_and_use(body.element, initial_use.element)
    changed_relation = relation_between_body_and_use(body.element, changed_use.element)
    generated_at = datetime.fromisoformat(evidence["audit"]["generated_at"])
    calendar = LunarPythonCalendarProvider().get_calendar_snapshot(generated_at, "Asia/Shanghai")
    body_strength = seasonal_strength_for(body.element, calendar.month_element)

    source_sha = hashlib.sha256(reading.encode("utf-8")).hexdigest().upper()
    reconstructed = "\n\n".join(parsed[heading] for heading in expected)
    reconstructed_sha = hashlib.sha256(reconstructed.encode("utf-8")).hexdigest().upper()
    if source_sha != reconstructed_sha or source_sha != evidence["reading_utf8_sha256"]:
        raise RuntimeError("V008_RECONSTRUCTION_HASH_MISMATCH")

    page = [
        "# V008 真实 OpenAI high Canary：第八页与第九页",
        "",
        f"> 原问题：{evidence['input']['question_text']}",
        f"> 三数：{'、'.join(str(value) for value in evidence['input']['numbers'])}",
        "> 状态：SUCCESS；正文按标题机械分发，未摘要、未改写、未二次生成。",
        "",
        "# 第八页：观象五幕",
        "",
    ]
    labels = [
        f"第一幕：本卦｜{base['name']}",
        f"第二幕：互卦｜{mutual['name']}",
        f"第三幕：动爻｜{moving['name']}",
        f"第四幕：变卦｜{changed['name']}",
    ]
    for label, heading in zip(labels, expected[1:5], strict=True):
        page.extend([f"## {label}", "", parsed[heading].split("\n\n", 1)[1], ""])
    page.extend(
        [
            "## 第五幕：旺衰",
            "",
            f"**程序事实**：体卦为{body_name}，初始用卦为{initial_use_name}，变化后用卦为{changed_use_name}。",
            "",
            f"**体用关系**：开始时为{_PLAIN_RELATION_LABELS[initial_relation]}；变化后为{_PLAIN_RELATION_LABELS[changed_relation]}。",
            "",
            f"**旺衰**：体卦为{_PLAIN_STRENGTH_LABELS[body_strength]}。",
            "",
            f"**固定文化解释**：开始时，{_RELATION_EFFECTS[initial_relation]} 变化后，{_RELATION_EFFECTS[changed_relation]} {_STRENGTH_MEANINGS[body_strength]}",
            "",
            "> 本幕只使用程序盘面、体用关系和旺衰规则，不属于模型正文，也不承载综合判断。",
            "",
            "# 第九页：综合决策",
            "",
        ]
    )
    for heading in TAIL_HEADINGS:
        page.extend([parsed[heading], ""])
    page.extend(
        [
            "---",
            "",
            f"模型正文 SHA-256：`{source_sha}`",
            f"按原九章顺序重建 SHA-256：`{reconstructed_sha}`",
        ]
    )
    PAGE_PATH.write_text("\n".join(page).rstrip() + "\n", encoding="utf-8")
    provenance = {
        "case_id": evidence["case_id"],
        "status": "SUCCESS",
        "input": evidence["input"],
        "call_ledger": evidence["call_ledger"],
        "chart_facts": facts,
        "program_strength": {
            "calendar_provider": calendar.provider_version,
            "body_trigram": body_name,
            "initial_use_trigram": initial_use_name,
            "changed_use_trigram": changed_use_name,
            "initial_relation": initial_relation.value,
            "changed_relation": changed_relation.value,
            "body_strength": body_strength.value,
            "additional_casts": 0,
        },
        "source_reading_utf8_sha256": source_sha,
        "reconstructed_reading_utf8_sha256": reconstructed_sha,
        "reconstructed_equals_source": reading == reconstructed,
        "model_calls_for_render": 0,
        "page_path": str(PAGE_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    PROVENANCE_PATH.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"case_id": evidence["case_id"], "reading_sha256": source_sha}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

