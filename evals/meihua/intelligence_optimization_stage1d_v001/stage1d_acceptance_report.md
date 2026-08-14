# 观象智能能力优化阶段1D验收报告

## 验收结论

状态：`INVALID_RUN_CLOSE_COMPLETE`

阶段1D唯一正式运行无效，不能判为能力通过，也不能判为能力失败：

> 10个Critic请求全部在模型推理前被服务端Structured Outputs Schema校验拒绝。模型没有产生任何辨识内容，因此Critic-first是否能命中关键痛点仍未得到验证。

本阶段保持冻结、不修补、不重跑、不接生产、不进入阶段2。

## 唯一运行事实

- 正式run：`runs/stage1d_single_run_guanxiang_stage1d_20260807t000532z.json`；
- API请求：10次；
- 成功模型调用：0次；
- 生成token：0；
- Proposer调用：0次；
- 模型重试：0次；
- 调用序号：1—10连续；
- 共同错误：`Invalid schema for response_format 'CriticOutput': decision.oneOf is not permitted`。

run中的`run_status=COMPLETED`只表示runner完成遍历并落盘，不代表实验有效。治理结论以本报告和manifest的`INVALID_RUN_CLOSE_COMPLETE`为准。

## 为什么不是能力失败

服务端在推理前拒绝了wire schema，所以没有生成：

- READY或ASK判断；
- M01—M04关键维度；
- M02对“是否继续/投入速度”的区分；
- M04对动机、期望和担心代价的判断；
- 任何瓶颈提议。

因此不能把0个正确案例描述成“Critic 0/10”。能力实际上是0次被测试。

## 根因

阶段1D使用Pydantic判别联合表达严格互斥：

- Critic的`AskOneReview | ReadyReview`生成`oneOf + discriminator`；
- Proposer的FrameValue联合也存在6处同类结构。

本地SDK可以生成合法的strict JSON Schema，Pydantic也能解析该结构，但目标服务端只接受更受限的Structured Outputs方言，并拒绝Critic的`oneOf`。冻结前测试证明了“Schema可生成”，没有证明“目标服务端接受实际wire schema”。

## 治理与可观测性

有效的部分：

- 错误响应正文、错误类型、延迟、调用序号均完整保存；
- 运行锁原子创建，只有一个marker和一个run；
- 错误路径没有调用Proposer；
- 冻结后没有修改Prompt、合同或runner；
- 完整回归1002/1002通过；
- 生产、UI、API、数据库、排盘、解卦和知识库零变更。

执行偏差：第一次400已证明是全局Schema错误，runner仍发送了其余9个必然失败请求。这些不是模型重试且没有token，但新runner必须在首个`invalid_json_schema`后全局停止。

## 保护集

H11—H16已出现在正式run及其预期记录中，不能继续作为后续阶段的封存保护案例。任何新能力实验必须使用全新的独立保护集。

## PMO建议

阶段1D关闭。若继续，建议新建一个极小的阶段1E，只修实验基础设施：

1. wire层使用不含`oneOf/discriminator`的扁平nullable结构；
2. 内部层继续用后置验证保持READY/ASK与GROUNDED/UNKNOWN互斥；
3. 冻结保护集前，分别用无关虚拟输入完成Critic ASK、Critic READY和Proposer真实服务端canary；
4. 首个`invalid_json_schema`必须全局停止；
5. canary通过后才生成并封存全新的3个VETO、3个READY案例。

该建议不构成阶段1E授权，必须由用户确认后才能开始。
