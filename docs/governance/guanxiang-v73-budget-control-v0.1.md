# 观象 V73 公测预算控制 v0.1

状态：`GATE_0_CANDIDATE`

对应工作包：`WP-G0-06`

## 1. 产品负责人决定

- 阶段总责任硬上限：`CNY 150.00`
- 范围：V73 Product Beta 1 的全部付费 API 调用，包括 intake、high、canary、
  失败、超时、未结算调用和反事实质量检查。
- 本决定不等于授权真实调用。每次真实 canary 仍需 PO 单独批准。

决策编号：`DEC-G0-BUDGET-001`

## 2. 保护性换算

运行时以 USD micro-units 计量，但使用固定保护汇率 `1 USD = CNY 8.00`。
该数值是预算防穿透规则，不是实时汇率报价。运行窗口内只能因风险上调，不得因
有利汇率下调来扩大调用。

- CNY 150 绝对责任上限：`USD 18.75`
- 可自动分配上限：`CNY 145 / USD 18.125`
- 不可自动动用缓冲：`CNY 5 / USD 0.625`
- 预警线：`CNY 90 / USD 11.25`

任何时候按 `已结算实际 + 未结算最大预留` 计算占用，并向上取整。未知费用继续
占用其最大预留，直至完成对账。若账单或实际人民币支出先达到 CNY 150，立即 S0
停止，不得用缓冲解释为可继续消费。

## 3. 官方价格与冻结模型

价格核验日期：`2026-08-18`

来源：OpenAI 官方模型详情页：

- `https://developers.openai.com/api/docs/models/gpt-5.6-sol`
- `https://developers.openai.com/api/docs/models/gpt-5.6-luna`

- high：`gpt-5.6-sol`，标准输入 `$5/MTok`，cache write `$6.25/MTok`，标准输出
  `$30/MTok`。
- intake：`gpt-5.6-luna`，标准输入 `$0.20/MTok`，cache write `$0.25/MTok`，
  标准输出 `$1.20/MTok`。

使用标准服务层，不使用 Fast/Priority。定价、模型、币种或计费规则与冻结值不一致
时，预算控制进入 `PRICING_MISMATCH`，禁止新调用，等待重新版本化。

Gate 0 的“单次预计成本”采用保守最大预留值：intake `USD0.02`、high `USD0.50`、
完整体验 `USD0.52`。在首次获批 canary 得到真实 usage 前，不另设乐观均值。canary
后可单列实际均值用于观察，但不得降低硬预留或扩大批次责任容量。

## 4. 单次硬上限与调用次数

- 单次 intake 最大预留：`USD 0.02`。
- 单次 high 最大预留：`USD 0.50`。
- 单次完整体验最大预留：`USD 0.52`。
- 每凭证：最多 1 次 intake、1 次 high；恢复和 GET 不增加调用。
- 全阶段 intake 最大次数：30。
- 全阶段 high 最大次数：36。
- 真实测试用户上限：30；次数上限不构成完成 30 人的承诺。
- global high 并发：1；global intake 并发：2。

调用前还必须执行 billable token 硬门，不能只依赖请求字符数：

- intake：标准输入最多 40,000 token、`max_output_tokens=128`；按 1.25 倍
  uncached input 的 cache-write 最坏价格计算为 `USD 0.0101536`，向上预留
  `USD 0.02`；
- high：标准输入最多 20,000 token、`max_output_tokens=12,000`；按同样的
  cache-write 最坏价格计算为 `USD 0.485`，向上预留 `USD 0.50`；
- 计算包含 system/developer/user、结构化 schema、历史 turns、推理与可见输出等所有
  Provider 计费 token；不得把缓存折扣或实际常见输出当成保护性估计；
- 本地估算无法证明低于硬门时直接按单次上限预留；Provider 返回 usage 后只可释放
  差额，不能事后补记来掩盖预留不足。

只要单次保守预估超过相应上限，调用前拒绝。金额上限和次数上限同时生效，先达到
任何一个即停止。30 人只是最大暴露量；预算不足时缩小样本，不突破上限。

## 5. 最大责任算术与 CNY 145 自动分配

以下是所有最低 Gate 同时成立的最坏预留，不依赖“实际通常更便宜”：

| 用途 | 最大次数 | 单次最大预留 | 最大责任 |
|---|---:|---:|---:|
| Gate 1 唯一真实 canary（intake+high） | 1 | USD0.52 | USD0.52 / CNY4.16 |
| Gate 3A 原3人复测（intake+high） | 3 | USD0.52 | USD1.56 / CNY12.48 |
| Gate 3B～4 最多25名有效启动者（含失败） | 25 | USD0.52 | USD13.00 / CNY104.00 |
| Gate 3C 三对反事实（每对2次high） | 6 high | USD0.50 | USD3.00 / CNY24.00 |
| 合计 | intake 29 / high 35 | — | USD18.08 / CNY144.64 |

这组责任容量允许 25 名标准流程启动者中至少 20 人完成，正好覆盖 80% 完成率门，
并保留 CNY5.36 未分配空间。CNY145 自动分配如下：

- Gate 1 真实 canary：最多 CNY4.16；只允许 1 次完整体验；
- Gate 3C 三对反事实：最多 CNY24；只允许 6 次 high；
- Gate 3A 与 Gate 3B～4：最多 CNY116.48；最多 28 次完整体验（原3人+25名启动者）。

Gate 4 的“累计最多30人”是暴露上限而非应达到的样本承诺。在当前最大预留下，
计划上限为 25 名标准流程启动者；只有已结算差额确实释放、下一批全量最大预留仍
不穿透 CNY145/CNY150 时，才可逐人增加，绝不能以未来释放为由提前发出凭证。

子预算不得互相自动挪用。每批开始前，`可用子预算` 必须覆盖该批所有可能调用的
最大预留；否则缩小批次。CNY5 缓冲只能由 PO 新决定释放，系统不得自动使用。

## 6. 原子预算状态

每个付费请求必须按以下顺序执行：

1. 验证体验凭证、风险边界、次数、频率、幂等和停止状态；
2. 计算冻结模型下的保守最大费用；
3. 在同一原子操作中校验并写入金额、次数和并发预留；
4. 只有预留成功才允许调用 Provider；
5. 终态写入实际费用并释放差额；
6. 超时、断线或响应未知时保留最大预留，不按 0 结算；
7. 孤儿任务必须由对账流程裁决，执行代理不得手工释放。

预算库、凭证库或限流库不可用时 fail closed。凭证/限流密钥与
`PYTHON_ENGINE_KEY` 分离。

## 7. 恢复权限

- 自动停止后不得自动恢复。
- 预算控制设计负责人不得单独恢复。
- 恢复需要 QA `PASS`、反向论证无阻断、PMO 登记和 PO 明确 `GO`。
- 恢复不得提高 CNY 150 总上限；提高总额必须建立新的 PO 决策和版本。

## 8. 每次汇报字段

```text
hard_cap_cny
protective_fx_cny_per_usd
allocated_cap_cny
warning_line_cny
settled_actual_usd/cny
unsettled_reserved_usd/cny
available_allocated_usd/cny
intake_calls_reserved/finalized
high_calls_reserved/finalized
live_calls_this_update
```

Gate 0 不发起真实调用，当前实际使用为 `CNY 0 / USD 0`。
