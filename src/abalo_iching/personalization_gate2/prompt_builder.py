from __future__ import annotations

import hashlib
import json

from .models import ExperimentArm, Gate2ExperimentRequest, Gate2PromptPackage


PROMPT_VERSION = "personalization_gate2_offline_v2"

SYSTEM_INSTRUCTIONS = """你正在执行观象 Gate 2 离线合成案例实验。
只使用输入中列出的现实事实与允许的卦象 Evidence；不得重新排盘、补写未知事实、读心、保证结果、生成输入未提供的具体日期，或提供证券与医疗操作指令。
现实事实、卦象事实和解释接榫必须分开。解释接榫只能标记为实验性解释假设。
context_facts.fact_text 必须逐字复制其唯一 reality_refs 对应的输入现实事实，不得改写或补充。
第一段先给一个明确但不过界的主要判断；必须说明为什么不是相反姿态，并给出具体对象、动作、可观察结果与转向条件。
B 组不得使用任何卦象、爻辞、体用或传统术数内容；C/D 组只能引用输入中提供的 EVxx。
必须严格按给定结构化 Schema 输出，不得增加字段。一次生成完成，不请求工具，不联网，不自我修复。"""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Gate2PromptBuilder:
    """构造独立实验 Prompt，不复用或修改正式解释 Prompt。"""

    version = PROMPT_VERSION

    def build(self, request: Gate2ExperimentRequest) -> Gate2PromptPackage:
        if request.metadata.arm is ExperimentArm.A:
            raise ValueError("A 组是确定性 v16 基线，不构造模型 Prompt")

        chart_payload = None
        if request.chart_context is not None:
            chart_payload = {
                "chart_mapping_id": request.chart_context.chart_mapping_id,
                "is_mismatched_control": request.chart_context.is_mismatched_control,
                "evidence": [
                    {
                        "ref": item.ref,
                        "text": item.text,
                        "knowledge_review_status": item.knowledge_review_status.value,
                    }
                    for item in request.chart_context.evidence
                ],
            }

        payload = {
            "experiment_constraints": {
                "arm": request.metadata.arm.value,
                "synthetic_only": True,
                "question_text_used_for_calculation": False,
                "question_text_used_for_interpretation": True,
                "store": False,
                "tools": [],
                "single_generation_only": True,
                "automatic_model_repair": False,
                "interpretation_is_hypothesis": True,
            },
            "reality_context": request.reality.model_dump(mode="json"),
            "chart_context": chart_payload,
            "allowed_reality_refs": sorted(request.reality.reality_refs()),
            "allowed_evidence_refs": sorted(
                request.chart_context.evidence_refs() if request.chart_context else set()
            ),
            "output_schema": request_output_schema(),
        }
        digest_input = f"{SYSTEM_INSTRUCTIONS}\n{_canonical_json(payload)}".encode("utf-8")
        return Gate2PromptPackage(
            prompt_version=self.version,
            system_instructions=SYSTEM_INSTRUCTIONS,
            input_payload=payload,
            prompt_sha256=hashlib.sha256(digest_input).hexdigest(),
        )


def request_output_schema() -> dict[str, object]:
    from .models import Gate2ExperimentOutput

    return Gate2ExperimentOutput.model_json_schema()
