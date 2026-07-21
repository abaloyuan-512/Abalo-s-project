# Gate 2 阶段 C.2离线结构契约加固

## 决策

阶段 C.2只修复阶段 C.1暴露出的“机器可见 Schema 与本地语义校验不一致”问题。它不重写 C.1历史结果，不调用外部模型，不进入阶段 D，也不修改正式产品。

## 已确认的接口断点

C.1首次原始输出中的8条`REALITY_FACT`把自己的`RWxx`写入了`reality_refs`。旧`gate2_schema_v1`导出的 JSON Schema 只声明该字段是最多20项的数组；“事实项必须为空”只存在于 Pydantic 后置校验器中。阶段 C Prompt v3也没有逐字段明确这一空数组要求。

因此，模型可生成满足表面 JSON Schema、但无法通过本地模型校验的对象。这是结构契约可见性缺口，不改变 C.1按`PROVIDER_FAILED`硬停止的结论。

## C.2离线设计

- 新 Schema 坐标：`gate2_schema_v2`；
- 新 Prompt 坐标：`personalization_gate2_calibration_v4`；
- 新 Validator 坐标：`personalization_gate2_validator_v3`；
- 将`source_trace`拆成四个带常量标签的联合分支：`REALITY_FACT`、`CHART_FACT`、`REALITY_ONLY`解释接榫和`REALITY_AND_CHART`解释接榫；
- 事实分支在 JSON Schema 中直接声明`reality_refs`与`evidence_refs`的`maxItems=0`；
- 两种解释接榫分别声明所需引用的`minItems=1`或`maxItems=0`；
- Prompt 用自然语言重复相同约束，明确事实项不得把自己的来源编号重复写入解释引用数组；
- C.1的`gate2_schema_v1`、Prompt v3、Validator v2和付费入口保持不变。

## 权限与停止边界

- 外部模型调用：0；
- 新增API费用：0美元；
- 真实复测授权：否；
- 锁定测试集：不创建、不读取、不暴露；
- 阶段 D：未授权；
- 正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate和正式解释知识：零修改。

## 离线验证结果

- OpenAI SDK严格 Schema 转换保留4个`source_trace`联合分支；
- C.1事实项自引用失败已由离线测试复现，并在 C.2 Schema 边界直接拒绝；
- 新增只接受注入模拟客户端的 C.2后台 Provider，不提供默认OpenAI网络客户端；
- 新增固定0美元预算的 C.2后台 Runner，拒绝 C.1 Provider或任何非模拟Provider；
- 纯 Fake 客户端与真实OpenAI SDK加`MockTransport`两条端到端路径均通过；
- Gate 2定向89项通过；
- 全仓862项通过。

后续若考虑真实复测，必须先完成离线 Schema 导出检查、失败复现测试、Gate 2定向测试和全仓测试，再由产品负责人另行明确授权调用次数与费用上限。
