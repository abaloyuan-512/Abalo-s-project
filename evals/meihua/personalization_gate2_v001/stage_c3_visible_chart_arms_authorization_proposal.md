# Gate 2阶段 C.3可见卦象组补齐提案与执行前检查单

## 独立审查结论

Gate 2阶段 C.2已经证明公开合成案例`G2CAL-001/B`可在`gate2_schema_v2`、Prompt v4和实验Validator v3下完成一次真实后台生成并通过验证，但该结果只覆盖无卦象的 B组。它尚未证明同一冻结契约能够处理：

- C组：现实情境＋真实卦象；
- D组：现实情境＋预先冻结的错配卦象。

因此，C.2通过不构成阶段 D、锁定测试集或正式产品集成的工程与产品授权。进入锁定集前的最小下一步，应先在同一公开案例上补齐 C、D两组，使`G2CAL-001`具备可比较的 B/C/D首次原始输出。

## 当前离线准备度

- C.2请求构造器已经支持 B/C/D，并保持 A组关闭；
- C、D请求分别强制携带真实非错配卦象和预先冻结的错配卦象；
- C、D输出必须包含`CHART_FACT`与`REALITY_AND_CHART`解释接榫；
- Fake客户端下的 C、D后台端到端验证已经通过；
- 真实OpenAI SDK加`httpx.MockTransport`下的 B/C/D端到端验证已经通过；
- 新增独立C.3付费入口，默认`NOT_AUTHORIZED`，在授权与逐项确认前不会检查API Key；
- 离线编排测试已验证固定先C后D，且C失败时不会创建D组生成；
- Schema v2、Prompt v4、Validator v3、C.1/C.2历史入口和正式产品均未修改；
- 真实外部模型调用0次，新增费用0美元。

当前状态是`OFFLINE_READY_AWAITING_EXPLICIT_AUTHORIZATION`。本文件只形成提案，不授权或执行任何真实请求。

## 建议的最小授权包络

- 唯一公开合成案例：`G2CAL-001`；
- 固定运行顺序：先 C、后 D；
- 最大生成POST：2次，每组最多1次；
- 每个POST取得response ID后，只轮询该POST对应的同一response ID；
- 任一组失败后立即停止，不运行后续组；
- 模型：`gpt-5.6-sol`；
- 推理档位：`medium`；
- `max_output_tokens`：10000；
- `background=true`、`store=false`、`tools=[]`；
- SDK自动重试：0；
- 自动模型修复：0；
- 失败后的补发或第二次生成：0；
- SDK：独立运行环境精确使用`openai==2.46.0`；
- 锁定测试集、真实用户数据和正式产品：继续关闭。

按仓库中冻结的`openai_gpt_5_6_sol_standard_2026_07_21`价格坐标重新计算：

| 组别 | 单次保守预检上界 |
| --- | ---: |
| `G2CAL-001/C` | 0.475313美元 |
| `G2CAL-001/D` | 0.475307美元 |
| 合计 | 0.950620美元 |

建议本轮总费用硬上限为1.00美元。执行前仍须重新核对官方价格；若任何单次预检或合计预检超过授权硬上限，不得创建POST。产品负责人须声明当时账户余额不少于8.00美元，才能在最坏情况下继续保留至少7美元。

## 执行前检查单

以下条件必须全部通过，任一失败都不得创建生成POST：

1. 分支为`codex/mvp-runnable-baseline`，HEAD与产品负责人授权坐标一致；
2. 工作区除两个已知历史视觉审计截图目录外，没有授权范围外修改；
3. Gate 2定向测试、全仓测试和`git diff --check`全部通过；
4. C.2坐标仍精确为`gate2_schema_v2`、`personalization_gate2_calibration_v4`和`personalization_gate2_validator_v3`；
5. C.1与C.2历史结果、已消费入口、正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate和正式解释知识保持不变；
6. 运行时`openai`版本精确为2.46.0，并记录Python、OpenAI、Pydantic和httpx版本；
7. 输入只允许公开合成案例`G2CAL-001`，组别只能按 C、D顺序运行；
8. 产品负责人明确确认最多2次POST、1.00美元总硬上限、至少7美元保留额和当时声明余额；
9. C、D两次保守预检分别记录，合计不得高于1.00美元；
10. 证据根目录必须全新、尚不存在、位于Git仓库外，不得复用 C.1或C.2目录；
11. API Key只允许在授权硬门之后检查“是否存在”，不得打印、哈希、回显、持久化或写入证据；
12. Provider固定`max_retries=0`，Runner不存在自动修复、自动续写或失败后补发路径；
13. C.2已消费入口继续锁死；C.3使用新的、默认未授权的独立入口；
14. 阶段 D状态仍为未授权，锁定测试集仍为`NOT_CREATED_OR_EXPOSED`。

建议的仓库外证据目录候选为：

```text
D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c3_visible_chart_arms_20260721
```

该路径在提案形成时尚不存在；真正执行前必须再次检查，不能因本记录而跳过“尚不存在”硬门。

## 运行中硬停止规则

- C组最多创建1个后台response；完成后才允许考虑D组；
- D组最多创建1个后台response；两组各自只轮询自己的同一response ID；
- response ID缺失或变化、通信错误、轮询上限、未知状态、`incomplete`、`failed`或`cancelled`立即硬停止；
- Schema解析、实验Validator硬失败或质量失败均保留首次原始输出和Usage后停止；
- C组任何失败都不得运行D组；D组任何失败都不得补发；
- 不得切换案例、不得继续`G2CAL-002`、不得创建锁定测试集、不得进入阶段 D。

## 证据与验收

仓库外证据至少保存：授权坐标、运行清单、公开合成输入、C/D映射ID、请求和版本哈希、每次后台检查点、每组response ID、API状态、首次原始输出、Usage、推理Token、费用或`UNKNOWN`、Schema/Validator结果、跨组比较输入和根SHA-256清单。

工程运行只有同时满足以下条件，才可记为`READY_FOR_BLIND_REVIEW`：

- C、D生成POST各恰好1次，自动重试0次，自动模型修复0次；
- 两组各自的轮询与恢复始终使用其首次取得的同一response ID；
- 两组API终态均为`completed`且取得Usage；
- 两组首次原始输出均直接通过Schema v2和实验Validator；
- 两组总费用不高于1.00美元，账户至少7美元保留线未突破；
- 证据包完整且SHA-256核验通过；
- 锁定测试集、正式产品和阶段 D保持关闭。

`READY_FOR_BLIND_REVIEW`不等于Gate 2或产品价值通过。B/C/D的产品差异必须随后由至少3名互相独立的评审，在不知道组别的情况下使用冻结Rubric判断；本单一公开案例也不能满足锁定集整体通过线。

## 可直接确认的授权条款

产品负责人如决定执行，可明确回复以下整段，并填写当时实际余额：

> 我授权Gate 2阶段 C.3仅对公开合成案例G2CAL-001补齐C组与D组真实后台输出，固定先C后D；最多2次生成POST、每组最多1次，总费用硬上限1.00美元，SDK自动重试0次、自动模型修复0次，任何失败后不得补发或继续下一组。我声明当前账户余额为___美元且不少于8.00美元，并要求至少保留7美元。模型固定gpt-5.6-sol、medium、max_output_tokens=10000、background=true、store=false、tools=[]，运行环境使用openai==2.46.0。证据写入全新、尚不存在、位于Git仓库外的目录；每个POST取得response ID后只允许轮询或恢复该ID。任一通信、状态、Schema、Validator、预算或证据完整性失败都立即硬停止；不得切换案例，不得创建或读取锁定测试集，不得进入阶段D，不得修改正式产品、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或正式解释知识。
