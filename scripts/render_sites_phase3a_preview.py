"""Render a safe static Phase 3A HTML preview from a Contract V1 response."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_response_html(response: dict[str, Any]) -> str:
    result = response.get("deterministic_result") or {}
    gate = response["release_gate"]
    narrative = response["narrative"]
    def hexagram(key: str) -> str:
        item = result.get(key) or {}
        return f"{_text(item.get('symbol', ''))} 第{_text(item.get('king_wen_number', '—'))}卦 · {_text(item.get('name', '—'))}"
    body_use = result.get("body_use") or {}
    elements = result.get("five_elements") or {}
    strengths = result.get("seasonal_strength") or {}
    conclusion = result.get("deterministic_conclusion") or {}
    evidence = result.get("evidence_summary") or {}
    question = response.get("question_text", "仅显示确定性演示结果")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>梅花确定性结果 · Phase 3A本地预览</title><style>
:root{{--ink:#28251f;--muted:#6f695d;--paper:#f6f1e7;--card:#fffdf7;--line:#d8cdb9;--accent:#7a3f2b;--safe:#365c4a}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 system-ui,"Noto Serif SC",serif}}main{{max-width:980px;margin:auto;padding:42px 22px 70px}}header{{border-top:4px solid var(--accent);padding:22px 0 28px}}h1{{font-size:clamp(28px,5vw,46px);margin:.1em 0}}h2{{font-size:20px;margin:0 0 14px}}p{{margin:.45em 0}}.eyebrow{{letter-spacing:.16em;color:var(--accent);font-weight:700}}.muted{{color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:14px}}.hex{{font-size:18px;font-weight:700}}dl{{display:grid;grid-template-columns:160px 1fr;gap:7px 16px;margin:0}}dt{{color:var(--muted)}}dd{{margin:0}}.gate{{border-left:5px solid var(--safe)}}.warning{{border-left:5px solid var(--accent)}}code{{overflow-wrap:anywhere}}@media(max-width:720px){{.grid{{grid-template-columns:1fr}}dl{{grid-template-columns:1fr}}}}
</style></head><body><main><header><div class="eyebrow">SITES-FIRST · OFFLINE PREVIEW</div><h1>梅花确定性结果</h1><p>{_text(question)}</p><p class="muted">输入数字：{_text(', '.join(map(str,result.get('input_numbers',[]))))}</p></header>
<section class="grid"><article class="card"><h2>本卦</h2><div class="hex">{hexagram('base_hexagram')}</div></article><article class="card"><h2>互卦</h2><div class="hex">{hexagram('mutual_hexagram')}</div></article><article class="card"><h2>变卦</h2><div class="hex">{hexagram('changed_hexagram')}</div></article></section>
<section class="card"><h2>程序事实</h2><dl><dt>动爻</dt><dd>{_text(result.get('moving_line','—'))}</dd><dt>体 / 初始用 / 变化用</dt><dd>{_text(body_use.get('body_trigram','—'))} / {_text(body_use.get('initial_use_trigram','—'))} / {_text(body_use.get('changed_use_trigram','—'))}</dd><dt>关系</dt><dd>{_text(body_use.get('initial_relation','—'))} → {_text(body_use.get('changed_relation','—'))}</dd><dt>五行</dt><dd>{_text(elements.get('body','—'))} / {_text(elements.get('initial_use','—'))} / {_text(elements.get('changed_use','—'))}</dd><dt>旺衰</dt><dd>{_text(strengths.get('body','—'))} / {_text(strengths.get('initial_use','—'))} / {_text(strengths.get('changed_use','—'))}</dd></dl></section>
<section class="card"><h2>确定性结论</h2><p>结论等级：<strong>{_text(conclusion.get('conclusion_level','—'))}</strong></p><p>证据充分度：{_text(conclusion.get('evidence_sufficiency','—'))}</p><p class="muted">Evidence摘要：{_text(evidence.get('count',0))}项；类型 {_text(', '.join(evidence.get('evidence_types',[])))}</p></section>
<section class="card warning"><h2>AI解释状态：{_text(narrative['status'])}</h2><p>{_text(narrative['blocked_reason'])}。此页没有Mock Narrative，也不代表正式报告。</p></section>
<section class="card gate"><h2>Release Gate</h2><p>不收费：{_text(not gate['should_charge'])} · 不允许正式保存：{_text(not gate['formal_report_persistence_allowed'])} · 不进入封闭测试：{_text(not gate['closed_beta_allowed'])}</p><p class="muted">确定性计算来源：PYTHON_AUTHORITATIVE_ENGINE</p></section>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    response = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_response_html(response), encoding="utf-8")


if __name__ == "__main__":
    main()
