from __future__ import annotations

import hashlib
import json

from .models import Gate2ExperimentRequest, Gate2PromptPackage
from .prompt_builder import Gate2PromptBuilder


CALIBRATION_PROMPT_VERSION = "personalization_gate2_calibration_v3"

CALIBRATION_ADDITIONAL_INSTRUCTIONS = """
阶段 C 结构约束补充：
1. unknowns 必须逐字、逐项完整复制输入 reality_context.unknowns，不得增加、删除或改写。
2. 输出任何位置实际使用的每个 RWxx，都必须在 source_trace 中有且只有一个同编号 REALITY_FACT 项；每个 EVxx 同理必须有同编号 CHART_FACT 项。
3. REALITY_FACT 与 CHART_FACT 的 supports_fields 必须指向该事实实际支撑的字段；不得用解释性 ILxx 冒充事实来源。
4. B 组所有 ILxx 必须为 REALITY_ONLY；C/D 组所有 ILxx 必须为 REALITY_AND_CHART。
5. judgment_signature 五字段与 user_facing_reading 五字段必须全部出现在至少一个 ILxx 的 supports_fields 中。
6. 不确定信息只能放入 unknowns，不得转写成已发生事实、第三方想法或结果保证。
""".strip()


class Gate2CalibrationPromptBuilder(Gate2PromptBuilder):
    """阶段 C 专用 Prompt；不改变阶段 A/B 与正式解释 Prompt。"""

    version = CALIBRATION_PROMPT_VERSION

    def build(self, request: Gate2ExperimentRequest) -> Gate2PromptPackage:
        base = super().build(request)
        system_instructions = (
            f"{base.system_instructions}\n\n{CALIBRATION_ADDITIONAL_INSTRUCTIONS}"
        )
        payload_text = json.dumps(
            base.input_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        prompt_sha256 = hashlib.sha256(
            f"{system_instructions}\n{payload_text}".encode("utf-8")
        ).hexdigest()
        return Gate2PromptPackage(
            prompt_version=self.version,
            system_instructions=system_instructions,
            input_payload=base.input_payload,
            prompt_sha256=prompt_sha256,
        )
