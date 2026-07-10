# 梅花排盘数据契约 V1

契约版本：`MEIHUA_DATA_CONTRACT_V1`

## 基本约定

- 正式运行数据唯一存放于 `src/abalo_iching/data/meihua/`，通过标准库 `importlib.resources` 加载；不得依赖当前工作目录、仓库根目录或 editable 安装路径。
- JSON 编码 UTF-8；枚举序列化为枚举值字符串。
- 爻为 `0|1`，数组一律自下而上。
- 时间为包含 UTC offset 的 ISO 8601 字符串。
- `timezone_name` 为 IANA 名称；不得传 naive datetime。
- 版本字段不可为空。

## 模型

### MeihuaInput

`first_number`、`second_number`、`third_number` 为必填整数；`cast_at`、`timezone_name` 必填；`question_id` 可为 `null`。输入时间在输出中规范化到指定 IANA 时区。

### Trigram

必填：`number`、`name_zh`、`symbol`、`element`、`lines_bottom_up`、`data_version`。对象从静态 JSON 加载后为不可变 dataclass。

### Hexagram

必填：`king_wen_number`、`name_zh`、`full_name_zh`、`unicode_symbol`、`upper_trigram`、`lower_trigram`、`lines_bottom_up`、`data_version`。

### BodyUseAssignment

必填：`body_trigram`、`initial_use_trigram`、`changed_use_trigram`。变化后不重新取体。

### SeasonContext

必填：`current_solar_term`、`current_solar_term_started_at`、`month_branch`、`month_start_solar_term`、`month_element`、五行完整 `element_strengths`、`body_strength`、`initial_use_strength`、`changed_use_strength`。

### Evidence

九类证据均包含 `evidence_id`、`evidence_type`、`source_ref`、`polarity`、`strength`、`fact`、`rule_statement`、`data_version`，均不可为空。

### TimingContext

`exact_date_feature_enabled` 固定 `false`；`level` 固定 `STAGE_ONLY`；`candidate_dates` 固定空数组。

### RuleVersions

包含 `rule_version`、`trigram_data_version`、`hexagram_data_version`、`calendar_provider`、`engine_version`。

### MeihuaChart

顶层包含输入、上下卦、动爻、本卦、互卦、变卦、体用对象、四类五行关系、动爻阶段、季节上下文、证据数组、时间上下文和版本对象。所有字段除 `question_id` 外均不可为 `null`。

## 枚举

- 五行关系：`USE_GENERATES_BODY`、`BODY_CONTROLS_USE`、`SAME_ELEMENT`、`BODY_GENERATES_USE`、`USE_CONTROLS_BODY`。
- 旺衰：`PROSPEROUS`、`SUPPORTED`、`RESTING`、`CONFINED`、`DEAD`。
- 时间：`STAGE_ONLY`、`TIMING_UNAVAILABLE`；Phase 1 实际固定前者。
- 证据 polarity：`POSITIVE`、`NEGATIVE`、`MIXED`、`NEUTRAL`。
- 证据 strength：`STRONG`、`MEDIUM`、`WEAK`。

## API 复用

未来网站、小程序或 API 层只调用 `cast_meihua(MeihuaInput)` 并使用 `chart_to_dict`/`chart_to_json`；不得重新实现排盘。反序列化由 `chart_from_dict`/`chart_from_json` 完成，API 层不得依赖 `lunar_python`。
