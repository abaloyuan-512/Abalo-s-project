# 观象智能能力优化阶段1E

状态：`AUTHORIZED_CANARY_DESIGN`

## 唯一目标

先证明Critic与Proposer实际发送的Structured Outputs wire schema能被目标服务端接受，再使用全新封存保护集验证Critic-first辨识能力。

## 固定顺序

```text
扁平wire schema + 内部互斥验证
→ 静态Schema门（禁止oneOf/discriminator）
→ Critic ASK真实服务端canary
→ Critic READY真实服务端canary
→ Proposer真实服务端canary
→ 三项全部通过后才生成全新6案保护集
→ 唯一正式能力实验
```

## 允许范围

- Critic与Proposer的扁平wire schema；
- 内部后置验证，保证ASK/READY和GROUNDED/UNKNOWN/NOT_RELEVANT互斥；
- 三项无关虚拟案例canary；
- M01—M04核心案例；
- canary通过后由独立角色生成的全新3 ASK + 3 READY保护集；
- 隔离测试、runner、调用记录、治理记录与验收报告。

## 禁止范围

- 不修改生产辨识、UI、API、数据库、路由或旧入口；
- 不排盘、不起卦、不解卦、不建设知识库；
- 不进入阶段2；
- 不复用H11—H16作为保护集；
- 不以本地Schema可生成为服务端兼容证明；
- 不在首个`invalid_json_schema`后继续发送同一Schema请求；
- 正式能力run后不改Prompt、合同或重跑。

## 通过标准

### Canary

- Critic ASK、Critic READY、Proposer三项均获得服务端接受并通过内部合同与证据验证；
- 实际发送Schema不含`oneOf/discriminator`；
- 任何Schema兼容错误立即全局停止。

### 能力实验

- M01—M04首次4/4 ASK且命中冻结语义，关键回答后4/4 READY并形成瓶颈；
- 全新保护集首次6/6正确，ASK语义命中，READY不过度追问；
- 零`REVIEW_ERROR`，零重试，调用记录与实际路径一致；
- 完整回归通过，生产零变更。

机械门全绿不自动等于价值通过，最终由PMO逐案语义验收。
