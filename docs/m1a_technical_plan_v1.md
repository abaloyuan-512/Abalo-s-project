# M1-A技术实施与验收计划V1

## 1. 审批状态与执行摘要

```text
M1_A_CHARTER_STATUS=FROZEN
M1_A_TECHNICAL_PLAN_STATUS=APPROVED_WITH_MANDATORY_AMENDMENTS
M1_A_BATCH_1_AUTHORIZED=true
M1_A_BATCH_2_AUTHORIZED=false
M1_A_BATCH_3_AUTHORIZED=false
M1_A_MODEL_EVALUATION_AUTHORIZED=false
```

计划以现有V2 Application Contract为唯一产品语义入口，建立窄的M1-A Intake边界，并从`ConclusionSynthesizer`提取共享Chart-only确定性核心。Phase 2继续使用原Knowledge包装层，M1-A不创建第二套合成算法。

## 2. 三项强制修订

1. **M1ARequest不得包含`MeihuaChart`。** 实施对象必须至少拆分为排盘前的`M1AIntake`与排盘后的`M1AProgramContext`；Chart只在本地确定性计算和投影函数中短暂存在。
2. **不得形成`interpretation`反向依赖`application`。** 依赖方向固定为V2 Application Contract → M1-A Application Boundary → Interpretation Chart-only Core。领域解析、17/3组合和问题模板仍由Application权威逻辑负责。
3. **安全Evidence不得压缩为少量通用空话。** 接口必须保留确定性生成、Canonical Evidence一对一私有映射、方向、强度、允许角色和条件差异，并支持私有映射哈希和Provider可见载荷哈希；不得泄露原始Chart结构。Batch 1只冻结接口约束，不实现最终命题模板。

## 3. 当前差距与唯一技术方案

现有`InterpretationRequest`包含旧Phase 2领域、自由文本、背景和完整Chart；`InterpretationService`会选择Knowledge并把它传给Synthesis、Catalog、Renderer、Prompt和Validator；`ConclusionSynthesizer`把`unreviewed_notice`加入warnings。这些结构不能直接作为M1-A入口。

Knowledge关闭方向比较：

| 方向 | 修改范围 | Phase 2兼容 | 重复服务风险 | 零Knowledge可证明性 | 测试与维护 |
|---|---|---|---|---|---|
| A. 全服务显式disabled模式 | 中到大 | 条件分支影响较广 | 低 | 中 | 分支组合多 |
| B. 伪造严格空`KnowledgeSelection` | 小 | 表面兼容 | 低 | 低；Canonical与notice语义仍耦合 | 容易产生假关闭 |
| C. 完整复制窄服务 | 大 | 隔离较好 | 高 | 高 | 重复实现、长期漂移 |
| D. Application窄边界＋共享Chart-only纯核心 | 小 | 高；旧包装不变 | 低 | 高；签名与依赖可静态证明 | 最低 |

唯一推荐并批准的方案是D：M1-A不进入现有Knowledge驱动的完整`InterpretationService`；共享纯Chart合成核心由历史包装和M1-A共同调用。后续Provider路径按独立白名单逐层增加，但不得复制完整服务。

## 4. V2内部请求边界

`M1AIntake`只包含：`question_id`、V2 `question_domain`、V2 `decision_goal`、V2 `time_horizon`、服务端生成的`normalized_question`、`question_template_version`、`contract_version`、合成数据标记。

Application层先使用现有V2枚举、合法组合与模板完成解析和生成，再构造`M1AIntake`。构造边界重新核对规范问题和版本，不接受字符串伪装枚举、旧Phase 2枚举、客户端自由问题、背景、三数、Chart、结论或Evidence。

原始三数停在V2 Application的确定性排盘边界；`MeihuaInput`和`MeihuaChart`不得进入Intake。Chart完成本地计算后仅作为临时参数投影为`M1AProgramContext`。

`M1AProgramContext`只承载Synthesis、程序私有Chart Evidence副本、当前为空的未来Provider Evidence白名单槽位和必要规则/引擎版本。它不含Chart、MeihuaInput、三数、real_world_context、Knowledge或产品领域枚举，且不得直接序列化为Provider输入。

## 5. Knowledge关闭设计

M1-A Chart-only核心签名只接受`MeihuaChart`，不接受`KnowledgeSelection`，不调用`select_knowledge`，不读取审核状态，不生成`unreviewed_notice`。Phase 2历史入口继续接收Knowledge，并仅在共享核心结果上保持原notice包装，因此历史warnings顺序、结论、Evidence ID、规则ID和序列化不变。

Batch 1通过签名检查、依赖检查、抛错替身、不同Knowledge状态不影响输出、notice隔离和历史等价测试证明零Knowledge。后续批次如发现任何KnowledgeEvidence、Canonical文本、action tendency、boundary或Knowledge派生notice，必须失败关闭。

## 6. Provider输入白名单计划（后续批次，未授权实施）

未来Provider仅允许看到：V2领域、目标、时间窗口；服务端`normalized_question`；程序裁剪的安全Evidence命题、短引用、方向、强度和允许角色；Program-owned限制；必要版本信息与可复验哈希。

明确禁止原始三数、Chart身份或结构、卦名卦序、互卦变卦、动爻、体用、旺衰和五行明细、程序结论文本与等级、程序时间、Knowledge、real_world_context、客户端自由文本和真实用户数据。`safe_evidence_content`是程序裁剪后的Evidence命题，不等于开放原始Chart。

快照测试必须同时采用正向字段白名单和递归禁词/禁字段断言，验证Evidence Catalog哈希、Program约束和版本完整性。Batch 1不创建Catalog、Prompt、Validator或Provider载荷。

## 7. fixture生成与冻结计划（后续批次，未实际生成）

使用产品负责人批准的固定排盘时间和`Asia/Shanghai`时区，从三个模数的384个最小同余代表生成候选Chart。生成脚本只负责确定性排盘、分类、贪心选择和哈希，不调用模型。

候选标签包括Evidence方向、EvidenceSufficiency、ConclusionLevel、初始/变化体用关系、动爻阶段、旺衰修饰及正向、负向、混合、不足状态。按“新增覆盖单元最多”确定性贪心选择，并列时选择最小三数。

先为17个合法领域—目标组合各分配至少一个fixture；未覆盖可达独立分类时，每单元增加一例。每个领域至少一个重复生成哨兵，语义边界强的组合优先分配混合、不足或条件性案例。fixture记录版本、输入、Program输出和哈希，并形成覆盖矩阵与人工审核产物。

不调用模型即可验收：384候选确定性、分类与选择复现、17组合分配、Program哈希、Knowledge零影响、Provider白名单快照骨架和历史回归。

## 8. 分层测试计划

| 组 | 目的与输入 | 关键断言与失败条件 | 模型 | 写仓库 | M1-A证据 |
|---|---|---|---|---|---|
| A Contract/输入 | V2全枚举及非法值 | 17合法、3非法；模板不漂移 | 否 | 否 | 是 |
| B V2→内部表示 | 结构化V2输入 | 类型和值保持；无旧枚举、Chart、背景和三数 | 否 | 否 | 是 |
| C Knowledge零影响 | 同Chart、不同Knowledge/抛错替身 | 不调用Knowledge；输出与状态无关；无notice | 否 | 否 | 是 |
| D Provider白名单/快照 | 未来安全载荷 | 仅白名单字段；禁字段为零；双哈希可复验 | 否 | 仅版本化快照 | 是 |
| E Program所有权/哈希 | 固定fixture | Chart、结论、时间及版本哈希不因Narrative变化 | 否 | 否 | 是 |
| F Evidence角色/Assembly | 角色化安全Evidence | 方向、强度、角色、条件与一对一映射保持 | 否 | 否 | 是 |
| G Validator静态红队 | 80条静态攻击资产 | 禁止输出全部拒绝；不冒充领域覆盖 | 否 | 否 | 是 |
| H 提示注入 | 16条静态注入资产及受控子集 | 指令不越权、不泄露程序私有内容 | 静态否；真实子集另批 | 否 | 是 |
| I Provider失败 | 超时、空响应、畸形响应 | 失败关闭、不收费、不持久化 | 否/Mock | 否 | 是 |
| J Repair一次 | 首次非法、一次修复 | 最多一次；二次失败即关闭 | 否/Mock | 否 | 是 |
| K Release Gate | 全结果状态 | UNVERIFIED及三项false不变 | 否 | 否 | 是 |
| L Phase 2回归 | 历史fixture与Mock | 旧Knowledge、Prompt、Validator、Catalog、Runner不变 | 否 | 否 | 兼容证据 |
| M 全仓 | 全部测试 | failed/warning/skip/xfail均为0 | 否 | 否 | 是 |

测试统一禁用pytest缓存和Python字节码，使用合成数据，不访问外部模型，不写入仓库外未批准位置。

## 9. 最小开发批次

### Batch 1｜V2内部请求边界与Chart-only确定性核心

唯一目标：建立`M1AIntake`、`M1AProgramContext`与共享Knowledge-free Synthesis核心。候选修改仅限`synthesis.py`、必要导出；候选新增仅限两个M1-A模块、测试和冻结文档。验收为17/3组合、零Knowledge、无反向依赖、Phase 2兼容、全仓通过。无需模型，可单独回滚。出现范围外依赖立即停止。

### Batch 2｜安全Evidence投影与Provider输入最小化（未授权）

唯一目标：实现程序生成的一对一安全Evidence、角色化Catalog与Provider白名单快照。禁止改变Engine、V2 Contract和Knowledge。必须单独批准，不得由Batch 1自动进入。

### Batch 3｜Assembly、静态防线与受控离线评估（未授权）

唯一目标：完成M1-A Prompt/Validator/Assembly、失败与Repair门禁、fixture资产和批准后的受控模型证据。真实模型仍需独立批准；不得改变Release Gate。

## 10. 历史兼容、Release与停止条件

Phase 2旧枚举、InterpretationRequest、Knowledge选择、Catalog、Renderer、Prompt、Validator、Provider、Repair、live eval和序列化均保持历史行为；V1、V2正式页面及Phase 3B不得修改。共享核心重构必须由历史测试证明输出不变。

任一分层测试失败、出现warning/skip/xfail、Knowledge泄漏、反向依赖、Provider禁字段、历史序列化漂移、需要修改禁止资产或需要模型/真实数据时立即停止。Batch 1通过不代表Narrative验证通过，也不改变Release状态。

本计划不存在新的产品语义阻断项。M1-A产品立项已经冻结；仅获批批次可以实施，不得自行进入下一批次。
