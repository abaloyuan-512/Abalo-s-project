"""Print the fixed Phase 1 demonstration chart; never calls OpenAI."""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from abalo_iching.meihua import MeihuaInput, cast_meihua, chart_to_dict  # noqa: E402
from abalo_iching.meihua.enums import RELATION_LABELS_ZH, SEASONAL_STRENGTH_LABELS_ZH  # noqa: E402


def main() -> None:
    chart_input = MeihuaInput(
        first_number=100,
        second_number=27,
        third_number=368,
        cast_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone_name="Asia/Shanghai",
        question_id="phase1-demo",
    )
    chart = cast_meihua(chart_input)
    print("=== Meihua Engine Phase 1 Demo ===")
    print(f"输入: {chart.input.first_number}, {chart.input.second_number}, {chart.input.third_number}")
    print(f"上卦/下卦: {chart.upper_trigram.name_zh} / {chart.lower_trigram.name_zh}")
    print(f"本卦: 第{chart.base_hexagram.king_wen_number}卦 {chart.base_hexagram.full_name_zh}")
    print(f"动爻: {chart.moving_line}")
    print(f"互卦: 第{chart.mutual_hexagram.king_wen_number}卦 {chart.mutual_hexagram.full_name_zh}")
    print(f"变卦: 第{chart.changed_hexagram.king_wen_number}卦 {chart.changed_hexagram.full_name_zh}")
    print(f"体/初始用: {chart.body_trigram.name_zh} / {chart.initial_use_trigram.name_zh}")
    print(f"初始关系: {RELATION_LABELS_ZH[chart.initial_body_use_relation]}")
    print(f"变化后用: {chart.changed_use_trigram.name_zh}")
    print(f"变化后关系: {RELATION_LABELS_ZH[chart.changed_body_use_relation]}")
    print(f"当前节气/月令: {chart.season_context.current_solar_term} / {chart.season_context.month_branch}月")
    print(
        "体/初始用/变化后用旺衰: "
        f"{SEASONAL_STRENGTH_LABELS_ZH[chart.season_context.body_strength]} / "
        f"{SEASONAL_STRENGTH_LABELS_ZH[chart.season_context.initial_use_strength]} / "
        f"{SEASONAL_STRENGTH_LABELS_ZH[chart.season_context.changed_use_strength]}"
    )
    print("=== Structured JSON ===")
    print(json.dumps(chart_to_dict(chart), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
