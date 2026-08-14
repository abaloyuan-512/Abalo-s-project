# 阶段1D风险记录

| ID | 风险 | 影响 | 缓解措施 | 状态 |
| --- | --- | --- | --- | --- |
| S1D-R-001 | Blind Critic脱离Proposer后逢案必问 | 高 | 3个以上READY保护案例必须全部ALLOW | 开放 |
| S1D-R-002 | M02式复合谓词仍被当成一个选择 | 高 | 核心M02必须区分是否继续与投入速度，并保留给定前提 | 开放 |
| S1D-R-003 | 把执行参数误判为新问题定义 | 高 | 明确时间窗口不等于持续频率，普通执行粒度不足以VETO | 开放 |
| S1D-R-004 | 互斥Schema仍无法防止证据误引 | 高 | 保留逐字引用验证与字段级错误记录 | 开放 |
| S1D-R-005 | 失败调用usage不可得 | 中 | 至少记录调用编号、角色、错误类型、原始响应（若有）、延迟和usage可用性 | 开放 |
| S1D-R-006 | 保护集泄漏或重复调参 | 高 | 合同与runner冻结后才打开，单次锁阻止重跑 | 开放 |
| S1D-R-007 | OpenAI私有Schema转换辅助函数版本耦合 | 低 | 当前依赖环境已用strict schema与19项测试验证；合同与runner哈希冻结 | 接受，仅限隔离实验 |
| S1D-R-008 | 机械dimension命中但语义仍偏离 | 高 | PMO逐案核对definition、question、前提和证据；机械全绿不自动判PASS | 开放 |
| S1D-R-009 | 独立保护集与合同枚举命名空间不一致 | 中 | 结构预检在任何调用前拦截；仅允许一次全局机械映射并保留完整谱系 | 已关闭：revision 2最终预检通过 |
| S1D-R-010 | 本地strict JSON Schema可生成但服务端不接受其方言 | 高 | 原方案仅递归检查required/extra，未做真实服务端canary | 已发生：Critic `oneOf`被服务端拒绝，阶段INVALID |
| S1D-R-011 | Proposer wire schema含6处同类`oneOf/discriminator` | 高 | 本run未到达Proposer；合同审查确认潜在同类失败 | 未验证；若新阶段继续必须先独立canary |
| S1D-R-012 | 全局确定性Schema错误未立即短路 | 中 | runner只按案例fail closed，未识别所有案例共用的不可恢复合同错误 | 已发生：首个400后又发出9个必然失败请求；无token但属执行偏差 |
