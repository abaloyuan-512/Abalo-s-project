# 阶段1D执行记录

| ID | 计划要求 | 实际动作 | 证据 | 状态 |
| --- | --- | --- | --- | --- |
| S1D-EX-001 | 用户授权后开始 | 用户明确采纳阶段1D建议并授权自主推进 | `manifest.json` | 完成 |
| S1D-EX-002 | 设置独立PMO、合同审查与保护集角色 | 三个子任务分别执行范围闸门、只读合同审查与保护集封存 | 协作记录 | 完成 |
| S1D-EX-003 | 冻结前不得读取保护集期望 | 主代理直到Prompt、合同和runner冻结后才执行结构预检；未在冻结前读取正文或期望 | `manifest.json` | 完成 |
| S1D-EX-004 | 冻结Critic-first合同与runner | 实现Critic先行、VETO不调用Proposer、READY后才提议、互斥联合类型和失败关闭 | 合同、runner、专项测试 | 完成 |
| S1D-EX-005 | 修复冻结前审计阻断 | 修复HTTP成功Schema失败留痕、原子运行锁、保护集范围偏差和严格资产预检 | 合同、runner、19项测试 | 完成 |
| S1D-EX-006 | 冻结前专项与完整回归 | 专项19/19；完整pytest 1002/1002 | pytest输出、`manifest.json` | 完成 |
| S1D-EX-007 | 登记全部冻结哈希 | Prompt、合同、runner、测试、核心输入/回答和三份保护资产均登记SHA256 | `manifest.json` | 完成 |
| S1D-EX-008 | PMO冻结许可 | PMO二次复核确认无代码阻断，允许唯一正式运行 | PMO协作记录 | 完成 |
| S1D-EX-009 | 首次保护资产结构预检 | 全部hash通过；在marker和模型调用前发现`expected_dimension`命名空间不兼容 | 预检错误、PMO记录 | 完成（已拦截） |
| S1D-EX-010 | 一次兼容性冻结修订 | 独立heldout角色新建v2文件，只按全局映射修改`expected_dimension`；原文件保留 | v1/v2 expectations及SHA、字段级校验摘要 | 完成 |
| S1D-EX-011 | 第二次且最终的冻结前预检 | revision 2全部hash、6案3/3、ID覆盖、标签、维度和答案结构通过；仍无runs目录或marker | 预检输出、`manifest.json` | 完成 |
| S1D-EX-012 | 用户明确批准唯一正式模型实验 | 2026-08-07用户回复“批准执行阶段1D唯一正式模型实验” | 对话授权、marker | 完成 |
| S1D-EX-013 | 执行唯一冻结run | 10个Critic请求均在推理前被服务端400拒绝，错误为`decision.oneOf is not permitted`；0成功、0 token、0 Proposer | single run文件 | 完成（无效） |
| S1D-EX-014 | 零重试并关闭 | 未修改冻结Prompt、合同或runner，未发起第二次run；保护集退役 | manifest、PMO终验 | 完成 |
| S1D-EX-015 | 运行最终完整回归 | 完整pytest 1002/1002通过 | pytest输出、验收报告 | 完成 |
