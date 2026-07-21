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

## 九、Gate 2阶段 C.2后续结果（覆盖本文件早先的 C.1停止状态）

本节是本文件的最新状态；凡前文与本节冲突，以本节为准。

- C.2已完成`gate2_schema_v2`、Prompt v4、Validator v3、离线网络隔离、真实后台Provider/Runner和付费入口加固；
- 产品负责人授权的唯一一次 C.2真实复测已经执行并消费；
- 只使用公开合成案例`G2CAL-001/B`，生成POST恰好1次，随后只轮询同一response ID 16次；
- OpenAI SDK为2.46.0，模型`gpt-5.6-sol`、`medium`、`max_output_tokens=10000`、`store=false`、`tools=[]`；
- API终态`completed`，首次原始输出直接通过 Schema v2和实验Validator，最终结果`VALIDATED`；
- 输入5826 Token、输出3295 Token，其中推理475 Token，总计9121 Token；
- 实际费用0.127980美元，低于0.50美元授权硬上限；
- 自动SDK重试0次、自动模型修复0次、第二次生成0次；
- Gate 2定向109项、全仓882项通过；
- 锁定测试集未创建、未读取、未暴露；正式产品与阶段 D均未进入；
- C.2付费授权已经锁死，后续任务不得再次创建任何OpenAI生成请求。

C.2完整原始证据只保存在本机仓库外目录：

```text
D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c2_retest_20260721
```

根证据manifest覆盖39个文件，逐文件SHA-256全部匹配；manifest自身SHA-256为：

```text
35e5849d7d151a5a77ed435894a48995a128603bf6395ea803cfe52d05c52b81
```

后续任务必须先读取`stage_c2_live_retest_authorization_proposal.md`、`stage_c2_retest_result.md`和`stage_c2_status.json`，并把`HARD_STOP_REAL_RETEST_VALIDATED`视为当前权威状态。包含本节、C.2实现、测试和结果记录的提交应作为后续远端权威坐标；若同步后的远端分支不包含`stage_c2_retest_result.md`，必须停止并重新核对同步来源，不得据此重复真实调用。

## 十、Gate 2阶段 C.3离线准备（不构成真实调用授权）

在 C.2真实复测通过后完成独立顺序审查：C.2只覆盖公开合成案例`G2CAL-001/B`，尚未真实验证同一 Schema v2、Prompt v4和Validator v3下的 C组真实卦象输入与D组冻结错配卦象输入。因此不能从 C.2直接进入锁定测试集或阶段 D。

当前已完成的纯离线准备：

- C、D两组分别通过Fake客户端后台端到端验证；
- B、C、D三组分别通过真实OpenAI SDK加`httpx.MockTransport`的端到端验证；
- 独立C.3付费入口默认未授权，且授权与逐项确认均先于API Key存在性检查；
- 离线编排已验证固定先C后D，C失败时不会运行D；
- C组强制真实非错配卦象，D组强制预先冻结的错配卦象；
- C/D解释接榫强制为`REALITY_AND_CHART`，且必须同时引用现实与卦象事实；
- Gate 2定向133项、全仓906项通过；
- 本轮真实外部模型调用0次、费用0美元；C.2已消费入口继续锁死；
- 锁定测试集未创建、未读取、未暴露；阶段 D与正式产品均未进入。

下一真实候选步骤被收窄为 C.3：只补齐`G2CAL-001/C`和`G2CAL-001/D`，固定先C后D，最多2次POST，总费用硬上限建议1.00美元，任一失败立即停止。当前状态仍是`OFFLINE_READY_AWAITING_EXPLICIT_AUTHORIZATION`，不得因“继续推进”等一般性指令推导出付费授权。

后续任务必须先读：

```text
evals/meihua/personalization_gate2_v001/stage_c3_visible_chart_arms_authorization_proposal.md
evals/meihua/personalization_gate2_v001/stage_c3_status.json
```

未经产品负责人按提案条款明确确认，不得创建 C.3真实生成请求；无论是否授权 C.3，阶段 D、锁定测试集和正式产品集成都继续需要新的独立批准。
