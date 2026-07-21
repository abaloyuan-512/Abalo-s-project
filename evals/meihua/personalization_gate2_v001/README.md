# Gate 2 阶段 A/B 离线实现与阶段 C 可见校准

本目录记录观象个性化解读 Gate 2 的阶段 A/B 状态、阶段 C 授权与治理边界。实现代码位于：

```text
src/abalo_iching/personalization_gate2/
```

自动测试位于：

```text
tests/test_personalization_gate2_offline.py
tests/test_personalization_gate2_plan.py
tests/test_personalization_gate2_stage_c.py
tests/test_personalization_gate2_stage_c1.py
tests/test_personalization_gate2_stage_c1_entry.py
```

## 当前已实现

- 严格的合成现实输入、A/B/C/D分组、卦象Evidence和结构化输出模型；
- `RWxx`现实事实、`EVxx`卦象事实与`ILxx`实验性解释接榫三条来源链；
- 与正式Validator隔离的实验Validator，分别记录硬安全失败与产品质量失败；
- B组`REALITY_ONLY`、C/D组`REALITY_AND_CHART`的来源约束；
- 最终判断签名与用户可见五字段的来源覆盖检查；
- 只允许Fake Provider和零美元费用的阶段A/B预算硬门；
- 单次生成、无自动修复、保留首次原始输出的离线运行器；
- 仓库外证据包写出、UTF-8/LF与SHA-256清单；
- 安全`case_id`与最终解析路径双重检查，阻止证据目录逃逸或写回仓库；
- 首次完整结构化输出的硬安全扫描，以及现实事实文字与唯一`RWxx`的逐字核对；
- 实验Prompt v2、实验Validator v2与Schema v1的运行前版本坐标核验；
- 锁定测试集、疑似敏感输入、仓库内运行证据写入的前置拦截；
- Fake Provider无网络干跑与自动测试。

## 明确未做

- 没有配置或读取API Key；
- 没有调用OpenAI或其他外部模型；
- 没有产生API费用；
- 没有创建、读取或暴露锁定测试集；
- 没有修改正式网站、视觉、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或解释知识审核状态；
- 没有把实验输出装配进正式产品。

以上“未做”描述对应阶段 A/B 历史快照。产品负责人已于 `2026-07-21` 另行授权阶段 C；当前授权与运行状态以 `stage_c_status.json` 为准，`stage_ab_status.json` 不回写为阶段 C 状态。

## 阶段 C 独立边界

- 只使用代码中可见的两组合成校准案例，不创建、读取或暴露锁定测试集；
- A/B/C/D顺序预先冻结；B/C/D每个结果只生成一次，首次失败原样保留，不自动修复或重试；
- 使用隔离的 `OpenAIGate2Provider`、阶段 C Prompt v3和独立预算守门，不修改正式 Provider或正式 Prompt；
- 模型固定为`gpt-5.6-sol`、`xhigh`、`store=false`、`tools=[]`；
- 产品负责人声明账户余额9美元，至少保留7美元，本轮可用费用硬上限为2美元；
- 真实运行证据、响应ID、输出与成本明细只写入Git仓库外的新目录；
- 阶段 C不会自动进入阶段 D、网站集成或Release Gate。

## 阶段 C 当前结果

首次真实运行在`G2CAL-001/B`的OpenAI SDK/Pydantic结构验证路径失败并硬停止：只发生1次生成尝试，剩余5次没有运行，没有自动重试或修复。

产品负责人随后单独授权了最多1次、费用硬上限0.35美元的诊断重试。该次请求在等待OpenAI API响应时超时，Provider按契约立即停止；没有自动重试、没有模型修复，也没有继续其他案例。两次真实尝试均未取得响应ID和Usage对象，因此本地无法确认准确费用，状态必须记为`UNKNOWN`而不是已确认0美元。详见`stage_c_failure_analysis.md`。

## 阶段 C.1离线稳定性加固

阶段 C.1离线加固已完成；产品负责人随后单独授权一次低成本真实复测：

- 新增隔离的后台Provider与Runner，保持旧阶段 C同步Provider和历史证据不变；
- 后台POST最多创建1次生成，随后只按同一响应ID执行GET轮询；
- 每次状态变化写入仓库外不可覆盖检查点，并为每个检查点保存SHA-256；
- 支持进程恢复后只轮询已有响应ID，不创建新的模型生成；
- `incomplete`、轮询上限或通信失败均保留响应ID、API状态、Usage、推理Token、费用和不完整原因；
- 候选参数为`gpt-5.6-sol`、`medium`、`max_output_tokens=10000`；保守预估单次最多0.423050美元；
- 本次复测最多1次生成调用，新增费用硬上限0.45美元，账户声明余额8.85美元并继续保留至少7美元；
- 付费入口必须显式确认上述额度、使用全新仓库外目录并检查`OPENAI_API_KEY`存在性；
- 仍只允许公开可见合成案例，不创建、读取或暴露锁定测试集，不进入阶段 D。

具体契约和当前状态见`stage_c1_offline_hardening_plan.md`与`stage_c1_status.json`。

该次授权已使用：只创建1次后台响应并轮询同一响应ID。API终态为`completed`，Usage和费用均已取得，但首次原始输出因8条`REALITY_FACT`错误携带非空`reality_refs`而未通过既有Schema，最终按`PROVIDER_FAILED`硬停止。实际费用0.136155美元，自动重试和自动修复均为0。详见`stage_c1_retest_result.md`。

## 阶段 C.2离线结构契约加固

阶段 C.2已获得仅离线实施授权，用于修复 C.1暴露出的机器可见 Schema 缺口：旧 Schema 未把`REALITY_FACT`和`CHART_FACT`的空引用数组要求暴露为 JSON Schema 约束。

- 新增隔离的`gate2_schema_v2`、阶段 C.2 Prompt v4和实验 Validator v3坐标；
- `source_trace`改用四个带常量标签的联合分支，让事实项空引用和两类解释接榫的引用要求直接出现在 JSON Schema；
- Prompt 同步明确事实项不得把自己的`RWxx`或`EVxx`重复写入解释引用数组；
- 新增仅接受注入模拟客户端、固定0美元预算的 C.2后台 Provider/Runner，并通过 Fake 与 SDK `MockTransport`端到端验证；
- C.1历史 Schema、Prompt、Validator和已消耗的付费入口均不修改；
- 本阶段外部模型调用0次、费用0美元，真实复测与阶段 D仍未授权。

设计与状态见`stage_c2_offline_contract_plan.md`和`stage_c2_status.json`。

## 本地验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_plan.py tests\test_personalization_gate2_offline.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_stage_c.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_stage_c1.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_stage_c1_entry.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_stage_c2_contract.py
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

阶段 C当前仍停在失败分析状态，不自动进入阶段 D。锁定集与正式离线比较仍需产品负责人再次明确批准，并由独立保管方执行。
