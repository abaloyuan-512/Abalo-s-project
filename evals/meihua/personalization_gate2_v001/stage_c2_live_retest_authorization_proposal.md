# Gate 2 阶段 C.2真实复测授权提案与执行前检查单

## 当前结论

阶段 C.2已完成 Schema v2、Prompt v4、Validator v3和离线后台链路验证。产品负责人明确授权的唯一一次真实复测已经执行并消费，结果为`VALIDATED`；后续不得再次创建生成请求，不创建锁定测试集，也不进入阶段 D。

当前结论为`HARD_STOP_REAL_RETEST_VALIDATED`：C.2结构契约、真实后台Provider/Runner、仓库外证据链和付费入口均已验证；付费入口授权已消费并锁死。当前离线Provider继续只允许Fake客户端或使用`httpx.MockTransport`的OpenAI SDK客户端。

## 授权记录

- 产品负责人指令：按照本提案建议推进；
- 声明账户余额：8.71美元；
- 授权费用硬上限：0.50美元；
- 授权生成POST：最多1次；
- 仓库外证据目录：`D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c2_retest_20260721`；
- 当前授权状态：已授权、已消费；不得再次生成。

## 建议授权包络

- 唯一案例与组别：公开合成案例`G2CAL-001/B`；
- 最大生成POST：1次；
- 最大新增费用：0.50美元硬上限；
- 账户安全线：执行前由产品负责人声明当前余额，且声明余额必须至少为7.50美元，以保留至少7美元；
- 模型：`gpt-5.6-sol`；
- 推理档位：`medium`；
- `max_output_tokens`：10000；
- 后台模式：`background=true`；
- 数据保留：`store=false`；
- 工具：`tools=[]`；
- SDK自动重试：0；
- 自动模型修复：0；
- 失败后的第二次生成：0；
- SDK：单独复测环境精确使用`openai==2.46.0`，约束见`stage_c2_retest_constraints.txt`。

采用与 C.1相同的模型、推理档位和输出上限，只改变已经版本化的 Schema v2和Prompt v4，从而尽量减少比较变量。按当前版本化价格与 C.2 Prompt/Schema计算，单次保守预检为0.468769美元，因此0.45美元不足以覆盖保守上界，建议硬上限为0.50美元。实际费用仍必须以API Usage计算；若没有Usage对象，费用状态记为`UNKNOWN`，不得记为0美元。

## 执行前检查单

以下条件必须全部通过，任一失败都不得创建生成POST：

1. 仓库根目录、分支和HEAD与产品负责人授权坐标一致，工作区没有授权范围外的修改；
2. Gate 2定向测试、全仓测试和`git diff --check`通过；
3. C.1 Schema、Prompt、Validator、历史入口和历史证据保持不变；
4. C.2坐标精确为`gate2_schema_v2`、`personalization_gate2_calibration_v4`和`personalization_gate2_validator_v3`；
5. 运行时`openai`版本精确为2.46.0，并记录Python、OpenAI、Pydantic与httpx版本；
6. 只使用`G2CAL-001/B`公开合成输入，不创建、读取或暴露锁定测试集；
7. 产品负责人已明确确认1次生成、0.50美元硬上限、至少7美元保留余额和当前声明余额；
8. 保守预检费用重新计算且不高于0.50美元；
9. 证据根目录是全新、尚不存在、位于Git仓库外的绝对路径，不得复用 C.1目录，不得位于当前仓库或其子目录；
10. API Key只允许由运行进程在授权后检查“是否存在”，不得打印、持久化、哈希、回显或写入证据；
11. 付费入口的授权常量仍为未消费状态，且命令行确认值与本授权包络逐项一致；
12. Provider固定`max_retries=0`，Runner没有自动修复、自动续写或第二次生成路径。

## 运行中硬停止规则

- POST最多创建1个后台response；
- 首次取得response ID后，所有GET只轮询同一ID；进程恢复也只能继续该ID；
- response ID缺失或变化、通信错误、轮询上限、未知状态、`incomplete`、`failed`或`cancelled`均立即硬停止；
- Schema解析、实验Validator硬失败或质量失败均保留首次原始输出和Usage后停止；
- 任何失败都不得自动重试POST、不得模型修复、不得切换案例、不得继续 C/D组，也不得进入阶段 D。

## 仓库外证据要求

全新证据目录至少保存：运行清单、公开合成输入、请求与版本坐标哈希、每次后台检查点、同一response ID、API状态、首次原始输出、Usage、推理Token、费用或`UNKNOWN`状态、Schema/Validator结果、最终摘要，以及所有证据文件的SHA-256清单。检查点和最终文件必须不可覆盖写入；仓库只允许保存脱敏结论和哈希核验结果，不得提交原始响应或API Key。

## 验收条件

只有同时满足以下条件，才可写为“C.2单次真实复测通过”：

- 生成POST恰好1次，自动重试0次，自动模型修复0次；
- 所有轮询和恢复均使用同一response ID；
- API终态为`completed`且取得Usage；
- 首次原始输出直接通过`Gate2ExperimentOutputV2`，事实项引用数组满足空数组约束；
- 实验Validator硬安全与产品质量检查均通过；
- 实际费用不高于0.50美元，且账户保留余额条件未被突破；
- 证据包完整、SHA-256核验通过；
- 锁定测试集、正式产品和阶段 D仍保持关闭。

API终态`completed`本身不等于实验通过。任何一项不满足，都必须记录精确失败阶段并硬停止，不得将失败改写为通过。

## 可直接确认的授权条款

产品负责人如决定执行，可明确回复以下整段：

> 我授权Gate 2阶段 C.2进行唯一一次真实后台复测，仅限公开合成案例G2CAL-001/B；最多1次生成POST，费用硬上限0.50美元，SDK自动重试0次，自动模型修复0次，失败后不得创建第二个生成。模型固定gpt-5.6-sol、medium、max_output_tokens=10000、store=false、tools=[]，运行环境使用openai==2.46.0。我确认执行前声明的当前账户余额不少于7.50美元，并要求至少保留7美元。证据必须写入全新、尚不存在、位于Git仓库外的目录；取得response ID后只允许轮询或恢复同一ID。任一通信、状态、Schema、Validator、预算或证据完整性失败都立即硬停止；不得创建或读取锁定测试集，不得进入阶段D，不得修改正式产品、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或正式解释知识。
