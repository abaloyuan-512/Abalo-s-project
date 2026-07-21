# Gate 2阶段 C.1单次真实后台复测结果

## 结论

本次已授权复测只创建1次OpenAI后台响应，并按同一响应ID轮询22次。API终态为`completed`，但首次原始结构化输出未通过既有阶段 C Schema，因此实验结果按`PROVIDER_FAILED`硬停止。

- 案例：公开合成案例`G2CAL-001/B`
- 模型：`gpt-5.6-sol`
- 推理强度：`medium`
- 最大输出Token：10000
- 生成POST：1
- 自动重试：0
- 自动模型修复：0
- API状态：`completed`
- 本地失败代码：`structured_output_schema_invalid`
- 轮询GET：22
- 输入Token：4185
- 输出Token：3841
- 其中推理Token：699
- 总Token：8026
- 按API Usage和当前标准价格计算费用：0.136155美元
- 授权费用硬上限：0.45美元
- 锁定测试集：未创建、未读取、未暴露
- 正式产品：零修改
- 阶段 D：未进入

本次授权已用尽。无论后续如何分析，都不得把失败结果改写为通过，也不得自动生成第二个响应。

## 首个失败

首次原始输出包含8条`REALITY_FACT`来源记录。它们的`link_mode`均为`NOT_APPLICABLE`、`interpretation_hypothesis`均为`false`，但每条仍把自己的`RWxx`放入了仅供解释接榫使用的`reality_refs`。既有`Gate2ExperimentOutput`因此报告8个字段级验证错误：`REALITY_FACT 不得携带解释接榫字段`。

第9条`INTERPRETIVE_LINK`使用`REALITY_ONLY`并引用现实事实；本次硬失败发生在模型输出进入实验Validator之前，不能据此形成产品质量通过结论。

本记录只描述已取得的失败证据，不修改实验Prompt、Schema或Validator，也不提出自动修复。

## 证据

仓库外原始证据目录：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c1_retest_20260721
```

证据目录包含运行清单、公开合成输入、23个不可覆盖后台检查点及其SHA-256、首次原始输出、Usage、响应ID、实验失败和最终摘要。核验结果：23个检查点哈希全部匹配，最终`run_record.json`与证据包manifest中的SHA-256匹配。
