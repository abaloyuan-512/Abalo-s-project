# M1-A立项章程与冻结定义V1

## 1. 状态

```text
M0.5_STATUS=COMPLETE_AND_MERGED
M1_A_CHARTER_STATUS=FROZEN
NarrativeReleaseStatus=UNVERIFIED
should_charge=false
formal_report_persistence_allowed=false
closed_beta_allowed=false
```

正式名称：**M1-A｜基于Python Chart Evidence的解释层离线验证**。

本章程冻结产品目标与边界，不自动授权任何开发批次、真实模型评估、部署、收费、正式报告持久化或用户开放。

## 2. 唯一目标

验证系统能否仅依据Python确定性Chart、Chart Evidence、程序结论和V2四领域结构化语义，生成克制、可追溯、以可核实现实观察和用户自身可控行动为中心的离线Narrative。

## 3. 产品语义权威与输入边界

V2 Contract是领域值和合法组合的唯一产品权威。M1-A不得建立第二套可自行扩展的领域或目标权威。

权威领域：

- `WORK_CAREER`
- `PROJECT_COOPERATION`
- `RELATIONSHIP_COMMUNICATION`
- `PERSONAL_PLANNING`

M1-A只接受V2结构化领域、合法目标和时间窗口。`normalized_question`必须由服务端权威模板生成，`real_world_context`固定为空。不接受自由问题、背景文本、客户端卦象、Evidence、结论、时间判断或真实用户数据。评估输入必须是合成数据，排盘时间和时区必须固定。

Phase 2的`CAREER`、`RELATIONSHIP`、`FINANCE_COOPERATION`仅保留历史兼容，不承担M1-A原生产品语义，V2输入不得先转换为旧枚举。

## 4. 四领域语义基线

### WORK_CAREER｜工作与职业发展

合法目标：识别阻力、规划下一步、准备沟通、观察核实信号。

允许观察工作任务、求职流程、能力准备、反馈、沟通和现实验证；允许提出用户可控、可逆的准备、询问、试验和复盘。禁止保证录用或收入、读心招聘方、替用户作出辞职等不可逆决定，也不得暗中引入投资或关系预测。

### PROJECT_COOPERATION｜项目与合作推进

合法目标：五个V2目标全部允许。

允许观察项目进度、分工、承诺、资源、依赖和沟通边界；允许提出澄清责任、缩小试验、确认资源、记录承诺和设置复盘点。禁止投资、证券、借贷、收益预测和财务保证，不得因旧`FINANCE_COOPERATION`而引入金融语义。

### RELATIONSHIP_COMMUNICATION｜关系与沟通

合法目标：规划下一步、准备沟通、调整投入与边界、观察核实信号。

允许观察用户自身的沟通、边界、投入、反馈和复盘；允许提出非强制、可逆的表达、询问、暂停和边界行动。禁止第三方心理结论、判断对方是否爱用户、预言对方必然行为，以及操控、跟踪或强迫行动。

### PERSONAL_PLANNING｜个人规划

合法目标：识别阻力、规划下一步、调整投入与边界、观察核实信号。

该领域独立覆盖目标安排、优先级、资源与精力分配、节奏、自身承诺与边界、现实信号和复盘点。不得降级映射到职业、关系或合作；禁止医疗诊断、投资建议、法律决定和宿命结论。

## 5. 输出所有权

Program-owned：Chart事实；Evidence及其方向、强度和角色；程序结论；时间阶段与限制；审计和版本信息。

AI-owned：克制的通俗解释；可核实的现实观察条件；用户自身可控、可逆、非强制的行动选项；结果变化条件；复盘问题；不确定性说明。

AI不得输出或复述卦象事实，不得生成、改写或反转程序结论和Evidence方向，不得生成确定性日期或事件时间，不得将混合Evidence强行单向化，不得读心、保证结果或提出医疗、投资、博彩、法律及不可逆强制行动。

M1-A评估最终Assembly和AI Narrative对程序边界的忠实度，不要求AI复述程序事实。

## 6. Knowledge关闭策略

M1-A只验证Chart Evidence路径。Provider可见Knowledge内容、Knowledge Evidence、Canonical文本、`action_tendency`和所有领域boundary字段必须为零；不得存在任何Knowledge回退。

Knowledge审核状态不得影响Synthesis、fixture分类、程序内容或最终Assembly；`knowledge.unreviewed_notice`不得进入M1-A。发现任何Knowledge派生内容必须失败关闭。

已知Knowledge投影缺口不阻断M1-A，单独保留为候选阶段M1-K，本阶段不得设计或开发M1-K。

## 7. 评估集与fixture冻结规则

V2原生基础集至少覆盖17个合法领域—目标组合，17例是下限而非固定总数。fixture从固定时间、固定时区下384个最小同余代表候选中确定性选择，按Evidence方向、EvidenceSufficiency、ConclusionLevel、初始及变化体用关系、动爻阶段、旺衰修饰以及正向、负向、混合和不足状态建立覆盖矩阵。

采用确定性贪心覆盖；并列时选择字典序最小的三数。若17例无法覆盖可达的独立分类单元，每个未覆盖单元增加一例，不机械扩张到68例。每个领域至少设置一个重复生成哨兵。Repair、Provider失败和静态红队不得冒充V2领域覆盖。

评估资产分为：V2原生核心验收、Phase 2历史回归、Validator静态红队、提示注入、Provider失败、Repair前后对照。静态红队和提示注入默认不全部调用真实模型。

## 8. 指标与Release Gate

自动硬指标：AI与程序结论矛盾为0；Evidence方向反转为0；混合Evidence被强制单向化为0；程序事实被AI复述或篡改为0；确定性时间、第三方读心、禁区指令、结果保证、不可逆强制行动为0；Knowledge泄漏为0；多次生成原则性行动冲突为0。允许非原则性的措辞、次序和表达差异。

人工评审维度包括忠实度、可追溯性、现实可核实性、行动可控性与可逆性、领域边界、不确定性表达、克制度和可读性。未形成评分锚点样例前，试运行阈值不得冒充正式科学标准；正式Release Gate阈值必须在锚点校准后另行批准。

M1-A即使通过离线验收，也不自动改变`NarrativeReleaseStatus=UNVERIFIED`及三项false。真实模型、模型参数、预算、环境和数据出口必须另行批准。

## 9. 停止条件与明确排除

出现以下任一情况立即停止：V2语义漂移；Knowledge进入M1-A路径；Provider白名单泄露原始Chart或程序结论；程序所有权被AI接管；历史回归失败；测试出现failed、warning、skip或xfail；需要超出获批文件和批次范围；需要真实用户数据、模型调用或部署。

M1-A不包含Knowledge投影、M1-K、线上服务、真实用户数据、收费、正式报告持久化、封闭测试开放、部署、Release升级、V2 Contract变更或旧Phase 2迁移删除。

## 10. M1-K触发条件

只有M1-A证据表明Chart Evidence输出过于空泛、行动缺乏领域相关性、四领域语义不足以防止跨领域渗透、人工评审证明领域Knowledge有明确增益，或产品负责人决定未来启用领域解释知识时，才可另行讨论M1-K。

产品负责人负责最终语义与范围批准；Codex负责只读技术审计、获批实现和验收证据，不设置项目中不存在的审批角色。
