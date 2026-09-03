# 观象 V73 Gate 0 五类台账 v0.1

状态：`PARKED_BY_PO_SCOPE_CLARIFICATION`

更新时间：`2026-08-18`（Asia/Shanghai）

基线：`guanxiang-p1-p9-v72-frozen-20260817` / `12c5f4307b16e97a86cd5f8b13969ef61478f6d7`

## 1. WBS 台账

统一规则：`VERIFIED` 只表示独立验收通过；`CLOSED` 表示对应 PO 决定也已登记。
本表的验收文件均为候选，须由 PMO、反向论证官和 QA 复审后才能改变状态。

所有 WBS、缺陷、风险、决策和证据必须通过 ID 双向互引。证据条目必须记录采集
时间、基线、验证人、位置、SHA-256、数据分类及支持的 WP/DEF/RISK/DEC。候选文件
最终修订后重新计算哈希，不得登记编辑前哈希。

| WP | 状态 | Owner | 独立验证 | 前置依赖 | 输入 | 输出 | 验收条件 | DEF/RISK/DEC/EVD | 阻塞 | 更新时间/变更人 |
|---|---|---|---|---|---|---|---|---|---|---|
| G0-01 | VERIFIED | /root | PMO、反向、QA | 无 | V72冻结、tag、commit、部署、健康 | V72闭环证据 | tag/commit/摘要/健康身份一致 | EVD-G0-V72-001 | 无；三方PASS | 2026-08-18 /root |
| G0-02 | VERIFIED | 三独立角色 | PO | V72、v0.1 | v0.1、AGENTS、仓库证据 | 三份独立审查 | 角色、日期、结论可追溯 | EVD-G0-REVIEW-001 | 无 | 2026-08-18 PMO |
| G0-03 | CLOSED | /root | PMO、反向、QA、PO | G0-02 | v0.1阻断与审查 | v0.2治理控制 | 三方PASS且PO批准 | DEC-G0-SCOPE-001 / EVD-G0-REVIEW-001 | 无 | 2026-08-18 PO |
| G0-04 | BLOCKED | /root | QA、反向、PO | G0-03、G0-01 | v0.2、V6、AGENTS、接口契约 | V73 Spec+产品证据口径 | 范围/类型/三入口/分母冻结并获PO批准 | RISK-G0-SCOPE-001 / DEC-G0-AUDIENCE-001、DEC-G0-SAFETY-001、DEC-G0-QUALITY-001 / EVD-G0-SPEC-001、EVD-G0-RUBRIC-001 | 内容PASS；候选决定待PO | 2026-08-18 /root |
| G0-05 | BLOCKED | PMO+/root | QA、反向 | G0-03 | 十WP、证据、PO决定 | 五类台账 | ID双向互引、历史、哈希完整 | 全部ID / EVD-G0-LEDGER-001 | 内容PASS；待PO后生成final manifest与提交 | 2026-08-18 /root |
| G0-06 | BLOCKED | /root | QA、反向、PO | G0-03、G0-05 | CNY150、官方价格、模型上限、计量模块 | 预算控制 | 最大责任、金额+次数、预留/并发/恢复均冻结 | DEF-G0-002 / RISK-G0-COST-001 / DEC-G0-BUDGET-001、DEC-G0-BUDGET-002 / EVD-G0-BUDGET-PO-001、EVD-G0-PRICE-001、EVD-G0-BUDGET-001 | 内容PASS；待PO预算参数与G0-05 | 2026-08-18 /root |
| G0-07 | BLOCKED | /root | 反向、QA | G0-04、G0-06 | V73数据流、接口、预算、安全边界 | 威胁模型+固定用例 | 正/隐晦/邻近/并发/故障用例完整 | DEF-G0-001、DEF-G0-005 / RISK-G0-CRED-001、RISK-G0-SAFE-001 / DEC-G0-SAFETY-001 / EVD-G0-THREAT-001、EVD-G0-SECURITY-001 | 内容PASS；待PO安全决定与前置WP | 2026-08-18 /root |
| G0-08 | BLOCKED | /root | QA、反向、PO | G0-03、G0-05 | 表/日志/反馈、TTL、AGENTS | 数据治理 | 字段/根目录/Provider/保留/删除/授权冻结 | DEF-G0-003 / RISK-G0-DATA-001 / DEC-G0-DATA-001 / EVD-G0-DATA-001 | 内容PASS；待PO数据决定与保管人 | 2026-08-18 /root |
| G0-09 | BLOCKED | /root | QA、PO | G0-03、G0-04 | 两路径、设备、V72测试基线 | QA矩阵+评分口径 | 测试门、设备版本、分母和证据冻结 | DEF-G0-004 / RISK-G0-MOBILE-001、RISK-G0-EVIDENCE-001 / DEC-G0-QUALITY-001 / EVD-G0-QA-001、EVD-G0-RUBRIC-001 | 内容PASS；待PO质量决定与真机 | 2026-08-18 /root |
| G0-10 | BLOCKED | /root | QA、反向、PO | G0-04、G0-06、G0-07、G0-08 | 预算、安全、数据、GET/POST、部署 | 双层停止+KS演练 | 唯一状态码、60秒、运行中语义、权限/恢复冻结 | DEF-G0-006 / RISK-G0-COST-001、RISK-G0-DATA-001 / DEC-G0-STOP-001 / EVD-G0-QA-001 | 内容PASS；待PO停止决定、替补与权限演练 | 2026-08-18 /root |

状态历史：

- `2026-08-18` PMO 建议建立五表，G0-05 进入 `IN_PROGRESS`。
- `2026-08-18` PO 批准 v0.2 与 CNY 150 硬上限；G0-03 进入 `CLOSED`。
- `2026-08-18` 三方首轮复审后 G0-01 获 PMO/反向/QA `PASS`，移为 `VERIFIED`；
  G0-04～10 因实质缺口和前置依赖移为 `REWORK`。当前为 3/10。
- `2026-08-18` 第二轮与定向反证确认治理内容 `PASS/CONDITIONAL_PASS`，文本阻断
  已关闭；G0-04～10 移为 `BLOCKED`，只等待PO决定、资源、final manifest与版本提交。

## 2. 缺陷台账

| ID | 严重度 | 事实 | Owner / WP | Gate 1 前关闭条件 | 证据/风险 | 状态 |
|---|---|---|---|---|---|---|
| DEF-G0-001 | S0 | Direct Reading V2 与 intake 现为 owner-only | Gate1执行代理 / G0-07 | 限次凭证、绑定与IDOR/重放测试通过 | EVD-G0-SECURITY-001 / RISK-G0-CRED-001 | OPEN |
| DEF-G0-002 | S0 | 现有预算仅计量，hard limit与次数上限为空 | Gate1执行代理 / G0-06 | 原子金额+次数预留覆盖intake/high | EVD-G0-BUDGET-001 / RISK-G0-COST-001 | OPEN |
| DEF-G0-003 | S1 | 隐私页30分钟与后端TTL45分钟冲突 | Gate1执行代理 / G0-08 | 文案与实现统一并有测试 | EVD-G0-DATA-001 / RISK-G0-DATA-001 | OPEN |
| DEF-G0-004 | S1 | Sites package test漏2项deterministic测试 | Gate1执行代理 / G0-09 | pnpm test稳定执行不少于60项 | EVD-G0-QA-001 / RISK-G0-SCOPE-001 | OPEN |
| DEF-G0-005 | S0 | 高风险输入未有Direct V2输入级安全退路 | Gate1执行代理 / G0-07 | HR+旁路组全部0排盘/0Provider | EVD-G0-SECURITY-001 / RISK-G0-SAFE-001 | OPEN |
| DEF-G0-006 | S0 | 停止开关未形成匿名链路双层闭环 | Gate1执行代理 / G0-10 | KS-01～10 fixture/mock通过 | EVD-G0-QA-001 / RISK-G0-COST-001、RISK-G0-DATA-001 | OPEN |

这些是 Gate 1 的实施缺陷，不因 Gate 0 文档通过而关闭。

## 3. 风险台账

| ID | 风险与影响 | 触发器 | 控制 | Owner | 关联ID | 状态 |
|---|---|---|---|---|---|---|
| RISK-G0-COST-001 | CNY150穿透（S0） | 新预留使实际+未结预留越线；计价不符；孤儿未知 | 1:8、最大预留、CNY145自动上限、CNY5缓冲、fail closed | /root+QA | G0-06、G0-10 / DEF-G0-002、006 / DEC-G0-BUDGET-001、002 | CONTROL_CANDIDATE |
| RISK-G0-CRED-001 | 跨用户读取或多次生成（S0） | 无效/复用凭证、IDOR、异ID并发 | 128-bit、摘要、7天、一次体验、绑定/撤销 | Gate1执行代理 | G0-07 / DEF-G0-001 / DEC-G0-AUDIENCE-001 | OPEN |
| RISK-G0-SAFE-001 | 高风险被当正常占问（S0） | 任一入口出现风险而进入排盘/Provider | 成年人、三入口、本地安全门、正/隐/负例 | Gate1执行代理 | G0-07 / DEF-G0-005 / DEC-G0-SAFETY-001 | OPEN |
| RISK-G0-DATA-001 | 敏感内容泄露或超期（S0/S1） | 进入Git/Provider、跨用户、超期 | 仓库外双库、白名单、删除授权、manifest | PO数据保管人 | G0-08、G0-10 / DEF-G0-003、006 / DEC-G0-DATA-001 | CONTROL_CANDIDATE |
| RISK-G0-MOBILE-001 | 微信/键盘/弱网阻断主链路（S1） | M02/M04/M05/M06任一真实主链路失败 | M01～M06、双路径、固定弱网、恢复 | Gate2执行代理 | G0-09 / DEC-G0-QUALITY-001 | OPEN |
| RISK-G0-SCOPE-001 | 误改规则、V72、旧入口或弱化测试（S0） | 禁止路径diff或基线测试倒退 | 允许/禁止清单、diff、1474+、60+ | PMO+QA | G0-04、G0-09 / DEF-G0-004 | CONTROL_CANDIDATE |
| RISK-G0-EVIDENCE-001 | 小样本/选择性反馈造成虚假结论 | 剔除退出、混合版本、挑选输出 | 固定分母、分cohort、单次生成、盲评 | PMO | G0-04、G0-09 / DEC-G0-QUALITY-001 | CONTROL_CANDIDATE |

## 4. 决策台账

| ID | 决策 | 决策人 | 状态 | 证据/备注 |
|---|---|---|---|---|
| DEC-G0-SCOPE-001 | 批准治理计划 v0.2，继续完成 Gate 0 | PO | APPROVED | 2026-08-18 用户消息 |
| DEC-G0-BUDGET-001 | 本轮公测全部付费 API 总责任硬上限 CNY150 | PO | APPROVED | 不构成真实调用授权 |
| DEC-G0-BUDGET-002 | 1:8保护换算；CNY145自动上限、5缓冲、90预警；次数/并发/子预算 | PO | APPROVED_DEFERRED | 未来公测储备；不授权网站改造或真实调用 |
| DEC-G0-AUDIENCE-001 | 仅成年人；一人一张7天一次体验凭证；默认不跨设备 | PO | APPROVED_DEFERRED | 未来公测储备；当前不实施 |
| DEC-G0-SAFETY-001 | 固定高风险类别统一安全退路，不排盘、不调 high | PO | APPROVED_DEFERRED | 未来公测储备；当前不改网站功能 |
| DEC-G0-DATA-001 | 运行任务45分钟；元数据/联系/研究证据按冻结期限删除 | PO | APPROVED_DEFERRED | 数据保管人为PO；当前不实施新收集 |
| DEC-G0-QUALITY-001 | 固定启动/完成分母、评分线与3对×3人盲评 | PO | APPROVED_DEFERRED | 未来公测储备；当前只做布局巡检 |
| DEC-G0-STOP-001 | 双层停止；生成停止可查已安全完成任务，隐私停止禁GET；人工60秒 | PO | APPROVED_DEFERRED | 未来真实公测前再确定替补操作人 |
| DEC-G0-SCOPE-002 | 不得擅自修改网站代码/版本；下一步仅准备移动端布局，具体变化逐项授权 | PO | APPROVED | 当前最高优先级范围决定 |
| DEC-G0-DEVICE-001 | 华为Pura 70 Ultra为主真机；iPhone先仿真，声明支持则发布前必须真机 | PO | APPROVED | 不验则标“未验证、不承诺支持” |

## 5. 证据台账

| ID | 采集时间/验证人 | 位置 / SHA-256 | 数据分类 | 支持ID/结论 |
|---|---|---|---|---|
| EVD-G0-V72-001 | 2026-08-18 / root、PMO、反向、QA | `guanxiang-v72-release-closure-evidence-2026-08-18.md` / `PENDING_FINAL_MANIFEST` | PUBLIC_TECHNICAL | G0-01；线上commit对齐V72 |
| EVD-G0-REVIEW-001 | 2026-08-18 / PMO、反向、QA、PO | `guanxiang-v73-gate0-review-record-v0.1.md` / `PENDING_FINAL_MANIFEST` | INTERNAL_GOVERNANCE | G0-02、G0-03 / DEC-G0-SCOPE-001 |
| EVD-G0-BUDGET-PO-001 | 2026-08-18 / PO、PMO | 决策台账 / `PENDING_FINAL_MANIFEST` | INTERNAL_GOVERNANCE | G0-06 / DEC-G0-BUDGET-001；无调用授权 |
| EVD-G0-PRICE-001 | 2026-08-18 / root、PMO、QA | OpenAI Sol/Luna官方模型详情页 / 外部来源 | PUBLIC_PRICING | G0-06 / RISK-G0-COST-001 |
| EVD-G0-THREAT-001 | 2026-08-18 / root；独立复审待完成 | 仓库外稳定证据根；threat=`11AF...0D0`，manifest=`8FD0...DE81` | INTERNAL_SECURITY_SYNTHETIC | G0-07 / RISK-G0-CRED-001、RISK-G0-SAFE-001 |
| EVD-G0-SPEC-001 | 2026-08-18 / root | V73 Spec V1 / `PENDING_FINAL_MANIFEST` | PUBLIC_GOVERNANCE | G0-04 / DEC-G0-AUDIENCE-001、DEC-G0-SAFETY-001 |
| EVD-G0-LEDGER-001 | 2026-08-18 / root、PMO | 本文件 / `PENDING_FINAL_MANIFEST` | INTERNAL_GOVERNANCE | G0-05 / 全部ID |
| EVD-G0-BUDGET-001 | 2026-08-18 / root、QA | 预算控制 v0.1 / `PENDING_FINAL_MANIFEST` | INTERNAL_GOVERNANCE | G0-06 / DEF-G0-002 / RISK-G0-COST-001 |
| EVD-G0-SECURITY-001 | 2026-08-18 / root | 匿名安全边界 v0.1 / `PENDING_FINAL_MANIFEST` | INTERNAL_SECURITY_SYNTHETIC | G0-07 / DEF-G0-001、005 |
| EVD-G0-DATA-001 | 2026-08-18 / root | 数据治理 v0.1 / `PENDING_FINAL_MANIFEST` | INTERNAL_GOVERNANCE | G0-08 / DEF-G0-003 / RISK-G0-DATA-001 |
| EVD-G0-RUBRIC-001 | 2026-08-18 / root | 产品证据口径 v0.1 / `PENDING_FINAL_MANIFEST` | PUBLIC_GOVERNANCE | G0-04、G0-09 / DEC-G0-QUALITY-001 |
| EVD-G0-QA-001 | 2026-08-18 / root、QA | QA停止计划 v0.1 / `PENDING_FINAL_MANIFEST` | INTERNAL_QA_SYNTHETIC | G0-09、G0-10 / DEF-G0-004、006 |

## 6. 当前 Gate 结论

Gate 0 当前是 `CONDITIONAL_PASS / HOLD / NO-GO_FOR_GATE_1`。已验证工作包为
3/10；G0-04～10 内容通过但被外部条件阻塞。只有三角色最终签署、上述 `PROPOSED`
决定由 PO 批准、设备/运维资源
确认并形成版本提交后，PMO 才能将工作包依赖序列移为 `VERIFIED` 并请求 Gate 0 GO。

预算状态：真实调用 `0`，已结算 `CNY0`，未结预留 `CNY0`；CNY150 是硬上限，
在 Gate 1 未获授权且预算控制未实现前，不把它表述为可立即消费余额。

## 7. 产品负责人范围纠偏

决策 `DEC-G0-SCOPE-002`（2026-08-18，PO）：

- 当前网站功能、辨识、定问、排盘和解卦逻辑保持不变；
- 不得擅自修改网站代码或网站版本；任何具体改动须由PO逐项授权；
- 下一步只允许移动端布局的只读巡检和拟议清单；
- PO批准六项公测治理候选决定，但它们只作为未来公测储备，不授权实施匿名、安全、
  数据、预算或停止功能改造；
- 数据保管人由PO本人担任；
- 当前真实设备为华为Pura 70 Ultra（鸿蒙）；iPhone先使用参考视口仿真；后续若声明
  支持iPhone Safari/微信，发布前必须真机验收，否则标“未验证、不承诺支持”；
- 当前布局准备不要求替补部署操作人；未来真实公测前再决定；
- CNY150保持当前硬上限，若不足须先报告并取得新的明确数值批准。

原V73 Gate 0治理内容保持 `CONDITIONAL_PASS/HOLD` 历史证据，但项目线已停放。
当前项目坐标转为“移动端布局适配准备 / M0”，不得从本台账直接派发Gate 1代码。
