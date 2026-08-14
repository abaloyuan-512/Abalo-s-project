# 阶段1E风险记录

| ID | 风险 | 影响 | 缓解措施 | 状态 |
| --- | --- | --- | --- | --- |
| S1E-R-001 | wire schema仍含服务端不支持关键字 | 高 | 递归静态门 + 三项真实canary | 已关闭：真实3/3通过 |
| S1E-R-002 | 扁平nullable字段削弱互斥约束 | 高 | Pydantic后置validator + 单元测试 + 原始输出留痕 | 专项测试通过，持续监测 |
| S1E-R-003 | Critic schema通过但Proposer仍失败 | 高 | Proposer独立真实canary是保护集生成前硬门 | 已关闭：Proposer通过 |
| S1E-R-004 | Canary案例被误当能力评估 | 中 | Canary仅验证三条路径可执行，不进入正式准确率 | 开放 |
| S1E-R-005 | 新保护集与合同枚举再次不兼容 | 高 | 生成前向独立角色提供公开枚举协议并做双重结构预检 | 开放 |
| S1E-R-006 | 全局错误未短路 | 高 | runner识别`invalid_json_schema`并立即关闭 | 专项验证通过；本次无错误触发 |
