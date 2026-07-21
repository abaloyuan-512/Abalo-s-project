# 观象项目跨主机续接文档 · 2026-07-21

> 用途：从办公室电脑切换到家里电脑。家里电脑以GitHub远端分支为代码事实来源，不复制办公室未提交工作区，不重新执行今天已经完成的真实OpenAI复测。

## 一、GitHub同步坐标

- 仓库：`https://github.com/abaloyuan-512/Abalo-s-project.git`
- 权威工作分支：`codex/mvp-runnable-baseline`
- 不要从`main`继续。
- C.1离线加固提交：`7a08b2efbb75ccc36b21a7aa58dea44caf02fe91`
- C.1真实复测结果提交：`3e48524`
- 本交接本身会形成更新的后续提交；家里电脑最终HEAD应至少包含上述两个提交。

## 二、家里电脑如何同步

### 情况A：家里还没有这个仓库

在准备存放项目的父目录打开PowerShell：

```powershell
git clone --branch codex/mvp-runnable-baseline --single-branch https://github.com/abaloyuan-512/Abalo-s-project.git
cd Abalo-s-project
git status --short
git log -3 --oneline
```

`git status --short`应没有输出；最近提交中应能看到`3e48524`和`7a08b2e`。

### 情况B：家里已有这个仓库

先进入项目目录，先检查再同步：

```powershell
git status --short
git branch --show-current
```

如果`git status --short`有任何输出，先停止，不要自动`reset`、`stash`、覆盖或删除；让新的Codex任务判断这些文件是否是家里电脑自己的未提交成果。

如果工作区干净：

```powershell
git fetch origin
git switch codex/mvp-runnable-baseline
git pull --ff-only origin codex/mvp-runnable-baseline
git status --short
git log -3 --oneline
```

如果本地还没有该分支，用：

```powershell
git switch --track -c codex/mvp-runnable-baseline origin/codex/mvp-runnable-baseline
```

同步后`git status --short`应为空，提交历史应包含`3e48524`和`7a08b2e`。

## 三、家里新Codex任务必须先读

按顺序完整读取：

1. 根目录`AGENTS.md`
2. 本文件`docs/handoffs/2026-07-21-guanxiang-next-workstation-handoff.md`
3. `evals/meihua/personalization_gate2_v001/README.md`
4. `evals/meihua/personalization_gate2_v001/stage_c1_offline_hardening_plan.md`
5. `evals/meihua/personalization_gate2_v001/stage_c1_retest_result.md`
6. `evals/meihua/personalization_gate2_v001/stage_c1_status.json`

随后核对：项目根目录、当前分支、HEAD、`git status --short`和最近3个提交。不得把“能看到GitHub文件”误报成“已经读取办公室仓库外原始证据”。

## 四、今天已经完成，不得重做

- Gate 0与Gate 1均已通过并封板。
- Gate 2阶段A/B离线实现、阶段C失败分析和阶段C.1后台稳定性加固已完成。
- C.1离线加固已提交并推送；后台Provider只创建一次POST，后续只轮询同一response ID，SDK自动重试为0。
- 产品负责人授权的唯一一次C.1真实复测已经执行，授权已经消耗。
- 真实复测只使用公开合成案例`G2CAL-001/B`；没有使用真实用户资料或锁定测试集。
- API终态为`completed`，但首次原始输出未通过既有Schema，最终按`PROVIDER_FAILED`硬停止。
- 失败原因：8条`REALITY_FACT`错误携带非空`reality_refs`，触发`structured_output_schema_invalid`。
- 实际用量：4185 input、3841 output，其中reasoning 699，总计8026 Token。
- 按API Usage计算费用：0.136155美元，低于0.45美元授权硬上限。
- 自动重试0次、自动模型修复0次、第二次生成0次。
- 最终验证：Gate 2定向73项通过，全仓846项通过。
- 阶段D未进入；正式网站、V3、排盘、正式Prompt、正式Validator、Release Gate和解释知识均未修改。

## 五、原始证据的主机边界

GitHub只保存代码、测试、状态、脱敏结论和失败说明。完整原始证据没有提交到GitHub，仍只在办公室电脑：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c1_retest_20260721
```

该目录包含response ID、首次原始输出、Usage、23个后台检查点及SHA-256。已核验23个检查点哈希全部匹配，最终`run_record.json`与证据包manifest哈希匹配。

家里继续做产品决策和代码审查不需要复制原始证据。若以后需要跨主机搬运原始证据，必须另行决定受控传输方式；不得把该目录直接提交到GitHub，不得通过聊天粘贴API Key或完整敏感内容。

## 六、当前停止边界

新的Codex任务不得自动做以下事情：

- 不得再发第二个OpenAI生成请求；一次性入口已由`PAID_RETEST_AUTHORIZATION_CONSUMED=true`锁死。
- 不得自动修改实验Prompt、Schema或Validator来“修好”今天的失败。
- 不得进入阶段D，不得创建、读取或暴露锁定测试集。
- 不得修改正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或正式解释知识。
- 不得把API终态`completed`误写成实验通过；本地Schema验证已经明确失败。

下一步应先由产品负责人判断：是否只做失败原因评审，还是另开一个明确授权的新阶段。没有新的明确授权时，只允许只读分析和计划，不允许产生新的API费用。

## 七、办公室电脑的特殊状态

办公室正式目录：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project
```

该目录当前仍停在旧提交`3314f4b`，并保留了C.1离线实现的14个未提交副本。它们不是家里同步源；GitHub远端分支才是跨主机代码事实来源。

不要在办公室正式目录直接盲目`pull`、`reset --hard`、删除或覆盖。后续若要清理，应新开一个明确的“办公室重复工作区安全收口”任务，先逐文件证明这14个副本已被远端提交完整覆盖，再在用户确认后处理。

办公室当前`gh`命令行未登录，但Git远端凭据可正常push；这不影响家里通过Git同步代码。

## 八、家里新任务启动指令

复制下面整段作为家里Codex新任务的第一条消息：

```text
这是“观象”项目从办公室电脑到家里电脑的跨主机续接。请先完整读取仓库根AGENTS.md、docs/handoffs/2026-07-21-guanxiang-next-workstation-handoff.md，以及evals/meihua/personalization_gate2_v001/下的README.md、stage_c1_offline_hardening_plan.md、stage_c1_retest_result.md和stage_c1_status.json。先只读核对项目根目录、分支codex/mvp-runnable-baseline、HEAD、git status和最近3个提交，确认HEAD至少包含3e48524和7a08b2e。今天唯一一次真实OpenAI复测已经完成并硬停止，授权已消耗；不得再次生成、不得自动修改Prompt/Schema/Validator、不得进入阶段D或创建锁定测试集。请先汇报同步状态、已继承成果、办公室仓库外证据的不可见边界，以及建议的下一步决策，不要直接实施新阶段。
```
