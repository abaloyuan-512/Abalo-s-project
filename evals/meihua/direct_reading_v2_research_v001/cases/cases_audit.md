# Direct Reading V2 冻结案例审计

## 审计结论

- 资产版本：`GUANXIANG_DIRECT_READING_V2_RESEARCH_CASES_V001`
- 冻结范围：5 个确定性盘面、9 个原始问题。
- `cases.json` SHA-256：`7efe03e9c6ad9ee193748f6b6cb4881d9f3434f1acab1b0fe5cd8be0348dcb25`
- 确定性复算：通过。五案的本卦、互卦、变卦、上下卦、动爻位置、动爻名称及冻结爻辞全部与当前版本化引擎和经典文本包一致。
- 范围检查：通过。案例不含辨识回答、现实背景、旧版建议、旧版 clarity report 或旺衰字段。
- 本次未调用模型，未修改生产代码、Prompt、API、页面或确定性规则。

## 来源

### DR-01-WORK-SWITCH

来源为用户本轮提供的真实问题和已成卦结果：问题为“我要不要考虑换工作这件事？”，本卦风水涣、互卦山雷颐、三爻动、变卦巽为风。

用户未提供完整原始三数。研究资产保存的 `[5, 6, 3]` 是与该盘等价的归一化代表三数，字段 `numbers_semantics` 已明确标记为 `EQUIVALENT_NORMALIZED_TRIPLE_NOT_ORIGINAL_RAW_INPUT`，不得将其表述为用户当时输入的原始三数。该案不保存推测时间。

### DR-02 至 DR-05

四案及八个问题来自：

- `evals/meihua/personalization_gate0_v001/fixed_cases.json`
- `evals/meihua/personalization_gate0_v001/question_text_pair_outputs.json`
- `evals/meihua/personalization_gate0_v001/audit_summary.json`

原 Gate 0 数据集是 `SYNTHETIC_DETERMINISTIC_BASELINE_ONLY`。四案保留原始 `client_timestamp`：`2026-07-18T10:30:00+08:00`，仅用于来源追踪。根级 `model_input_policy` 已冻结：后续模型正文不得接收该时间，也不得由该时间派生旺衰输入。

## 五盘九问与敏感性配对

| 盘面 | 问题数 | 配对用途 |
|---|---:|---|
| DR-01 风水涣 → 巽为风 | 1 | 真实用户价值锚点；验证无辨识时能否完整回应换工作问题。 |
| DR-02 天地否 → 火地晋 | 2 | 同盘比较“继续争取晋升”与“接受岗位安排”。 |
| DR-03 山地剥 → 艮为山 | 2 | 同盘比较一般合作投入与“多次延期后追加预算”。 |
| DR-04 雷火丰 → 雷天大壮 | 2 | 同盘比较主动联系与“反复争执后继续维持”。 |
| DR-05 水雷屯 → 水地比 | 2 | 同盘比较继续备考与继续投入副业。 |

历史 Gate 0 审计显示，上述四组配对在旧流程中虽然问题文本不同，但各组两个 clarity report 完全相同。因而它们在本研究中的用途不是提供参考答案，而是检验新直接解卦方案能否在不改变确定性盘面的前提下，真正响应不同的所问之事。

敏感性判断边界：同盘换问题时，本卦、互卦、动爻、变卦及经典原文必须保持不变；现实应用、核心判断、行动建议和反向边界应当根据问题语义合理变化。

## 版本来源

每案均冻结以下版本：

- 规则：`MEIHUA_RULE_SPEC_V1`
- 引擎：`MEIHUA_ENGINE_PHASE1_V1`
- 八卦数据：`MEIHUA_TRIGRAMS_V1`
- 六十四卦数据：`MEIHUA_HEXAGRAMS_V1`
- 经典文本：`MEIHUA_CANONICAL_TEXTS_V1`

经典文本来源名称及引用地址随每案保存。来源名称自身注明“冻结主文本，待逐条人工版本核对”；本研究可以把它作为当前项目的版本化基准，不得把它宣称为最终校勘定本。

## 复算路径与结果

确定性复算使用现有只读构造链：

1. `cast_meihua(MeihuaInput(...))`
2. `build_interpretation_packet_v1(chart)`
3. 逐字段比较 `cases.json` 中的三个卦、本互变上下卦、动爻及版本来源。

附加约束检查：

- `case_count == 5`
- `question_count == 9`
- 9 个 `question_id` 唯一
- DR-01 明确标记为等价归一化代表数
- 四个 Gate 0 案例的来源时间完全一致
- `include_provenance_client_timestamp == false`
- `include_seasonal_strength == false`
- 不存在辨识、intake、confirmed facts、unknowns、旧建议、clarity report 或旺衰字段

复算结果：`PASS`。

## 使用风险

1. 除 DR-01 外均为合成问题，不能直接代表真实用户满意度。
2. DR-01 的 ChatGPT 解读可作为用户价值参照，不是经典意义上的唯一标准答案，也没有写入冻结案例。
3. 互卦及爻辞如何映射到现实属于解释假设；确定性事实只包括盘面构造和冻结原文。
4. 本数据集只研究“原始问题 + 确定性盘面”是否足以生成高质量解卦，不得借此提前恢复辨识或定问为必经步骤。
