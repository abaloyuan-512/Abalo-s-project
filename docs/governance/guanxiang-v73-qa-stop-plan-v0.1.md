# 观象 V73 QA、设备矩阵与停止演练 v0.1

状态：`GATE_0_CANDIDATE`

对应工作包：`WP-G0-09`、`WP-G0-10`

## 1. 零费用 QA 前置

所有自动化验收使用独立进程，先清空 `OPENAI_API_KEY`，记录 V72 tag、基线提交、
被测提交、工作区状态、Python、Node 和 pnpm 版本。Gate 0 的真实模型调用必须为 0。

## 2. Python 发布门

```powershell
$env:OPENAI_API_KEY = ""
.\.venv\Scripts\python.exe -m compileall src tests scripts
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src/abalo_iching --cov-report=term-missing --cov-fail-under=94
.\.venv\Scripts\python.exe -m pytest --cov=src/abalo_iching/interpretation --cov-report=term-missing --cov-fail-under=92
.\.venv\Scripts\python.exe scripts\verify_wheel_install.py
.\.venv\Scripts\python.exe scripts\verify_interpretation_wheel_install.py
.\.venv\Scripts\python.exe scripts\demo_meihua_interpretation_offline.py
.\.venv\Scripts\python.exe scripts\red_team_interpretation_validator.py
.\.venv\Scripts\python.exe -m pip check
```

通过：不少于 V72 的 1474 项且新增后不倒退；0 failed/error；总覆盖率 ≥94%；
interpretation ≥92%；red-team 80/0；两项 wheel、demo、compileall、pip check 通过；
`streamlit_app.py`、`iching_tools.py` 未修改；真实调用和费用为 0。

Gate 1 定向测试不能替代全量门，至少包含 hosted API、conditional intake、Direct
Reading V2/V3、Direct High、稳定性、知识保护和确定性金标测试。

## 3. Sites 发布门

当前 `package.json` 的 test 脚本漏掉
`tests/deterministic-cast-request.test.ts` 的 2 项。Gate 1 完成前必须修正脚本。

修正前显式验收：

```powershell
Push-Location sites\hosted-app
pnpm install --frozen-lockfile
pnpm run build
node --test tests\preview-poll.test.mjs tests\rendered-html.test.mjs `
  tests\result-presentation.test.mjs tests\page8-model.test.mjs `
  tests\direct-reading-v2-route.test.mjs
pnpm exec tsx --test tests\deterministic-cast-request.test.ts `
  tests\direct-reading-v2-preview.test.tsx
pnpm run lint
Pop-Location
```

正式门：`pnpm install --frozen-lockfile`、`pnpm test`、`pnpm run lint`；当前基线至少
执行 60 项，新增后只能增加；必须证明 deterministic 的 2 项已执行。依赖以
`pnpm-lock.yaml` 为准。

## 4. Gate 1 新增安全测试

- 凭证签发、7 天过期、撤销、次数耗尽和链接预览不消费。
- POST、GET、intake 校验同一凭证；任务与凭证绑定；A 不可读 B。
- 原始凭证不进入日志、响应或持久化。
- intake/high 同 ID 同载荷并发只产生一次相应模型调用。
- 同 ID 不同载荷拒绝，模型调用为 0。
- 完成、失败、丢失、刷新、返回和恢复不重新 POST；GET 调用数恒为 0。
- intake/high 统一金额与次数预留；预算、限流、凭证或 DB 故障 fail closed。
- 下一预留超过 CNY 150 总上限或 CNY 145 自动分配上限时原子拒绝。
- 高风险合成用例进入冻结安全退路；不排盘、不调用 high。
- 响应白名单、日志脱敏、V6 防回退和旧入口保护。

## 5. 设备矩阵

| ID | 环境 | 必测范围 |
|---|---|---|
| D01 | 1366×768，Chrome/Edge 无痕 | 凭证、CLEAR、ASK_ONCE、刷新恢复 |
| M01 | 375×667，桌面 Chrome/Edge DevTools 响应式仿真（iPhone SE 视口） | 两路径、键盘、溢出；不替代真实 Safari |
| M02 | 390×844，真实 iPhone Safari | 两路径、安全区、返回、分享、继续追问 |
| M03 | 360×800，Android Chrome 仿真 | 两路径、键盘、触控、滚动 |
| M04 | 412×915，真实 Android Chrome | 两路径、弱网、返回、横屏冒烟 |
| M05 | 真实 iPhone 微信内置浏览器 | 两路径、凭证、恢复、P8/P9 |
| M06 | 真实 Android 微信内置浏览器 | 两路径、凭证、恢复、P8/P9 |

测试开始前冻结并记录真实设备型号、系统版本、浏览器/微信版本、屏幕尺寸和网络。
任一必测真实设备无法完成主链路即 S1，不等待“高频”才升级。

Gate 0 资源登记（未填不得签署 G0-09）：

| ID | 型号 | OS | Safari/Chrome | 微信 | 资源确认人 |
|---|---|---|---|---|---|
| M02 | `TBD_PO_DEVICE` | `TBD` | `TBD` | 不适用 | `TBD_PO` |
| M04 | `TBD_PO_DEVICE` | `TBD` | `TBD` | 不适用 | `TBD_PO` |
| M05 | `TBD_PO_DEVICE` | `TBD` | Safari内核 `TBD` | `TBD` | `TBD_PO` |
| M06 | `TBD_PO_DEVICE` | `TBD` | Chrome内核 `TBD` | `TBD` | `TBD_PO` |

每项覆盖：P3/P4/P6 键盘、横向溢出、底部安全区、触控、返回/刷新/滚动恢复、
P8 五幕、P9 寄语与操作、`prefers-reduced-motion`、无悬停降级。弱网固定为
400ms RTT、400Kbps 下行、200Kbps 上行；恢复只能继续 GET，新增 POST 为 0。

## 6. 证据格式

仓库外：

```text
<GX_EVIDENCE_ROOT>/V73-PB1/Gate-<n>/<WP-ID>/<run-id>/
  environment.json
  commands/
  test-results/
  screenshots/
  recordings/
  network/
  budget/
  manifest.json
  MANIFEST.sha256
```

仓库内只保存脱敏总结和 manifest 哈希。manifest 记录时间、tag/commit、环境、完整
命令与退出码、测试数量、调用/预算、文件哈希、数据分类、脱敏结果和三角色签署。

## 7. 停止开关

两层控制：

- Sites：V73 公测总开关，以及既有 intake/high 预览开关；
- Python 引擎：`ABALO_CONDITIONAL_INTAKE_ENABLED` 与
  `ABALO_DIRECT_READING_V2_ENABLED`。

缺配置和重启默认关闭。Sites 控制、预算、限流或凭证存储异常时，必须在到达引擎
前 fail closed；引擎开关提供第二层停止。

两种停止模式：

- 生成停止：禁止新 intake/high POST；持有效凭证的已安全完成任务允许 GET。
- 隐私紧急停止：POST、GET、intake 全部关闭，直至影响评估完成。

进行中任务不自动重试；最大预留保持到对账。自动停止不得自动恢复。

运维权限：主操作人候选为 PO；替补为 `TBD_PO_DEPLOY_OPERATOR`。两人都必须在
Gate 0 关闭前用零费用 fixture 证明拥有 Sites 与 Python 部署配置的关闭和验证权限。
开发、QA、反向论证代理不得因掌握代码而被视为线上操作人。

收到人工 STOP 后 60 秒内完成双层关闭并验证。冻结并发下，触发瞬间最多已有1个
high和2个intake跨过Provider边界并可能完成；停止后不得发出任何新Provider调用，
已经完成intake也不得继续触发high。
隐私紧急停止不得向用户释放停止后返回的结果，最大预留保持到对账。

## 8. 演练用例

每案使用合成请求，记录开关前后值、HTTP 状态、任务状态迁移、intake/high 调用数、
预算预留/结算 delta、日志脱敏检查和证据哈希。

| KS-ID | 前置与请求 | 期望状态码 / 状态迁移 | 调用与预算 delta / 证据 |
|---|---|---|---|
| KS-01 | 所有 V73 配置缺失；分别 POST intake/high | 503；无任务，`DEFAULT_OFF` | 调用0、预留0；配置快照+网络记录 |
| KS-02 | Sites/引擎 fixture 开；合法凭证请求 | 202；`NONE→QUEUED→COMPLETED` | fake调用各1、按fixture预留后结算；任务记录 |
| KS-03 | Sites总开关关、引擎开；分别 POST | 503；`SITES_STOPPED` | 引擎/Provider调用0、预留0；边界日志 |
| KS-04 | Sites开、Python两生成开关关；分别 POST | 503；`ENGINE_STOPPED` | Provider调用0；若已预留则原子撤销并留审计；双侧日志 |
| KS-05 | 一个请求跨Provider边界后触发生成停止，再重放同ID POST | 原请求可完成一个终态；停止后的POST统一503；已有结果只经GET恢复 | 新调用0、新预留0；并发轨迹 |
| KS-06 | 已安全完成任务分别处于生成停止/隐私停止后 GET | 生成停止=200；隐私停止=503统一不可枚举响应 | GET Provider调用0、预留0；两模式网络证据 |
| KS-07 | 凭证/预算/限流/任务库逐一注入故障 | 503；`CONTROL_UNAVAILABLE`，不创建可执行任务 | Provider调用0、预留0；四组故障记录 |
| KS-08 | 构造下一预留越过CNY145/CNY150、次数上限及并发1/2 | 429+`Retry-After`；`BUDGET_OR_LIMIT_STOPPED` | 新调用0、新预留0；原子边界和并发记录 |
| KS-09 | 停止状态下重启 Sites 与 Python，且旧业务环境变量仍为true | 503；V73总开关/停止位优先，保持停止 | 调用0、预留0；重启前后配置/健康记录 |
| KS-10 | 已停止；未获授权尝试恢复，再依次登记QA/反向/PMO/PO并跑fixture | 未授权恢复=503；授权后fixture=202/完成 | 未授权0调用0预留；授权后仅fake调用；四签与审计记录 |

自动预算熔断必须在每次 Provider 调用前即时生效。恢复需要 PMO、反向论证、QA
和 PO 决定。
