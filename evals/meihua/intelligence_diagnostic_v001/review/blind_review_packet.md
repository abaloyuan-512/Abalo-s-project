# 观象智能能力诊断集 v1.0 · 盲评说明

## 只评两个问题

1. 当前辨识是否真正找到用户卡点，而不是复述信息？
2. 当前解卦是否像“因为这个卦而这样判断”，而不是普通 AI 建议？

## 评审材料隔离

- 用户价值评审只读取 `reviewer_cases/user_value_cases.json` 与 `user_value_form.json`。
- 易学结构评审只读取 `reviewer_cases/iching_structure_cases.json` 与 `iching_structure_form.json`。
- 产品边界评审只读取 `reviewer_cases/product_boundary_cases.json` 与 `product_boundary_checklist.json`。
- 评审者不得读取 `cases.json`、`case_index.json`、`reveal_key.json`、治理日志或历史反馈。
- `reveal_key.json` 由主代理和 PMO 密封保管；所有评审结果完成并冻结哈希后才能揭盲。

## 材料限制

- 10 例全部是合成或产品校准材料，不是真实用户案例。
- 当前有 4 例冻结辨识基线，其中 3 例完成、1 例在四次回答后仍未完成；其余 6 例的辨识问题必须填 `CANNOT_JUDGE`。
- 4 例具备完整、可复核的确定性盘面与历史解卦快照；其余案例材料不足时，不得强行评分。
- 没有案例本人反馈，普通用户评审和易学评审均尚未指派。

## 强制判定规则

- 用户评审缺少原问题、足够语境的逐轮辨识、建议题目或用户可见理由时，辨识项必须 `CANNOT_JUDGE`。
- 用户评审缺少同案确定性盘面、对应解卦或所回答问题时，卦象增量项必须 `CANNOT_JUDGE`。
- 易学评审遇到盘面、动爻、体用、旺衰或引用依据不足时，必须 `UNCERTAIN`，不能把材料缺失评成 `UNSUPPORTED`。
- 产品边界无法检查时填 `null` 与原因，整体状态为 `INCOMPLETE`，不能自动通过。
- 不用文案长度、古语数量或 validator 通过代替价值通过；任一硬边界失败不能被平均分抵消。

## 揭盲流程

1. 冻结盲包顺序和每例 `payload_sha256`。
2. 分角色发放对应盲包，不发放来源、分层、旧反馈和作者信息。
3. 回收评审结果并生成结果清单哈希。
4. PMO 核验缺答与强制 `CANNOT_JUDGE` / `UNCERTAIN` 是否合规。
5. 满足 `ALL_ASSIGNED_REVIEWS_FROZEN` 后才揭盲，并按预先冻结的分层汇总；不得根据结果重分层。
