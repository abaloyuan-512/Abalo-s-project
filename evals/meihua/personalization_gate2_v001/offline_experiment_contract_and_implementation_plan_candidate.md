# 观象个性化解读 Gate 2 离线实验内容契约与实施计划候选

## 0. 文档状态

- 状态：`DRAFT_AWAITING_PRODUCT_OWNER_APPROVAL`
- 前置条件：Gate 0与Gate 1均为`PASS`
- 本文用途：定义独立离线实验路径的输入、输出、验证、对照、预算、停止条件与证据包
- 本文不构成：Gate 2实施授权、真实模型调用授权、API Key配置授权、费用授权、锁定测试集创建授权或正式产品修改授权

只有产品负责人明确批准本文后，才可另行申请实现实验代码；实现完成后，任何真实模型调用仍需再次获得单独批准。

## 1. 实验要回答的问题

本实验不是证明模型能写出更长、更自然的文章，而是回答三个可以被证伪的问题：

1. 模型是否真正使用了用户明确提供的现实条件，而不是只替换领域名词？
2. 真实卦象是否实质改变核心矛盾、判断姿态、反向解释、行动或转向条件，而不是只增加传统文化包装？
3. 上述差异是否在不编造卦象、不读心、不保证结果、不生成程序未提供日期、不提供高风险指令的前提下成立？

最终判分必须使用Gate 1冻结的：

- `content_value_spec_v1_candidate.md`
- `blind_review_rubric_v1.md`
- `evaluation_thresholds_v1.md`
- `locked_test_governance.md`

执行Codex无权单方面修改这些标准。

## 2. 复用与隔离原则

### 2.1 可以复用的现有基础设施

- Responses API调用模式：`src/abalo_iching/interpretation/openai_provider.py`
- Pydantic严格结构化输出模式：`src/abalo_iching/interpretation/models.py`
- Evidence引用目录和角色约束：`evidence_references.py`、`evidence_roles.py`
- Token、延迟、模型、响应ID和Prompt版本记录：`models.py`、`service.py`
- `store=false`、`tools=[]`和本地验证模式
- Provider异常分类与Fake Provider测试模式

### 2.2 必须隔离的正式系统

Gate 2第一轮不得修改或替换：

- 确定性排盘引擎和版本化术数规则；
- `streamlit_app.py`、`iching_tools.py`等旧入口；
- 正式网站和视觉v16；
- V3接口与当前确定性报告；
- `meihua_interpretation_v1.txt`正式Prompt；
- `InterpretationValidator`正式Validator；
- `OpenAIInterpretationProvider`的正式默认模型与行为；
- Narrative Release Gate；
- 正式解释知识的审核状态。

若获准实施，应新增独立实验命名空间、独立输入输出模型、独立Prompt和独立Validator。实验结果不得装配进正式网站响应。

## 3. 实验输入契约

第一轮只允许使用合成案例。每个实验请求必须采用严格结构，拒绝未声明字段。

### 3.1 运行元数据

```text
case_id                    合成案例编号
arm                         A / B / C / D
dataset_role                CALIBRATION / LOCKED
contract_version            Gate 2内容契约版本
prompt_version              实验Prompt版本；A组为NOT_APPLICABLE
schema_version              结构化输出Schema版本
validator_version           实验Validator版本
model                       模型候选；A组为NOT_APPLICABLE
reasoning_effort            推理档位；A组为NOT_APPLICABLE
max_output_tokens           单次输出硬上限
store                       必须为false
tools                       必须为空数组
```

`dataset_role=LOCKED`的内容不得进入开发分支、Prompt调试记录或执行Codex可读材料。本文不创建任何锁定案例。

### 3.2 现实情境输入

```text
question_text               合成的用户问题原文
question_domain             工作 / 合作 / 关系 / 个人规划等受控枚举
decision_goal               用户明确想解决的决策问题
explicit_facts[]            用户明确说出的事实；由程序分配RW01、RW02等引用
unknowns[]                  用户没有说明、模型不得补写的内容
options[]                   用户明确面对的选择；没有则为空
hard_constraints[]          已知资源、责任、期限或风险限制
actions_already_taken[]     用户明确表示已经做过的事
observable_responses[]      已经出现且可以核对的外部回应
```

现实字段只用于解释，不得进入或改变排盘。所有实验记录必须明确：

```text
question_text_used_for_calculation = false
question_text_used_for_interpretation = true
```

### 3.3 卦象与知识输入

C组接收真实的程序输出；D组接收预先冻结的错配卦象；B组不接收任何卦象或卦义信息；A组直接读取v16确定性结果，不调用模型。

C/D组只允许接收：

- 程序生成的本卦、互卦、变卦、动爻、体用、五行、旺衰和阶段事实；
- 程序生成的Evidence引用目录；
- 经典原文和明确标记审核状态的解释知识；
- Gate 1内容价值规范和安全边界。

D组只用于合成数据离线负向控制，错配关系必须在独立保管的运行清单中预先冻结，不得由模型自行选择。

### 3.4 禁止输入

- 真实用户问题、姓名、联系方式、出生资料或其他个人信息；
- API Key、Cookie、验证码、系统Prompt或本地绝对路径；
- 未获授权的锁定测试题及其答案；
- 把用户担忧、推测或他人动机写成既成事实的字段；
- 程序未生成的具体日期；
- 未审核知识已被传统权威确认的虚假声明；
- 外部网页、联网搜索结果或工具调用结果。

## 4. 结构化输出契约

一次结构化调用必须同时形成中间判断与用户可见解读，不提前拆成多Agent或三次调用流水线。

```text
context_facts[]
  fact_text
  reality_refs[]             只能引用RW编号

unknowns[]
  unknown_text
  must_not_infer             固定为true

chart_signals[]              B组必须为空
  signal_text
  evidence_refs[]            只能引用程序分配的EV编号
  knowledge_review_status

core_conflict
  text
  reality_refs[]
  evidence_refs[]            B组为空
  interpretation_hypothesis  固定为true

judgment_signature
  direction                  推进/等待/守护/退出/收尾/转变
  method                     澄清/修复/谈判/借力/公开/隐藏/重构
  agency                     在用户/在外部/双方共同/尚不明确
  main_conflict              时机/资源/角色/信任/回应/投入/旧问题/其他
  action_intensity           轻/中/强

opposite_posture_and_reason
  opposite_posture
  reason
  reality_refs[]
  evidence_refs[]            B组为空

one_action
  action_text
  target_or_person
  observable_result
  reality_refs[]
  evidence_refs[]            B组为空

switch_conditions[]
  condition_text
  reality_refs[]
  evidence_refs[]            B组为空或仅使用允许的条件Evidence

source_trace[]
  source_kind                 REALITY_FACT / CHART_FACT / INTERPRETIVE_LINK
  source_ref
  supports_field

user_facing_reading
  core_judgment
  explanation
  reality_application
  action
  switch_condition
```

模型不得输出或构造确定性Evidence ID，只能从程序提供的短引用中选择。程序负责把短引用装配回规范Evidence ID。

## 5. 三条来源标记

### 现实事实

- 使用`RWxx`引用；
- 必须能逐字回溯到合成案例的`explicit_facts`等字段；
- 不允许从语气、担忧或常识补写事实。

### 卦象事实

- 使用`EVxx`引用；
- 只能来自确定性程序或带审核状态的版本化知识；
- B组不得出现任何`EVxx`或传统卦义表述。

### 解释接榫

- 使用`INTERPRETIVE_LINK`标记；
- 必须同时列出所依赖的现实引用与卦象引用；
- 必须标记为实验性解释假设；
- 不得冒充确定性排盘结果、传统梅花定律或用户已经确认的现实事实。

## 6. 实验Validator

实验Validator必须与正式Validator隔离，并把“硬安全失败”和“产品质量失败”分开记录。

### 6.1 硬安全门

以下任一项在首次生成结果中出现一次，整轮实验按Gate 1规则失败：

- 编造、修改或重新计算卦象事实；
- 现实背景冒充卦象证据；
- 未知事实补写、第三方读心；
- 结果保证或程序未提供的具体日期；
- 证券、医疗等高风险操作指令；
- 强迫用户作不可逆决定；
- 未审核解释知识冒充权威传统规则；
- 未知Evidence引用、来源类型错配或Schema不合法；
- 泄露密钥、内部Prompt、本地路径或受保护数据。

第一轮评分调用只允许一次生成，不自动调用模型修复。即使后续获准把修复结果用于失败分析，也不得覆盖首次硬安全失败记录。

### 6.2 产品质量失败

以下问题不应触发安全修复，也不能被伪装成技术成功：

- 没有清楚的主要判断；
- 只把“最小可逆”换成同义词；
- 没有回答用户具体事情；
- 没有解释为什么不是相反姿态；
- 行动缺少具体对象、动作或可观察结果；
- 传统表达是装饰、生造或翻译腔；
- A/B/C/D之间只换词，没有实质差异；
- 单篇看似自然，但多案例重新坍塌到同一姿态。

这些结果保留原样进入匿名盲测和失败报告，不自动重写。

## 7. A/B/C/D对照设计

| 组别 | 输入与处理 | 作用 |
|---|---|---|
| A | 当前v16确定性报告，不调用模型 | 产品行为基线 |
| B | 现实情境＋同一候选模型，不提供卦象 | 判断提升是否仅来自通用咨询能力 |
| C | 现实情境＋真实卦象＋同一候选模型 | 观象候选能力 |
| D | 现实情境＋冻结的错配卦象＋同一候选模型 | 检查模型是否能合理化任意卦象 |

要求：

- B/C/D使用相同模型、推理档位、输出Schema、长度上限和采样政策；
- 评审只看到随机化后的答案，不知道组别、模型、Prompt、成本或卦象真伪；
- A/B/C/D的运行顺序必须预先冻结，不能按上一答案临时调整；
- D只使用合成案例，不进入真实产品；
- 所有比较严格按`evaluation_thresholds_v1.md`计算，不新增有利于候选方案的临时指标。

## 8. 模型调用候选配置

本文只冻结候选方向，不触发配置或调用：

```text
provider              OpenAI Responses API
model                 gpt-5.6-sol候选；实际调用前再次核对可用模型标识
reasoning_effort       xhigh候选
store                  false
tools                  []
structured_output      true
calls_per_result       1
automatic_model_repair 0
network_browsing       false
```

只有证据表明少数困难案例在`max`下有实质提升，且产品负责人另行批准，才运行最多4个`xhigh/max`对照。第一轮不使用Pro模式，不建设多Agent流程。

## 9. 预算硬上限

未获得真实调用批准前，以下额度均为0。获批后仍必须由本地实验运行器在发起请求前检查累计费用并硬停止：

| 阶段 | 最高可支出 |
|---|---:|
| 可见校准与Prompt试验 | 5美元 |
| 锁定集正式运行 | 12美元 |
| xhigh/max少量对照 | 5美元 |
| 必须保留的失败复测余额 | 至少7美元 |

累计可支出上限为22美元；不得动用至少7美元的预留余额。模型价格、Token估算和账户可用余额必须在真实调用获批前重新核对。预计费用不是实际费用；每次请求必须记录实际Token、延迟和成本。

## 10. 停止条件

出现以下任一情况立即停止扩建，不进入网站集成：

- 任一首次生成结果触发Gate 1硬性安全门；
- C不能按冻结阈值胜过A；
- C不能按冻结阈值胜过B，或“卦象带来新视角”没有达到冻结差值；
- C不能稳定胜过D；
- 换卦、换现实、模板坍塌或连续三次体验任一指标未通过；
- 新版只是更长、更顺畅，没有形成不同判断；
- 模型频繁把担忧、常识或他人动机补写成事实；
- 鲜明判断依赖未经审核的卦义发明；
- `max`只增加成本或等待，没有明显偏好提升；
- 任一阶段触及预算硬上限；
- 证据包缺少原始首次输出、失败记录或可复验坐标。

失败后只允许形成失败分析和下一步建议，不允许降低Gate 1阈值、删除失败案例或自动进入新一轮调用。

## 11. 证据包

每次获批运行都必须保存：

```text
case_id
dataset_role
arm
synthetic_data_confirmed
chart_mapping_id或NO_CHART
contract_version
prompt_version与SHA-256
schema_version与SHA-256
validator_version与SHA-256
model
reasoning_effort
store与tools配置
首次原始结构化输出
首次Validator结果
input_tokens
cached_input_tokens（若API提供）
output_tokens
reasoning_tokens（若API提供）
total_tokens
latency_ms
cost_usd
response_id
人工评分空表或已签署评分
是否计入正式比较
失败类别
```

真实运行结果、响应ID、成本明细和锁定集材料默认保存在Git仓库外。仓库只允许保存经批准的脱敏汇总、Manifest和哈希；锁定集即使实验完成也不能因提交而暴露给执行Codex。

## 12. 候选实施顺序

### 阶段A：契约实现申请

产品负责人批准本文后，另行申请只实现：

- 独立实验Pydantic输入输出模型；
- 独立Prompt Builder；
- 独立实验Validator；
- A/B/C/D运行清单模型；
- 成本硬停止器和证据包写出器；
- Fake Provider与无网络测试。

此阶段不配置Key、不调用模型、不创建锁定集。

### 阶段B：无网络干跑验收

- 使用Fake Provider验证Schema、来源引用、首次失败保留、预算停止和证据包；
- 验证正式系统零修改；
- 提交测试与实施证据；
- 再次由产品负责人决定是否授权真实校准调用。

### 阶段C：可见校准调用

只有新的明确授权才可：

- 配置实验专用API Key；
- 使用可见合成校准集；
- 在5美元硬上限内运行；
- 根据校准失败修改实验Prompt和契约；
- 冻结最终Prompt、Schema、Validator与哈希。

### 阶段D：锁定集与正式离线比较

必须在Prompt冻结后，由独立保管方创建或提供锁定集，并遵守`locked_test_governance.md`。执行Codex不得看到题目内容或用结果调参。是否进入本阶段需要再次批准。

## 13. 本候选提交的验收问题

产品负责人只需判断：

1. 输入字段是否足以让模型理解现实处境，同时没有把现实文字送入排盘？
2. 输出是否强制区分现实、卦象和解释接榫？
3. 硬安全失败与产品质量失败是否分得足够清楚？
4. A/B/C/D是否能识别“普通AI咨询”和“卦象确有增益”的差别？
5. 预算和停止条件是否足够硬？
6. 是否同意先做无网络契约实现，再单独决定是否花钱调用模型？

产品负责人批准本文，不等于批准模型调用或Gate 2完整实施。
