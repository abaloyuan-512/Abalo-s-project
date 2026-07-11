"""Build the Phase 2B Batch 001 human-review workbench from frozen source data."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

BATCH_ID = "MEIHUA-KNOWLEDGE-BATCH-001"
EXTRACTION_SCRIPT_VERSION = "MEIHUA_REVIEW_BATCH_BUILDER_V1"
SOURCE_ACCESSED_AT = "2026-07-11"
EXPECTED_FORMAL_KNOWLEDGE_SHA256 = "4d6078252df9b7162fd49e211acba83460ef15aea01c4115b4d3b45caad8f7fa"

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "src/abalo_iching/data/meihua/hexagram_canonical_texts_v1.json"
HEXAGRAM_DATA_PATH = ROOT / "src/abalo_iching/data/meihua/hexagrams_v1.json"
FORMAL_KNOWLEDGE_PATH = ROOT / "src/abalo_iching/data/meihua/interpretation_knowledge_v1.json"
DOCS_DIR = ROOT / "docs/knowledge_reviews/batch_001"
DATA_DIR = ROOT / "review_data/meihua/batch_001"
EXPECTED_FIXTURE_PATH = ROOT / "tests/fixtures/knowledge_review_batch_001_expected.json"

CTEXT_BASE = "https://ctext.org/book-of-changes"
WIKISOURCE_BASE = "https://zh.wikisource.org/zh-hant/%E5%91%A8%E6%98%93"

SELECTIONS = (
    (1, "QIAN", 1),
    (2, "KUN", 6),
    (3, "ZHUN", 1),
    (4, "MENG", 1),
    (11, "TAI", 3),
    (12, "PI", 5),
    (34, "DA_ZHUANG", 4),
    (55, "FENG", 2),
)

SLUGS = {
    1: ("qian", "%E4%B9%BE"),
    2: ("kun", "%E5%9D%A4"),
    3: ("zhun", "%E5%B1%AF"),
    4: ("meng", "%E8%92%99"),
    11: ("tai", "%E6%B3%B0"),
    12: ("pi", "%E5%90%A6"),
    34: ("da-zhuang", "%E5%A4%A7%E5%A3%AF"),
    55: ("feng", "%E8%B1%90"),
}

# Only received Zhouyi judgments and the eight selected line statements are stored.
# No commentary, translation, or modern interpretation is included.
PUBLIC_SOURCE_TEXTS: dict[tuple[str, int, int | None], str] = {
    ("ctext", 1, None): "元亨，利貞。",
    ("ctext", 2, None): "元亨，利牝馬之貞。君子有攸往，先迷後得主，利西南得朋，東北喪朋。安貞，吉。",
    ("ctext", 3, None): "元亨，利貞，勿用有攸往，利建侯。",
    ("ctext", 4, None): "亨。匪我求童蒙，童蒙求我。初筮告，再三瀆，瀆則不告。利貞。",
    ("ctext", 11, None): "小往大來，吉亨。",
    ("ctext", 12, None): "否之匪人，不利君子貞，大往小來。",
    ("ctext", 34, None): "利貞。",
    ("ctext", 55, None): "亨，王假之，勿憂，宜日中。",
    ("ctext", 1, 1): "潛龍，勿用。",
    ("ctext", 2, 6): "龍戰于野，其血玄黃。",
    ("ctext", 3, 1): "磐桓；利居貞，利建侯。",
    ("ctext", 4, 1): "發蒙，利用刑人，用說桎梏，以往吝。",
    ("ctext", 11, 3): "无平不陂，无往不復，艱貞无咎。勿恤其孚，于食有福。",
    ("ctext", 12, 5): "休否，大人吉。其亡其亡，繫于苞桑。",
    ("ctext", 34, 4): "貞吉悔亡，藩決不羸，壯于大輿之輹。",
    ("ctext", 55, 2): "豐其蔀，日中見斗，往得疑疾，有孚發若，吉。",
    ("wikisource", 1, None): "元亨。利貞。",
    ("wikisource", 2, None): "元亨。利牝馬之貞。君子有攸往，先迷後得主。利西南得朋，東北喪朋。安貞，吉。",
    ("wikisource", 3, None): "元亨，利貞。勿用有攸往，利建侯。",
    ("wikisource", 4, None): "亨。匪我求童蒙，童蒙求我。初筮告，再三瀆，瀆則不告。利貞。",
    ("wikisource", 11, None): "小往大來，吉亨。",
    ("wikisource", 12, None): "否之匪人，不利君子貞，大往小來。",
    ("wikisource", 34, None): "利貞。",
    ("wikisource", 55, None): "亨。王假之，勿憂，宜日中。",
    ("wikisource", 1, 1): "潛龍勿用。",
    ("wikisource", 2, 6): "龍戰于野，其血玄黃。",
    ("wikisource", 3, 1): "磐桓，利居貞，利建侯。",
    ("wikisource", 4, 1): "發蒙，利用刑人，用說桎梏，以往吝。",
    ("wikisource", 11, 3): "无平不陂，无往不復，艱貞无咎。勿恤其孚，于食有福。",
    ("wikisource", 12, 5): "休否，大人吉。其亡其亡，繫于苞桑。",
    ("wikisource", 34, 4): "貞吉悔亡，藩決不羸，壯于大輿之輹。",
    ("wikisource", 55, 2): "豐其蔀，日中見斗，往得疑疾，有孚發若，吉。",
}

MODERN_FIELDS = (
    "judgment_paraphrase",
    "core_theme",
    "situation_pattern",
    "favorable_conditions",
    "risk_conditions",
    "action_tendency",
    "relationship_boundaries",
    "career_boundaries",
    "cooperation_boundaries",
    "prohibited_inferences",
    "evidence_direction",
    "evidence_strength",
    "reviewer_notes",
    "review_decision",
    "literal_paraphrase",
    "moving_stage_relationship",
)

REVIEW_QUESTIONS = (
    "白话直译是否忠实于原文，而不是自由发挥？",
    "核心主题是否避免写成必然吉凶？",
    "有利条件是否具有明确前提？",
    "风险条件是否可以被现实验证？",
    "是否错误推断第三方心理？",
    "是否错误承诺复合、升职、发财等事件？",
    "感情、职业和合作边界是否分别说明？",
    "prohibited_inferences 是否足够具体？",
    "evidence_direction 是否与原文和使用边界一致？",
    "当前内容是否可以进入 REVIEWED，还是应继续退回？",
)

_PUNCTUATION_RE = re.compile(r"[\s，。；：、！？,.!?:;‘’“”《》〈〉（）()\-—]")
_TRADITIONAL_TO_PROJECT = str.maketrans(
    {
        "馬": "马",
        "貞": "贞",
        "喪": "丧",
        "龍": "龙",
        "黃": "黄",
        "發": "发",
        "說": "说",
        "壯": "壮",
        "豐": "丰",
        "憂": "忧",
        "復": "复",
        "艱": "艰",
        "繫": "系",
        "輿": "舆",
        "見": "见",
        "無": "无",
        "於": "于",
        "後": "后",
    }
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_punctuation(text: str) -> str:
    return _PUNCTUATION_RE.sub("", unicodedata.normalize("NFKC", text))


def _normalize_script(text: str) -> str:
    return _normalize_punctuation(text).translate(_TRADITIONAL_TO_PROJECT)


def compare_sources(project_text: str, ctext_text: str | None, wikisource_text: str | None) -> dict[str, Any]:
    sources = [text for text in (ctext_text, wikisource_text) if text is not None]
    exact = bool(sources) and all(text == project_text for text in sources)
    punctuation_equal = bool(sources) and all(_normalize_punctuation(text) == _normalize_punctuation(project_text) for text in sources)
    script_equal = bool(sources) and all(_normalize_script(text) == _normalize_script(project_text) for text in sources)
    missing = len(sources) != 2
    punctuation_only = not exact and punctuation_equal
    script_only = not punctuation_equal and script_equal
    substantive = missing or not script_equal
    if missing:
        notes = "至少一个公开来源未取得；不得补写，必须人工来源复核。"
    elif substantive:
        notes = "规范化后仍存在字词差异，必须人工核对；自动程序未修改正式知识。"
    elif script_only:
        notes = "仅检测到简繁或项目规范化差异；仍需人工确认。"
    elif punctuation_only:
        notes = "仅检测到标点或空白差异；仍需人工确认。"
    else:
        notes = "自动字符比对未发现差异；仍需人工确认来源版本。"
    return {
        "project_text": project_text,
        "ctext_text": ctext_text,
        "wikisource_text": wikisource_text,
        "character_level_match": exact,
        "punctuation_only_difference": punctuation_only,
        "simplified_traditional_difference": script_only,
        "substantive_variant_detected": substantive,
        "variant_notes": notes,
        "source_accessed_at": SOURCE_ACCESSED_AT,
        "human_review_required": True,
    }


def _source_urls(number: int) -> dict[str, str]:
    ctext_slug, wiki_slug = SLUGS[number]
    return {
        "ctext_url": f"{CTEXT_BASE}/{ctext_slug}",
        "wikisource_url": f"{WIKISOURCE_BASE}/{wiki_slug}",
    }


def _empty_review_fields() -> dict[str, Any]:
    fields = {field: None for field in MODERN_FIELDS}
    fields["prohibited_inferences"] = []
    return fields


def build_records() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    formal_hash = _sha256_bytes(FORMAL_KNOWLEDGE_PATH.read_bytes())
    if formal_hash != EXPECTED_FORMAL_KNOWLEDGE_SHA256:
        raise ValueError(f"Formal knowledge hash changed: {formal_hash}")

    canonical = _read_json(CANONICAL_PATH)
    phase1 = _read_json(HEXAGRAM_DATA_PATH)
    canonical_by_number = {item["king_wen_number"]: item for item in canonical["hexagrams"]}
    phase1_by_number = {item["king_wen_number"]: item for item in phase1["hexagrams"]}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for number, roman, line_position in SELECTIONS:
        canonical_hexagram = canonical_by_number[number]
        phase1_hexagram = phase1_by_number[number]
        if canonical_hexagram["hexagram_name"] != phase1_hexagram["name_zh"]:
            raise ValueError(f"Hexagram name mismatch for {number}")
        for item_type, position in (("HEXAGRAM", None), ("LINE", line_position)):
            item_id = f"H{number:02d}" if position is None else f"H{number:02d}-L{position}"
            if item_id in seen:
                raise ValueError(f"Duplicate item_id: {item_id}")
            seen.add(item_id)
            if position is None:
                text = canonical_hexagram["canonical_judgment_text"]
                line_name = None
                card_path = f"hexagrams/H{number:02d}_{roman}.md"
            else:
                line = canonical_hexagram["lines"][position - 1]
                if line["line_position"] != position:
                    raise ValueError(f"Line position mismatch for {item_id}")
                text = line["canonical_line_text"]
                line_name = line["line_name"]
                card_path = f"lines/H{number:02d}_L{position}.md"
            if not text.strip():
                raise ValueError(f"Empty canonical text for {item_id}")
            comparison = compare_sources(
                text,
                PUBLIC_SOURCE_TEXTS.get(("ctext", number, position)),
                PUBLIC_SOURCE_TEXTS.get(("wikisource", number, position)),
            )
            comparison.update(_source_urls(number))
            workbench_status = (
                "SOURCE_VARIANT_REQUIRES_REVIEW"
                if comparison["substantive_variant_detected"]
                else "PENDING_HUMAN_REVIEW"
            )
            record = {
                "batch_id": BATCH_ID,
                "item_id": item_id,
                "item_type": item_type,
                "king_wen_number": number,
                "hexagram_name": canonical_hexagram["hexagram_name"],
                "upper_trigram": phase1_hexagram["upper_trigram"],
                "lower_trigram": phase1_hexagram["lower_trigram"],
                "line_position": position,
                "line_name": line_name,
                "canonical_text_from_project": text,
                "canonical_data_version": canonical["canonical_data_version"],
                "canonical_source_name": canonical_hexagram["source_name"],
                "canonical_source_reference": canonical_hexagram["source_reference"],
                "canonical_source_hash": _sha256_text(text),
                "current_cross_check_status": workbench_status,
                "normalization_rules": canonical["normalization_rules"],
                "extraction_script_version": EXTRACTION_SCRIPT_VERSION,
                "source_comparison": comparison,
                "current_knowledge_status": "CANONICAL_ONLY",
                "workbench_status": workbench_status,
                "knowledge_evidence": [],
                "human_signoff": None,
                "review_fields": _empty_review_fields(),
                "review_card_path": card_path,
            }
            records.append(record)

    return records, canonical


def _review_schema() -> dict[str, Any]:
    nullable_text = {"type": ["string", "null"], "maxLength": 2000}
    review_properties = {field: dict(nullable_text) for field in MODERN_FIELDS}
    review_properties["prohibited_inferences"] = {
        "type": "array",
        "items": {"type": "string", "minLength": 3, "maxLength": 300},
        "maxItems": 12,
    }
    completed_required = [
        "judgment_paraphrase",
        "core_theme",
        "situation_pattern",
        "favorable_conditions",
        "risk_conditions",
        "action_tendency",
        "relationship_boundaries",
        "career_boundaries",
        "cooperation_boundaries",
        "evidence_direction",
        "evidence_strength",
        "review_decision",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://abalo.local/schemas/meihua-batch-001-review.schema.json",
        "title": "Meihua Batch 001 Human Review Workbench",
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "workbench_type", "formal_import_enabled", "records"],
        "properties": {
            "batch_id": {"const": BATCH_ID},
            "workbench_type": {"const": "PENDING_HUMAN_REVIEW_NOT_FORMAL_KNOWLEDGE"},
            "formal_import_enabled": {"const": False},
            "records": {
                "type": "array",
                "minItems": 16,
                "maxItems": 16,
                "items": {"$ref": "#/$defs/reviewRecord"},
            },
        },
        "$defs": {
            "reviewRecord": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "batch_id",
                    "item_id",
                    "item_type",
                    "king_wen_number",
                    "hexagram_name",
                    "upper_trigram",
                    "lower_trigram",
                    "line_position",
                    "line_name",
                    "canonical_text_from_project",
                    "canonical_data_version",
                    "canonical_source_name",
                    "canonical_source_reference",
                    "canonical_source_hash",
                    "current_cross_check_status",
                    "normalization_rules",
                    "extraction_script_version",
                    "source_comparison",
                    "current_knowledge_status",
                    "workbench_status",
                    "knowledge_evidence",
                    "human_signoff",
                    "review_fields",
                    "review_card_path",
                ],
                "properties": {
                    "batch_id": {"const": BATCH_ID},
                    "item_id": {"type": "string", "pattern": "^H(?:01|02|03|04|11|12|34|55)(?:-L[1-6])?$"},
                    "item_type": {"enum": ["HEXAGRAM", "LINE"]},
                    "king_wen_number": {"enum": [1, 2, 3, 4, 11, 12, 34, 55]},
                    "hexagram_name": {"type": "string", "minLength": 1, "maxLength": 4},
                    "upper_trigram": {"type": "string", "minLength": 1, "maxLength": 2},
                    "lower_trigram": {"type": "string", "minLength": 1, "maxLength": 2},
                    "line_position": {"type": ["integer", "null"], "minimum": 1, "maximum": 6},
                    "line_name": {"type": ["string", "null"], "enum": [None, "初", "二", "三", "四", "五", "上"]},
                    "canonical_text_from_project": {"type": "string", "minLength": 2, "maxLength": 500},
                    "canonical_data_version": {"const": "MEIHUA_CANONICAL_TEXTS_V1"},
                    "canonical_source_name": {"type": "string", "minLength": 3, "maxLength": 300},
                    "canonical_source_reference": {"type": "string", "format": "uri"},
                    "canonical_source_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "current_cross_check_status": {"enum": ["PENDING_HUMAN_REVIEW", "SOURCE_VARIANT_REQUIRES_REVIEW"]},
                    "normalization_rules": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 2}},
                    "extraction_script_version": {"const": EXTRACTION_SCRIPT_VERSION},
                    "source_comparison": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "project_text",
                            "ctext_text",
                            "wikisource_text",
                            "character_level_match",
                            "punctuation_only_difference",
                            "simplified_traditional_difference",
                            "substantive_variant_detected",
                            "variant_notes",
                            "source_accessed_at",
                            "human_review_required",
                            "ctext_url",
                            "wikisource_url",
                        ],
                        "properties": {
                            "project_text": {"type": "string", "minLength": 2},
                            "ctext_text": {"type": ["string", "null"], "minLength": 2},
                            "wikisource_text": {"type": ["string", "null"], "minLength": 2},
                            "character_level_match": {"type": "boolean"},
                            "punctuation_only_difference": {"type": "boolean"},
                            "simplified_traditional_difference": {"type": "boolean"},
                            "substantive_variant_detected": {"type": "boolean"},
                            "variant_notes": {"type": "string", "minLength": 3, "maxLength": 500},
                            "source_accessed_at": {"type": "string", "format": "date"},
                            "human_review_required": {"const": True},
                            "ctext_url": {"type": "string", "format": "uri"},
                            "wikisource_url": {"type": "string", "format": "uri"},
                        },
                    },
                    "current_knowledge_status": {"const": "CANONICAL_ONLY"},
                    "workbench_status": {
                        "enum": [
                            "PENDING_HUMAN_REVIEW",
                            "SOURCE_VARIANT_REQUIRES_REVIEW",
                            "READY_FOR_CONTENT_REVIEW",
                            "RETURNED_FOR_REVISION",
                            "HUMAN_REVIEW_COMPLETE",
                        ]
                    },
                    "knowledge_evidence": {"type": "array", "maxItems": 0},
                    "human_signoff": {
                        "oneOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["person", "completed_at", "decision"],
                                "properties": {
                                    "person": {"type": "string", "minLength": 2, "maxLength": 100},
                                    "completed_at": {"type": "string", "format": "date-time"},
                                    "decision": {"const": "CONTENT_REVIEW_COMPLETE_NOT_APPROVED"},
                                },
                            },
                        ]
                    },
                    "review_fields": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": list(MODERN_FIELDS),
                        "properties": review_properties,
                    },
                    "review_card_path": {"type": "string", "pattern": "^(hexagrams|lines)/H[0-9]{2}_[A-Z0-9_]+\\.md$"},
                },
                "allOf": [
                    {
                        "if": {"properties": {"item_type": {"const": "HEXAGRAM"}}},
                        "then": {"properties": {"line_position": {"type": "null"}, "line_name": {"type": "null"}}},
                        "else": {"properties": {"line_position": {"type": "integer"}, "line_name": {"type": "string"}}},
                    },
                    {
                        "if": {"properties": {"workbench_status": {"const": "HUMAN_REVIEW_COMPLETE"}}},
                        "then": {
                            "properties": {
                                "human_signoff": {"type": "object"},
                                "review_fields": {
                                    "properties": {
                                        field: {"type": "string", "minLength": 3, "maxLength": 2000}
                                        for field in completed_required
                                    }
                                },
                            }
                        },
                        "else": {"properties": {"human_signoff": {"type": "null"}}},
                    },
                ],
            }
        },
    }


def _card(record: dict[str, Any]) -> str:
    comparison = record["source_comparison"]
    identity_lines = [
        f"- Batch ID：`{record['batch_id']}`",
        f"- Item ID：`{record['item_id']}`",
        f"- 卦序：{record['king_wen_number']}",
        f"- 卦名：{record['hexagram_name']}",
        f"- 上卦：{record['upper_trigram']}",
        f"- 下卦：{record['lower_trigram']}",
        f"- 当前知识状态：`{record['current_knowledge_status']}`",
        f"- 当前跨来源核验状态：`{record['current_cross_check_status']}`",
    ]
    if record["item_type"] == "LINE":
        identity_lines.extend([f"- 爻位：{record['line_position']}", f"- 爻名：{record['line_name']}"])
    project_label = "项目冻结卦辞" if record["item_type"] == "HEXAGRAM" else "项目冻结爻辞"
    fields = list(MODERN_FIELDS)
    if record["item_type"] == "HEXAGRAM":
        fields.remove("literal_paraphrase")
        fields.remove("moving_stage_relationship")
    pending = "\n".join(f"- {field}：`PENDING_HUMAN_REVIEW`" for field in fields)
    questions = "\n".join(f"{index}. {question}" for index, question in enumerate(REVIEW_QUESTIONS, start=1))
    line_questions = ""
    if record["item_type"] == "LINE":
        line_questions = (
            "\n11. 是否容易被脱离全卦语境误读？"
            "\n12. 是否可能被误读为‘这件事一定成功或失败’？"
        )
    ctext = comparison["ctext_text"] or "SOURCE_UNAVAILABLE_REQUIRES_HUMAN_REVIEW"
    wiki = comparison["wikisource_text"] or "SOURCE_UNAVAILABLE_REQUIRES_HUMAN_REVIEW"
    return f"""# {record['item_id']}｜{record['hexagram_name']}{'爻' if record['item_type'] == 'LINE' else '卦'}审核卡

> 本卡是待人工审核工作台，不是正式知识记录。所有现代解释字段均未填写。

## A. 身份信息

{chr(10).join(identity_lines)}

## B. 原文区

### {project_label}

> {record['canonical_text_from_project']}

### Chinese Text Project 对应文本

> {ctext}

来源：{comparison['ctext_url']}

### 维基文库对应文本

> {wiki}

来源：{comparison['wikisource_url']}

### 异文说明

{comparison['variant_notes']}

### 规范化说明

自动比较仅区分空白、标点、简繁/项目字符规范化及规范化后仍存在的字词差异；结果不能代替人工版本核验，也不能晋升知识状态。

## C. 待人工填写区

{pending}

## D. 审核问题

{questions}{line_questions}
"""


def _readme(records: list[dict[str, Any]]) -> str:
    return f"""# 梅花易数知识人工审核工作台｜Batch 001

Batch ID：`{BATCH_ID}`

本目录用于首批 16 条卦爻知识的人工内容审核准备，包含 8 条卦级记录和 8 条爻级记录。它与正式知识库、原始来源快照严格分离，不会自动写入正式知识库，也不会产生 KnowledgeEvidence。

## 为什么选择本批

本批覆盖萌芽、末端或过度、起步困难、信息不足、顺境转折、阻塞恢复、强而需节制、丰盛但信息遮蔽等需要谨慎审核的文本情境。选择这些情境是为了检查解释边界，不代表已经形成感情、职业或合作结论，更不代表“必成”或“必败”。

## 固定范围

- 卦级：乾、坤、屯、蒙、泰、否、大壮、丰。
- 爻级：乾初爻、坤上爻、屯初爻、蒙初爻、泰三爻、否五爻、大壮四爻、丰二爻。
- 记录总数：{len(records)}。

## 使用顺序

1. 先读 `SOURCE_COMPARISON.md`，确认项目冻结原文和两处公开来源的文本差异。
2. 按 `REVIEW_GUIDE.md` 填写 16 张 Markdown 审核卡或 Excel 工作簿。
3. 把每次人工决定记录在 `REVIEW_DECISION_LOG.md`。
4. 使用 `scripts/validate_meihua_review_batch.py` 做只读检查。
5. 当前版本禁止导入正式知识库；即使人工内容已完成，也只能等待后续人工批准阶段。
"""


def _review_guide() -> str:
    return """# 人工审核指南

1. **卦辞审核**：核对整卦卦辞的原文字词、适用边界和条件，不把卦名直接等同于现实事件。
2. **爻辞审核**：在全卦语境和具体爻位中核对爻辞，不把单爻从上下文中抽离。
3. **白话直译与现代应用解释**：直译只说明原句表层意思；现代应用解释还涉及现实条件，两者必须分开填写。
4. **“吉”不等于“必成”**：吉表示文本中的有利方向或条件，不是对现实结果的保证。
5. **“凶”不等于“必败”**：凶表示风险或不利方向，不等于事件必然失败。
6. **不推断第三方心理**：卦爻文本不能证明他人真实想法、承诺或隐秘动机。
7. **有利条件**：写清触发有利方向所需的前提、行为和可观察条件。
8. **风险条件**：写成现实中可以检查的风险信号，避免笼统恐吓。
9. **行动倾向**：描述可选择的行动方向，不写成命令或结果承诺。
10. **卦象指引与现实建议**：卦象指引必须有原文依据；现实建议必须说明它是现实判断，不能伪装成卦象事实。
11. **领域边界**：感情、职业、合作分别说明可谈内容与不可推断内容，不跨领域套用结论。
12. **prohibited_inferences**：具体列出不能推出的事件、心理、日期、概率或身份事实。
13. **evidence_direction 与 strength**：只表达知识证据方向和约束强度，不是统计概率，也不代表预测准确率。
14. **退回继续审核**：原文来源不一致、边界含糊、出现必然化承诺或第三方心理推断时，应退回修订。
15. **只能保持 CANONICAL_ONLY**：没有完成来源核对、内容审核和后续独立人工批准时，正式知识状态必须保持 CANONICAL_ONLY。

本指南服务于产品内容审核，不是玄学教学材料，也不授权自动生成现代解释。
"""


def _decision_log() -> str:
    return """# Batch 001 人工审核决策日志

> 初始模板：当前尚未填写任何审核决定。

| 日期 | Item ID | 审核人 | 审核轮次 | 决定 | 主要问题 | 修改要求 | 是否允许进入下一轮 | 备注 |
|---|---|---|---:|---|---|---|---|---|
|  |  |  |  | 保持 CANONICAL_ONLY／退回修订／内容审核完成 |  |  |  |  |
"""


def _comparison_markdown(records: list[dict[str, Any]]) -> str:
    rows = []
    for record in records:
        comparison = record["source_comparison"]
        rows.append(
            "| {item_id} | {item_type} | {punct} | {script} | {substantive} | {status} |".format(
                item_id=record["item_id"],
                item_type=record["item_type"],
                punct="是" if comparison["punctuation_only_difference"] else "否",
                script="是" if comparison["simplified_traditional_difference"] else "否",
                substantive="是" if comparison["substantive_variant_detected"] else "否",
                status=record["workbench_status"],
            )
        )
    punct_count = sum(item["source_comparison"]["punctuation_only_difference"] for item in records)
    script_count = sum(item["source_comparison"]["simplified_traditional_difference"] for item in records)
    substantive_count = sum(item["source_comparison"]["substantive_variant_detected"] for item in records)
    return f"""# Batch 001 跨来源原文对照

对照范围严格限定为 8 条卦辞和 8 条爻辞。公开来源只保存古籍原文和必要元数据，不包含现代译文或注释。

- Chinese Text Project：{CTEXT_BASE}
- 维基文库：{WIKISOURCE_BASE}
- 项目冻结主文本：`src/abalo_iching/data/meihua/hexagram_canonical_texts_v1.json`
- 来源访问日期：{SOURCE_ACCESSED_AT}

自动比较统计：标点/空白差异 {punct_count} 条；简繁或项目规范化差异 {script_count} 条；规范化后仍有实质字词差异 {substantive_count} 条。所有 16 条仍需人工复核。

| Item ID | 类型 | 标点差异 | 简繁/规范化差异 | 实质性异文 | 工作台状态 |
|---|---|---|---|---|---|
{chr(10).join(rows)}

自动比较结果不能代替人工异文审核；即使没有发现实质性异文，也不能据此晋升知识状态。
"""


def build() -> list[dict[str, Any]]:
    records, canonical = build_records()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "hexagrams").mkdir(exist_ok=True)
    (DOCS_DIR / "lines").mkdir(exist_ok=True)

    formal_hash = _sha256_bytes(FORMAL_KNOWLEDGE_PATH.read_bytes())
    snapshot = {
        "batch_id": BATCH_ID,
        "snapshot_type": "HUMAN_REVIEW_SOURCE_SNAPSHOT_NOT_FORMAL_KNOWLEDGE",
        "canonical_data_version": canonical["canonical_data_version"],
        "formal_knowledge_sha256": formal_hash,
        "source_accessed_at": SOURCE_ACCESSED_AT,
        "records": records,
    }
    drafts = {
        "batch_id": BATCH_ID,
        "workbench_type": "PENDING_HUMAN_REVIEW_NOT_FORMAL_KNOWLEDGE",
        "formal_import_enabled": False,
        "records": records,
    }
    manifest = {
        "batch_id": BATCH_ID,
        "record_count": len(records),
        "hexagram_record_count": sum(item["item_type"] == "HEXAGRAM" for item in records),
        "line_record_count": sum(item["item_type"] == "LINE" for item in records),
        "formal_knowledge_sha256": formal_hash,
        "canonical_data_version": canonical["canonical_data_version"],
        "selection": [
            {
                "king_wen_number": number,
                "hexagram_item_id": f"H{number:02d}",
                "line_item_id": f"H{number:02d}-L{line_position}",
                "line_position": line_position,
            }
            for number, _, line_position in SELECTIONS
        ],
        "formal_import_enabled": False,
        "generated_outputs": [
            "README.md",
            "BATCH_MANIFEST.json",
            "SOURCE_COMPARISON.md",
            "REVIEW_GUIDE.md",
            "REVIEW_DECISION_LOG.md",
            "MEIHUA_KNOWLEDGE_BATCH_001_REVIEW.xlsx",
            *[item["review_card_path"] for item in records],
        ],
    }
    expected = {
        "batch_id": BATCH_ID,
        "formal_knowledge_sha256": formal_hash,
        "hexagrams": [number for number, _, _ in SELECTIONS],
        "lines": [{"king_wen_number": number, "line_position": line} for number, _, line in SELECTIONS],
        "item_ids": [item["item_id"] for item in records],
        "review_card_paths": [item["review_card_path"] for item in records],
    }

    _write_json(DATA_DIR / "batch_001_source_snapshot.json", snapshot)
    _write_json(DATA_DIR / "batch_001_review_drafts.json", drafts)
    _write_json(DATA_DIR / "batch_001_review_schema.json", _review_schema())
    _write_json(DOCS_DIR / "BATCH_MANIFEST.json", manifest)
    _write_json(EXPECTED_FIXTURE_PATH, expected)
    (DOCS_DIR / "README.md").write_text(_readme(records), encoding="utf-8")
    (DOCS_DIR / "SOURCE_COMPARISON.md").write_text(_comparison_markdown(records), encoding="utf-8")
    (DOCS_DIR / "REVIEW_GUIDE.md").write_text(_review_guide(), encoding="utf-8")
    (DOCS_DIR / "REVIEW_DECISION_LOG.md").write_text(_decision_log(), encoding="utf-8")
    for record in records:
        (DOCS_DIR / record["review_card_path"]).write_text(_card(record), encoding="utf-8")
    print(f"BATCH_ID={BATCH_ID}")
    print(f"RECORDS={len(records)}")
    print(f"HEXAGRAM_RECORDS={sum(item['item_type'] == 'HEXAGRAM' for item in records)}")
    print(f"LINE_RECORDS={sum(item['item_type'] == 'LINE' for item in records)}")
    print(f"FORMAL_KNOWLEDGE_SHA256={formal_hash}")
    return records


if __name__ == "__main__":
    build()
