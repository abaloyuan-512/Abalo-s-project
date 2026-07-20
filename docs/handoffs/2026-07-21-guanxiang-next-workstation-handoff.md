# 观象项目工作电脑续接文档 · 2026-07-21

> 明天在工作电脑的新 Codex 对话中，上传本文件，并发送文末“启动指令”。新对话不得重新做已经完成的内容校准。

## 一、先同步代码

- 仓库：`abaloyuan-512/Abalo-s-project`
- 权威分支：`codex/mvp-runnable-baseline`
- 不要从`main`继续。
- 先 Fetch/Pull 远端该分支，再核对本文件记录的最新 Commit。
- 视觉、排版、美术风格与 v16 继续冻结。

## 二、必须按顺序读取

1. 根目录`AGENTS.md`
2. 根目录`继续观象.md`
3. `docs/handoffs/2026-07-20-guanxiang-personalization-feasibility.md`
4. `docs/handoffs/2026-07-21-guanxiang-gate1-independent-review.md`
5. `evals/meihua/personalization_gate1_v001/README.md`
6. `evals/meihua/personalization_gate1_v001/content_value_spec_v1_candidate.md`
7. `evals/meihua/personalization_gate1_v001/blind_review_rubric_v1.md`
8. `evals/meihua/personalization_gate1_v001/evaluation_thresholds_v1.md`
9. `evals/meihua/personalization_gate1_v001/gate1_status.json`

## 三、已经完成，不得重做

- Gate 0已独立复验`PASS`并封板。
- Gate 1第一轮6组A/B/C全部被产品负责人否决；该失败记录必须保留。
- 后续校准确定了产品声音：以明确、直截了当的判断为骨架，用自然、平实、有少量传统文化气息的中文表达；不得出现翻译腔、术语硬贴或生造比喻。
- 工作、关系、考试三个跨姿态案例已经逐项通过。
- 产品负责人已于2026-07-21明确批准《Gate 1评测通过线V1》。
- 独立复核已确认内容价值规范、跨姿态迁移、三条证据链、安全边界和Rubric维度通过；此前只剩阈值批准与远端冻结候选。
- 锁定测试集仍为`NOT_CREATED_OR_EXPOSED`，不得提前创建或让执行者看到。
- 术数审核者仍为`UNASSIGNED`；实验性判断签名不得冒充传统权威规则。

## 四、当前产品结论

观象当前同质化不是单纯的文风问题，而是：

- 卦象差异只进入解释段，不进入最终行动；
- 用户自由问题未被语义理解；
- 正式 Prompt、Validator 和旧评估题共同奖励“小步、观察、可逆”的单一姿态。

未来实验路径必须保持三条边界：

1. 确定性程序只负责排盘与卦象事实，AI不得参与排盘。
2. 模型只负责理解用户明确提供的现实处境，并完成卦象结构与现实问题的受控接榫。
3. 现实事实、卦象证据和模型解释必须分别标记，不得互相冒充。

## 五、明天允许推进到哪里

若本分支最新远端状态显示 Gate 1 最终独立复核为`PASS`，下一步只允许起草 Gate 2 的离线实验内容契约与实施计划，提交产品负责人批准。

在新的明确批准前，仍然禁止：

- 真实 OpenAI API 或其他模型调用；
- 充值、配置或发送密钥；
- 发送真实用户问题；
- 修改正式网站、V3、正式 Prompt、正式 Validator、排盘引擎或 Release Gate；
- 创建锁定测试集；
- 公开测试、收费或网站集成。

Gate 2候选计划应复用现有 Responses API、Structured Outputs、Evidence、Validator和成本记录基础设施；第一轮只考虑一次结构化调用，不提前建设多Agent或三次调用流水线。

## 六、明天首先要提交的内容

新对话先检查：

- 本地分支是否与远端一致；
- Gate 1最终状态和独立复核记录；
- 工作区是否只有用户已有的`.artifacts`截图产物；
- 是否仍为0次真实模型调用、0美元本轮API费用、正式产品零修改。

确认后，只提交一份 Gate 2 离线实验内容契约与实施计划候选，至少写清：

- 模型输入字段与禁止输入；
- 结构化输出字段；
- 现实、卦象、解释三条来源标记；
- 实验Validator的硬安全门与产品质量失败如何分开；
- A/B/C/D对照如何运行；
- 预算硬上限、停止条件和证据包；
- 明确不修改的正式系统范围。

不得自动调用模型；等待产品负责人再次批准。

## 七、给明天新对话的启动指令

```text
完整读取我上传的《观象项目工作电脑续接文档 · 2026-07-21》，然后按其中顺序读取仓库文件。先同步并核对远端分支codex/mvp-runnable-baseline及最新Commit，不要从main开始。Gate 0已经PASS，Gate 1内容校准与评测通过线已经完成，不得重新做A/B/C口味校准。先核对Gate 1最终独立复核状态；若已PASS，只起草Gate 2离线实验内容契约与实施计划候选，不得调用真实模型、产生API费用、创建锁定测试集或修改正式网站、V3、排盘、正式Prompt、正式Validator和Release Gate。完成后提交证据与计划，由我批准是否进入下一步。
```
