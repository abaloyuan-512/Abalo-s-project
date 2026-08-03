"""Versioned data contract for Guanxiang page 8 layered reading.

This module only structures already-computed chart facts and separately
validated interpretation hypotheses. It never casts or changes a chart.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from abalo_iching.personalization_gate2.models import StrictModel
from abalo_iching.personalization_gate2.stage_c2_contract import (
    Gate2ExperimentOutputV3,
)


PAGE8_READING_VERSION = "SITES_PAGE8_READING_V1"


class Page8SceneId(StrEnum):
    BASE_HEXAGRAM = "BASE_HEXAGRAM"
    MUTUAL_HEXAGRAM = "MUTUAL_HEXAGRAM"
    CHANGED_HEXAGRAM = "CHANGED_HEXAGRAM"
    MOVING_LINE = "MOVING_LINE"
    BODY_USE_STRENGTH = "BODY_USE_STRENGTH"


PAGE8_SCENE_ORDER = (
    Page8SceneId.BASE_HEXAGRAM,
    Page8SceneId.MUTUAL_HEXAGRAM,
    Page8SceneId.CHANGED_HEXAGRAM,
    Page8SceneId.MOVING_LINE,
    Page8SceneId.BODY_USE_STRENGTH,
)

_REQUIRED_EVIDENCE_BY_SCENE: dict[Page8SceneId, frozenset[str]] = {
    Page8SceneId.BASE_HEXAGRAM: frozenset({"EV10"}),
    Page8SceneId.MUTUAL_HEXAGRAM: frozenset({"EV11"}),
    Page8SceneId.CHANGED_HEXAGRAM: frozenset({"EV12"}),
    Page8SceneId.MOVING_LINE: frozenset({"EV13"}),
    Page8SceneId.BODY_USE_STRENGTH: frozenset({"EV02", "EV03", "EV06"}),
}


class Page8LayerInterpretationV1(StrictModel):
    """One evidence-linked interpretation hypothesis for one page-8 scene."""

    scene_id: Page8SceneId
    layer_summary: str = Field(min_length=12, max_length=220)
    reality_connection: str = Field(min_length=20, max_length=600)
    uncertainty_boundary: str = Field(min_length=12, max_length=320)
    reality_refs: list[str] = Field(min_length=1, max_length=8)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    interpretation_hypothesis: Literal[True]

    @model_validator(mode="after")
    def validate_references(self) -> Page8LayerInterpretationV1:
        if len(self.reality_refs) != len(set(self.reality_refs)):
            raise ValueError("第八页每幕 reality_refs 不得重复")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("第八页每幕 evidence_refs 不得重复")
        if any(not ref.startswith("RW") or not ref[2:].isdigit() for ref in self.reality_refs):
            raise ValueError("第八页现实依据必须使用 RWxx")
        if any(not ref.startswith("EV") or not ref[2:].isdigit() for ref in self.evidence_refs):
            raise ValueError("第八页卦象依据必须使用 EVxx")
        required = _REQUIRED_EVIDENCE_BY_SCENE[self.scene_id]
        if not required.issubset(self.evidence_refs):
            raise ValueError(f"{self.scene_id.value} 缺少指定卦象依据")
        return self


class OwnerPreviewExperimentOutputPage8V1(Gate2ExperimentOutputV3):
    """Existing owner-preview output plus the five page-8 interpretations."""

    layered_reading: list[Page8LayerInterpretationV1] = Field(
        min_length=5,
        max_length=5,
    )

    @model_validator(mode="after")
    def validate_layer_order(self) -> OwnerPreviewExperimentOutputPage8V1:
        if tuple(item.scene_id for item in self.layered_reading) != PAGE8_SCENE_ORDER:
            raise ValueError("第八页必须按本卦、互卦、变卦、动爻、体用旺衰输出")
        return self


class Page8FactV1(StrictModel):
    label: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=500)


class Page8DeterministicContentV1(StrictModel):
    """Chart/canonical content. No user reality is allowed in this block."""

    primary_name: str = Field(min_length=1, max_length=80)
    symbol: str | None = Field(default=None, max_length=16)
    king_wen_number: int | None = Field(default=None, ge=1, le=64)
    formation: str = Field(min_length=1, max_length=500)
    reading_role: str = Field(min_length=1, max_length=500)
    canonical_label: str | None = Field(default=None, max_length=40)
    canonical_text: str | None = Field(default=None, max_length=1200)
    plain_note: str | None = Field(default=None, max_length=1200)
    facts: list[Page8FactV1] = Field(default_factory=list, max_length=8)
    source_name: str = Field(min_length=1, max_length=160)
    source_reference: str = Field(min_length=1, max_length=300)


class Page8SceneV1(StrictModel):
    scene_id: Page8SceneId
    sequence: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=40)
    purpose: str = Field(min_length=1, max_length=220)
    deterministic: Page8DeterministicContentV1
    interpretation: Page8LayerInterpretationV1

    @model_validator(mode="after")
    def validate_scene_alignment(self) -> Page8SceneV1:
        if self.scene_id is not self.interpretation.scene_id:
            raise ValueError("第八页场景与个性化解释必须对应")
        return self


class Page8ReadingV1(StrictModel):
    template_version: Literal[PAGE8_READING_VERSION]
    stage_title: Literal["读卦"]
    user_question: str = Field(min_length=1, max_length=160)
    scenes: list[Page8SceneV1] = Field(min_length=5, max_length=5)
    epistemic_boundary: str = Field(min_length=1, max_length=500)
    page9_reserved: Literal[True]

    @model_validator(mode="after")
    def validate_scene_sequence(self) -> Page8ReadingV1:
        if tuple(scene.scene_id for scene in self.scenes) != PAGE8_SCENE_ORDER:
            raise ValueError("第八页场景顺序不符合冻结要求")
        if [scene.sequence for scene in self.scenes] != [1, 2, 3, 4, 5]:
            raise ValueError("第八页场景序号必须连续")
        return self


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"第八页缺少{label}")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"第八页缺少{label}")
    return value


def _text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"第八页缺少{label}")
    return text


def _hexagram_content(
    item: Mapping[str, Any],
    *,
    formation: str,
    facts: list[Page8FactV1] | None = None,
) -> Page8DeterministicContentV1:
    return Page8DeterministicContentV1(
        primary_name=_text(item.get("name"), "卦名"),
        symbol=_text(item.get("symbol"), "卦象"),
        king_wen_number=int(item.get("king_wen_number", 0)),
        formation=formation,
        reading_role=_text(item.get("reading_role"), "卦象阅读作用"),
        canonical_label="卦辞原文",
        canonical_text=_text(item.get("canonical_text"), "卦辞原文"),
        plain_note=_text(item.get("plain_note"), "字义小注"),
        facts=facts or [],
        source_name=_text(item.get("source_name"), "经典来源"),
        source_reference=_text(item.get("source_reference"), "经典出处"),
    )


def build_page8_reading_v1(
    *,
    user_question: str,
    deterministic_result: Mapping[str, Any],
    interpretations: Sequence[Page8LayerInterpretationV1],
) -> Page8ReadingV1:
    """Assemble the five review scenes without changing chart facts."""

    cultural = _mapping(deterministic_result.get("cultural_reading"), "文化读卦资料")
    hexagrams = [_mapping(item, "卦象资料") for item in _sequence(cultural.get("hexagrams"), "三卦资料")]
    if len(hexagrams) != 3 or [item.get("role") for item in hexagrams] != ["本卦", "互卦", "变卦"]:
        raise ValueError("第八页三卦资料顺序不完整")
    number_path = [_mapping(item, "三数路径") for item in _sequence(cultural.get("number_path"), "三数路径")]
    if len(number_path) != 3:
        raise ValueError("第八页三数路径不完整")
    moving_line = _mapping(cultural.get("moving_line"), "动爻资料")
    terms = [_mapping(item, "体用旺衰资料") for item in _sequence(cultural.get("terms"), "体用旺衰资料")]
    if len(terms) < 3:
        raise ValueError("第八页体用旺衰资料不完整")
    layer_map = {item.scene_id: item for item in interpretations}
    if tuple(layer_map) != PAGE8_SCENE_ORDER:
        raise ValueError("第八页个性化解释顺序不完整")

    base_facts = [
        Page8FactV1(
            label=_text(item.get("role"), "三数角色"),
            value=(
                f"输入数 {_text(item.get('input_number'), '输入数')} → "
                f"{_text(item.get('result_name'), '三数结果')}；"
                f"{_text(item.get('explanation'), '三数说明')}"
            ),
        )
        for item in number_path[:2]
    ]
    scene_specs = [
        (
            Page8SceneId.BASE_HEXAGRAM,
            "本卦",
            "看清这件事眼下最主要的结构，以及本卦怎样由前两数形成。",
            _hexagram_content(
                hexagrams[0],
                formation="第一数定上卦，第二数定下卦；上下两卦相叠，形成本卦。",
                facts=base_facts,
            ),
        ),
        (
            Page8SceneId.MUTUAL_HEXAGRAM,
            "互卦",
            "看清事情内部怎样发展，不把内部结构误当成已经发生的现实结果。",
            _hexagram_content(
                hexagrams[1],
                formation="取本卦中间四爻重新组合，形成互卦。",
            ),
        ),
        (
            Page8SceneId.CHANGED_HEXAGRAM,
            "变卦",
            "看清动爻改变后结构重点转向哪里，不把变卦写成必然未来。",
            _hexagram_content(
                hexagrams[2],
                formation="本次动爻由阴变阳或由阳变阴后，形成变卦。",
            ),
        ),
        (
            Page8SceneId.MOVING_LINE,
            "动爻",
            "看清本次变化发生在哪一爻、处于什么阶段，以及爻辞提供的观察角度。",
            Page8DeterministicContentV1(
                primary_name=_text(moving_line.get("line_name"), "动爻名称"),
                formation="第三数按六数之余确定本次动爻；这一爻变化后，本卦随之成为变卦。",
                reading_role="动爻标记本次卦象中实际发生结构变化的位置。",
                canonical_label="爻辞原文",
                canonical_text=_text(moving_line.get("canonical_text"), "爻辞原文"),
                facts=[
                    Page8FactV1(label="动爻位置", value=str(moving_line.get("position"))),
                    Page8FactV1(label="对应阶段", value=_text(moving_line.get("stage"), "动爻阶段")),
                    Page8FactV1(
                        label="变化路径",
                        value=(
                            f"{_text(deterministic_result.get('base_hexagram', {}).get('name'), '本卦')}"
                            f" → {_text(deterministic_result.get('changed_hexagram', {}).get('name'), '变卦')}"
                        ),
                    ),
                ],
                source_name=_text(moving_line.get("source_name"), "爻辞来源"),
                source_reference=_text(moving_line.get("source_reference"), "爻辞出处"),
            ),
        ),
        (
            Page8SceneId.BODY_USE_STRENGTH,
            "体用与旺衰",
            "分清体与用的关系及当前余力；旺衰只说明承接条件，不作吉凶总评。",
            Page8DeterministicContentV1(
                primary_name="体用与旺衰",
                formation="体用关系与旺衰由确定性排盘结果和版本化规则生成。",
                reading_role="体用帮助观察你与所问之事的关系，旺衰帮助观察当下余力与限制。",
                facts=[
                    Page8FactV1(
                        label=_text(item.get("title"), "体用旺衰标题"),
                        value=(
                            f"{_text(item.get('current_value'), '当前结果')}。"
                            f"{_text(item.get('meaning'), '含义')}"
                            f"{_text(item.get('current_effect'), '本次影响')}"
                        ),
                    )
                    for item in terms[:3]
                ],
                source_name="观象梅花确定性规则",
                source_reference=_text(cultural.get("template_version"), "文化读卦版本"),
            ),
        ),
    ]
    scenes = [
        Page8SceneV1(
            scene_id=scene_id,
            sequence=index,
            title=title,
            purpose=purpose,
            deterministic=deterministic,
            interpretation=layer_map[scene_id],
        )
        for index, (scene_id, title, purpose, deterministic) in enumerate(scene_specs, start=1)
    ]
    return Page8ReadingV1(
        template_version=PAGE8_READING_VERSION,
        stage_title="读卦",
        user_question=user_question.strip(),
        scenes=scenes,
        epistemic_boundary=(
            "卦象依据来自确定性排盘与版本化经典资料；结合所问的文字是解释假设，"
            "只使用用户明确提供的信息，不把现实背景伪装成卦象证据。"
        ),
        page9_reserved=True,
    )
