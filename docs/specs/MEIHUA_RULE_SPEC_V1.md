# 梅花易数确定性排盘规则 V1

规则版本：`MEIHUA_RULE_SPEC_V1`
状态：Phase 1 冻结

## 1. 产品边界

本规范只定义可由 Python 重复计算的排盘事实。AI 不参与起卦、排盘、历法、五行关系、旺衰、证据或时间阶段计算。Phase 1 不生成爱情、事业、吉凶总评、第三方心理或具体日期。

### 稳定规则 ID

| 规则 ID | 规则范围 | Evidence 类型 |
|---|---|---|
| `MEIHUA-V1-RULE-BASE-HEXAGRAM` | 本卦六爻、卦序与卦名事实 | `BASE_HEXAGRAM` |
| `MEIHUA-V1-RULE-BODY-USE` | 初始/变化后体用及互卦对体的五行关系 | `INITIAL_BODY_USE_RELATION`、`CHANGED_BODY_USE_RELATION`、`MUTUAL_LOWER_RELATION`、`MUTUAL_UPPER_RELATION` |
| `MEIHUA-V1-RULE-SEASONAL-STRENGTH` | 月令与旺相休囚死 | `BODY_SEASONAL_STRENGTH`、`INITIAL_USE_SEASONAL_STRENGTH`、`CHANGED_USE_SEASONAL_STRENGTH` |
| `MEIHUA-V1-RULE-MOVING-LINE-STAGE` | 动爻阶段标签 | `MOVING_LINE_STAGE` |

Evidence 的 `source_ref` 必须等于上表中真实存在的稳定规则 ID，不使用易随标题变化的 Markdown 锚点。

## 2. 输入

- `first_number`、`second_number`、`third_number` 必须是 `1..999` 的 `int`；`bool`、字符串、小数、零、负数和大于 999 均拒绝。
- `cast_at` 必须是 timezone-aware `datetime`。
- `timezone_name` 必须是有效 IANA 时区。
- 使用起卦所在地标准民用时间，不使用真太阳时。

统一一基取余：`mod_one_based(value, modulus)`；余数为 0 时返回模数。

## 3. 三数起卦

- 第一数模 8 得上卦。
- 第二数模 8 得下卦。
- 第三数模 6 得动爻。
- 先天数固定为：1乾、2兑、3离、4震、5巽、6坎、7艮、8坤。

## 4. 本卦、互卦、变卦

所有爻数组自下而上：初爻在索引 0，上爻在索引 5。

- 本卦：`下卦三爻 + 上卦三爻`。
- 互卦下卦：`lines[1:4]`。
- 互卦上卦：`lines[2:5]`。
- 变卦：只执行 `changed_lines[moving_line - 1] ^= 1`。
- 互卦不重新划分体用；其上下卦分别与原始体卦计算五行关系。

64 卦名称、King Wen 序号、Unicode 符号和结构必须从 `hexagrams_v1.json` 读取，不得运行时猜测。

## 5. 体用

- 动爻 1–3：上卦为体，下卦为用。
- 动爻 4–6：下卦为体，上卦为用。
- 变化后原不动经卦继续为体；原发生变化的一卦为变化后的用，不在变卦重新取体用。

## 6. 五行关系

相生：木→火→土→金→水→木。
相克：木→土→水→火→金→木。

输出只能是：`USE_GENERATES_BODY`、`BODY_CONTROLS_USE`、`SAME_ELEMENT`、`BODY_GENERATES_USE`、`USE_CONTROLS_BODY`。分别计算初始体用、变化后体用、互卦下卦对体、互卦上卦对体。

## 7. 动爻阶段

1 `GERMINATION`；2 `EARLY_FORMATION`；3 `INTERNAL_THRESHOLD`；4 `EXTERNAL_TURNING_POINT`；5 `CORE_DECISION`；6 `CLOSING_OR_EXCESS`。阶段标签不等于吉凶判断。

## 8. 节气月令与旺相休囚死

历法只能经 `calendar_provider.py` 调用 `lunar_python==1.4.8`。该库节气时刻为北京时间，适配层先按绝对时刻转换至北京时间计算，再把节气边界转换回输入 IANA 时区。

月令按“节”开始，不按农历初一：立春寅木、惊蛰卯木、清明辰土、立夏巳火、芒种午火、小暑未土、立秋申金、白露酉金、寒露戌土、立冬亥水、大雪子水、小寒丑土。

- 同月令五行：旺 `PROSPEROUS`。
- 月令所生：相 `SUPPORTED`。
- 生月令者：休 `RESTING`。
- 克月令者：囚 `CONFINED`。
- 被月令克：死 `DEAD`。

内部秩仅用于相对比较：旺 2、相 1、休 0、囚 -1、死 -2；不得相加成总分、百分比或准确率。节气计算失败必须抛出 `CalendarCalculationError`，不得用固定日期近似。

## 9. 证据与时间

证据只记录程序已经计算出的卦、关系、旺衰和阶段事实。关系/旺衰对应的 polarity 与 strength 是版本化分类标签，不是总分。

### Evidence polarity/strength 冻结表

基础卦与阶段：

| Evidence | 条件 | polarity | strength |
|---|---|---|---|
| `BASE_HEXAGRAM` | 始终 | `NEUTRAL` | `MEDIUM` |
| `MOVING_LINE_STAGE` | 始终 | `NEUTRAL` | `WEAK` |

所有初始、变化后及互卦对体关系统一使用下表：

| 五行关系 | polarity | strength |
|---|---|---|
| `USE_GENERATES_BODY` 用生体 | `POSITIVE` | `STRONG` |
| `BODY_CONTROLS_USE` 体克用 | `POSITIVE` | `MEDIUM` |
| `SAME_ELEMENT` 比和 | `MIXED` | `MEDIUM` |
| `BODY_GENERATES_USE` 体生用 | `NEGATIVE` | `MEDIUM` |
| `USE_CONTROLS_BODY` 用克体 | `NEGATIVE` | `STRONG` |

三个旺衰 Evidence 统一使用下表：

| 旺衰 | polarity | strength |
|---|---|---|
| `PROSPEROUS` 旺 | `POSITIVE` | `STRONG` |
| `SUPPORTED` 相 | `POSITIVE` | `MEDIUM` |
| `RESTING` 休 | `NEUTRAL` | `WEAK` |
| `CONFINED` 囚 | `NEGATIVE` | `MEDIUM` |
| `DEAD` 死 | `NEGATIVE` | `STRONG` |

旺衰只生成独立的季节证据，不增强、削弱或翻转基础生克 Evidence 的 polarity/strength。Phase 1 不合并 Evidence，不生成吉凶总分、百分比、准确率或最终吉凶结论。

`exact_date_feature_enabled=false`，`timing.level=STAGE_ONLY`，`candidate_dates=[]`。程序没有提供日期时，AI 也不得生成日期。

## 10. 当前未实现

旧版页面迁移、AI 解释层、四柱、六爻纳甲、六亲、世应、报告 HTML、用户系统、数据库、支付、邮件、具体日期应期均不在 Phase 1。
