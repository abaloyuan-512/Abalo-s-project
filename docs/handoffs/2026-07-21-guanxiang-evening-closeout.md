# 观象项目晚间收口与工作电脑续接 · 2026-07-21

> 用途：2026-07-21晚间在家里电脑完成收口，次日在工作电脑从GitHub权威分支无缝续接。本文不授权任何新的OpenAI调用、锁定测试集、阶段 D或正式产品修改。

## 一、远端权威坐标

- 仓库：`https://github.com/abaloyuan-512/Abalo-s-project.git`
- 权威分支：`codex/mvp-runnable-baseline`
- 不从`main`继续；
- C.2真实复测闭环提交：`3cf1e3825a545e14c30cf3e68693d30afb841ef6`；
- C.3全部纯离线准备提交：`e03cf7ea13dac4ab4166e3faa705b0e75fb66dc3`；
- 最终远端HEAD还应包含本晚间交接文档提交，因此必须至少是`e03cf7e`的后继提交。

明天同步后必须用以下命令核对，不得只凭GitHub页面可见判断：

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/codex/mvp-runnable-baseline
git status --short --branch
git log -4 --oneline --decorate
```

本地HEAD与`origin/codex/mvp-runnable-baseline`必须完全一致，历史中必须包含`e03cf7e`与`3cf1e38`。

## 二、工作电脑必须使用新的干净克隆

办公室原目录此前停留在旧提交并保留14个未提交副本。不得在该目录直接`pull`、`reset --hard`、`stash`、删除或覆盖。原目录继续作为待独立安全收口的历史工作区。

建议在办公室仓库父目录新建干净克隆，例如：

```powershell
cd "D:\效率软件--Github\文件储存夹"
git clone --branch codex/mvp-runnable-baseline --single-branch https://github.com/abaloyuan-512/Abalo-s-project.git Abalo-s-project-20260722
cd Abalo-s-project-20260722
git branch --show-current
git rev-parse HEAD
git rev-parse origin/codex/mvp-runnable-baseline
git status --short --branch
git log -4 --oneline --decorate
```

只有新的干净克隆才作为明天Codex任务的工作目录。办公室旧目录的14个副本应另开“办公室重复工作区安全收口”任务逐文件核验，不能混入明天的功能推进。

## 三、今晚已完成的权威成果

### Gate 2阶段 C.2

- 唯一一次真实复测已完成并通过；
- 公开合成案例`G2CAL-001/B`；
- POST 1次，同一response ID轮询16次；
- OpenAI SDK 2.46.0；
- Schema v2、Prompt v4、Validator v3；
- API终态`completed`，本地结果`VALIDATED`；
- 实际费用0.127980美元；
- 自动SDK重试0次、自动模型修复0次；
- C.2授权已消费并锁死，不得再次生成。

### Gate 2阶段 C.3纯离线准备

独立审查确认C.2只真实覆盖B组，不能直接进入阶段D。今晚已完成进入下一次可见比较前的全部无付费准备：

- C组真实非错配卦象请求与D组冻结错配卦象请求已核对；
- C、D两组均通过Fake后台端到端验证；
- B、C、D均通过真实OpenAI SDK加`httpx.MockTransport`端到端验证；
- C/D解释接榫强制`REALITY_AND_CHART`并同时引用`RWxx`与`EVxx`；
- 新增独立C.3入口，默认`NOT_AUTHORIZED`；
- 未授权和缺少逐项确认时，均先于API Key存在性检查硬停止；
- 离线编排固定先C后D，C失败时不运行D；
- 单组最多1次POST，总计最多2次，0自动重试、0自动修复、0失败补发；
- C.1、C.2历史入口和结果保持不变；
- 正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate和正式解释知识均未修改。

## 四、最终离线验证

- Gate 2定向：133项通过；
- 全仓：906项通过；
- `git diff --check`通过；
- 全仓首轮曾出现1次Windows本地HTTP临时服务器连接中止；该用例隔离复跑通过，随后第二轮全仓906项整轮通过；
- 本轮C.3真实外部模型调用0次、费用0美元；
- 锁定测试集未创建、未读取、未暴露；
- 阶段D未进入。

## 五、仓库外证据与不提交资产

C.2完整原始证据只保存在家里电脑的仓库外目录，不提交Git：

```text
D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c2_retest_20260721
```

根manifest覆盖39个文件，manifest SHA-256：

```text
35e5849d7d151a5a77ed435894a48995a128603bf6395ea803cfe52d05c52b81
```

以下两个家里电脑的历史视觉审计截图目录继续保留为未跟踪证据，不提交、不删除；它们不会出现在工作电脑的新克隆中，这是预期状态：

```text
sites/hosted-app/.artifacts/product-audit-2026-07-19/
sites/hosted-app/.artifacts/qa/
```

不得把仓库外原始响应、response ID、API Key或完整敏感内容提交到GitHub或粘贴到聊天。

## 六、明天新任务必须完整读取

按顺序读取：

1. 根目录`AGENTS.md`；
2. 本文件`docs/handoffs/2026-07-21-guanxiang-evening-closeout.md`；
3. `docs/handoffs/2026-07-21-guanxiang-next-workstation-handoff.md`；
4. `evals/meihua/personalization_gate2_v001/README.md`；
5. `evals/meihua/personalization_gate2_v001/stage_c2_retest_result.md`；
6. `evals/meihua/personalization_gate2_v001/stage_c2_status.json`；
7. `evals/meihua/personalization_gate2_v001/stage_c3_visible_chart_arms_authorization_proposal.md`；
8. `evals/meihua/personalization_gate2_v001/stage_c3_status.json`。

读取后先汇报：根目录、分支、HEAD与远端引用、工作区状态、继承的C.2/C.3成果、仓库外证据不可见边界，以及当前授权状态。

## 七、明天唯一允许的下一决策

当前状态：

```text
STAGE_C2 = HARD_STOP_REAL_RETEST_VALIDATED
STAGE_C3 = OFFLINE_READY_AWAITING_EXPLICIT_AUTHORIZATION
STAGE_D_AUTHORIZED = false
LOCKED_TEST_SET_STATUS = NOT_CREATED_OR_EXPOSED
```

在真实调用前，产品负责人必须重新查看当时OpenAI API余额并明确授权。建议包络：

- 只使用`G2CAL-001`；
- 固定先C后D；
- 最多2次POST，每组最多1次；
- 总费用硬上限1.00美元；
- 声明余额至少8.00美元，至少保留7美元；
- 每组取得response ID后只轮询该组同一ID；
- C失败不运行D；任何失败都不补发；
- `openai==2.46.0`、`gpt-5.6-sol`、`medium`、`max_output_tokens=10000`、`background=true`、`store=false`、`tools=[]`；
- 证据写入全新、尚不存在的仓库外目录。

候选目录为：

```text
D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c3_visible_chart_arms_20260721
```

该目录在今晚收口时尚不存在，执行前仍必须再次检查。

没有包含实际余额的明确授权时，只允许只读核对、离线审查和计划；不得发起真实请求。即使C.3以后完成，也不得自动进入阶段D、锁定测试集或正式产品集成。

## 八、明天可直接复制的新任务指令

```text
继续推进“观象”项目。请在新的干净克隆中工作，权威分支为codex/mvp-runnable-baseline。开始前完整读取根AGENTS.md、docs/handoffs/2026-07-21-guanxiang-evening-closeout.md、docs/handoffs/2026-07-21-guanxiang-next-workstation-handoff.md，以及evals/meihua/personalization_gate2_v001/下的README.md、stage_c2_retest_result.md、stage_c2_status.json、stage_c3_visible_chart_arms_authorization_proposal.md和stage_c3_status.json。先只读核对根目录、分支、HEAD、origin跟踪引用、git status和最近提交，确认历史包含e03cf7e与3cf1e38。C.2真实授权已消费并硬停止；C.3只完成离线准备，真实C/D调用未授权。不得读取或输出API Key，不得创建或读取锁定测试集，不得进入阶段D，不得修改正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或正式解释知识。先汇报同步和继承结论；没有产品负责人包含实际余额的明确授权时，不得产生API费用。
```

## 九、2026-07-22阶段 C.3后续结果

本节覆盖本文第七、八节中“C.3等待授权”的旧状态。产品负责人已明确授权并完成唯一一次 C.3真实运行：`G2CAL-001/C`与`G2CAL-001/D`均各1次POST、均`VALIDATED`，总费用0.395065美元，工程状态为`READY_FOR_BLIND_REVIEW`。授权已消费，阶段 D与锁定测试集仍未授权。

最新收口入口为：

```text
docs/handoffs/2026-07-22-guanxiang-stage-c3-closeout.md
```
