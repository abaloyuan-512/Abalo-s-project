# 阶段1E决策日志

| ID | 决策 | 依据 | 影响 |
| --- | --- | --- | --- |
| S1E-DEC-001 | wire层不使用Pydantic判别联合 | 阶段1D的`oneOf/discriminator`被服务端拒绝 | 使用扁平required-nullable字段和后置验证 |
| S1E-DEC-002 | 本地静态门与真实canary缺一不可 | SDK可生成合法Schema不代表目标服务端接受 | 三项canary通过前不生成保护集 |
| S1E-DEC-003 | Schema兼容错误全局短路 | 阶段1D首个400后又发出9个必然失败请求 | 首个`invalid_json_schema`立即停止所有后续调用 |
| S1E-DEC-004 | H11—H16永久退役 | 已出现在阶段1D正式run及预期记录中 | 阶段1E必须使用全新案例与ID |
| S1E-DEC-005 | Canary输入采用阳台种植中性场景 | 避免与M01“立即公开启动”语义过近 | 只验证ASK、READY、Proposer三条服务路径，不计能力分 |
| S1E-DEC-006 | 成功计数分层 | 服务端/wire成功不等于业务语义通过 | 分别记录`wire_successful_call_count`与`validated_path_success_count` |
| S1E-DEC-007 | Canary 3/3通过后才生成保护集 | 真实服务端已接受Critic ASK、Critic READY、Proposer两份wire合同 | 放行H17—H22独立生成；canary不计正式能力分 |
| S1E-DEC-008 | 暂停阶段1E正式实验 | 用户真实体验证明当前更基础的问题是跳过辨识后完全不调用AI；用户批准直接解卦优先 | 不执行Stage1E唯一正式run；已生成资产保留但不继续使用 |
