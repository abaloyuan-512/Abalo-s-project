# 观象首位真实用户上线前交接（2026-07-23）

## 0. 交接目标与硬期限

- 目标：2026-07-23 12:30 前，让第一位真实用户从可访问的正式入口完成一次新版卦象解读。
- 今晚边界：用户已明确停止继续试卦。不得再发起付费模型调用，不得今晚直接开放为 public。
- 明早交付口径：交付“受控的首位真实用户 Beta”，不是把当前所有者私测页原样公开，也不把它宣称为已经成熟的无限量公开生产系统。

## 1. 唯一可信 Git 坐标

- 远端分支：`origin/codex/owner-preview-private`
- 已核验基线：`8f2d9200656840731aba2ac97f86b848d3d97fd4`
- 该分支包含 `codex/mvp-runnable-baseline` 的 `a2bb68d`，也包含更早的 Gate 2 C.3 与晚间交接提交。
- 当前家庭电脑干净发布副本：`D:\效率工具--GitHub\文件储存夹\Abalo-s-project-20260722`
- 原工作区 `D:\效率工具--GitHub\文件储存夹\Abalo-s-project` 停留在 `codex/mvp-runnable-baseline`，且有两个未跟踪视觉产物目录；不要用它覆盖发布分支。

工作电脑接续命令：

```powershell
cd 'D:\效率工具--GitHub\文件储存夹\Abalo-s-project'
git fetch origin --prune
git switch codex/owner-preview-private
git pull --ff-only origin codex/owner-preview-private
git merge-base --is-ancestor 8f2d9200656840731aba2ac97f86b848d3d97fd4 HEAD
git status --short
```

如果工作电脑从未建立该本地分支，则改用：

```powershell
git switch --track -c codex/owner-preview-private origin/codex/owner-preview-private
```

预期：`merge-base` 返回 0；`status --short` 为空。先阅读本文件，再开始修改。

## 2. 当前线上事实（今晚只读核验）

### Sites

- 项目：`appgprj_6a607f0e1f008191b980cd00c73ca268`
- 线上地址：`https://guanxiang-owner-private-preview.abaloyuan.chatgpt.site`
- 线上版本：3
- 部署状态：`succeeded`
- 环境变量修订：3
- 访问策略：`custom`，仅 1 位允许用户；因此当前不是第一位真实用户可直接使用的公开成品。
- Sites 仅持有开关、所有者邮箱、Render 地址与共享引擎密钥；没有 OpenAI Key。

### Render

- 服务：`srv-d9gbf261a83c73bo93lg`
- 地址：`https://abalo-owner-preview-engine.onrender.com`
- 当前实现已支持异步任务；OpenAI Key 仅配置在 Render。
- 先前直接调用 Render 的异步验收成功，固定模型 `gpt-5.6-sol`，单次实测成本约 `$0.201265`。这证明模型/API 链路可用，但不等于 Sites 全链路已经通过。

## 3. 今晚故障结论

用户在 Sites 页面提交后超过 3 分钟仍显示“正在生成”。今晚日志给出两层证据：

1. Sites Worker 对同一任务持续轮询 `/api/preview/v1/meihua`，HTTP 状态均为 200；不是浏览器到 Sites 的 `Failed to fetch`。
2. Render 两次模型请求都先正常得到 OpenAI HTTP 200，随后约 60.9 秒与 63.2 秒记录 `status=PREVIEW_FAILED audit_id=unavailable`。

前端 `sites/hosted-app/app/preview/OwnerPreviewApp.tsx` 的 `poll()` 存在确定性缺陷：

- `finish()` 遇到非 `SUCCESS` 会抛错；
- `poll()` 的 `catch` 只重新抛出包含“尚未建立”的错误；
- `PREVIEW_FAILED`、校验失败和多数查询异常都被吞掉，随后继续轮询到六分钟。

因此，截图不是“模型仍在生成”，而是“后端已失败、前端没有结束加载态”。Render 的 `PREVIEW_FAILED` 深层原因尚需明早从任务错误字段或增加安全日志定位；目前日志只暴露终态，没有暴露具体校验原因。

## 4. 明早 P0 工作顺序

严格按顺序完成，不要先开放 public：

1. 修复前端终态处理：`PREVIEW_FAILED` 必须立即退出加载态、展示可理解错误并保留任务编号；只有 `202/503` 或明确 `PENDING/RUNNING` 才继续轮询。
2. 增加回归测试：后端返回 HTTP 200 + `status=PREVIEW_FAILED` 时只处理一次，不继续轮询；刷新恢复任务也必须能结束。
3. 定位 Render 失败根因：检查任务错误字段、validator 结果与 OpenAI response 最终状态；不得把原始回复、API Key 或用户问题写入日志/Git。
4. 修复根因后先跑本地测试和构建，再部署 Render/Sites；所有引擎修改必须通过 `pytest`。
5. 做且只做必要的线上全链路验收：从 Sites 页面提交，确认成功结果实际呈现；再验证一个失败路径不会卡死。遵守幂等，刷新/重试不得重复调用模型。
6. 把当前 `/preview` 改造成真实用户入口：去掉“所有者私有校准”“我理解这是所有者私有校准版”等内部文案，保留清晰的费用/隐私/非确定性提示；不得删除旧版入口。
7. 增加最小公开保护：每会话幂等、输入长度限制、并发/频率限制、明确错误与重试路径。OpenAI Key 继续只在 Render。
8. 移动端与桌面端冒烟；11:45 前完成 go/no-go，12:00 冻结版本，12:15 用真实用户设备或无所有者登录态检查入口。
9. 只有上述验收全绿后，才把 Sites 访问策略从 `custom` 改为真实用户可访问的方式，并确认从无所有者登录态能打开。不要为了赶时间直接裸开无限量 public。

## 5. 距离“最终成品”的剩余差距与可行性

当前仍差四类工作：

- 可靠性：终态失败展示、Render 校验失败根因、全链路成功验收。
- 产品化：去掉所有者私测文案，把真实用户需要的解释、等待反馈、错误恢复做完整。
- 访问：当前仅 1 人允许访问；真实用户尚不能直接打开。
- 公开保护：基础限流/并发、幂等、隐私与故障兜底。

判断：如果明早不再改模型策略、不扩展功能，集中完成上述 P0，可以在上午交付一版“受控首位真实用户 Beta”。如果“最终成品”指成熟的长期公开生产系统（完善的滥用防护、监控、运营与大规模并发），无法负责任地承诺在 12:30 前全部完成。首位用户当天应采用受控开放、低并发、可随时回退的版本。

## 6. Gate 2 C.2 证据同步边界

- 家庭电脑目录 `D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c2_retest_20260721` 存在，约 45 个目录项/50 KB。
- 该目录故意位于 Git 仓库外，包含原始回复/response ID；此前交接明确要求不提交 GitHub。今晚没有把它伪装成“已通过 GitHub 同步”。
- 已脱敏的 Gate 2 状态、测试与结论在当前远端分支祖先提交中，足以继续产品修复。
- 如果导师 C2 明确必须读取原始证据，需另行选择经用户授权的私密加密传输或专用私有仓库；不得直接塞进现有 Git 历史。

## 7. 新对话首条指令（可直接粘贴）

> 读取 `docs/handoffs/2026-07-23-guanxiang-first-user-readiness-handoff.md`，确认当前分支是 `codex/owner-preview-private` 且包含 `8f2d920`。目标是在今天 12:30 前交付受控首位真实用户 Beta。先修复 `OwnerPreviewApp.tsx` 吞掉 `PREVIEW_FAILED` 的 P0，并定位 Render 约 61–63 秒后失败的根因；跑测试、构建并完成 Sites 全链路成功/失败验收后，才把真实用户入口开放。不要删除旧版入口，不要把 OpenAI Key 放到 Sites，不要提交原始 C.2 证据或用户数据。昨晚用户已要求停止调用；今天开始后只做必要、幂等的固定 `gpt-5.6-sol` 验收，避免重复付费。

## 8. 明早必须保存的最终证据

- 修复提交 SHA 与远端分支 SHA 一致。
- `pytest`、Sites 构建和前端回归测试结果。
- Render 与 Sites 部署 ID/版本号。
- 无所有者登录态的公开入口截图。
- 一次 Sites 全链路成功的状态、耗时、模型、validator 版本和实际费用；不保存用户原问题与完整模型原文。
- 一次终态失败不会无限加载的证据。

