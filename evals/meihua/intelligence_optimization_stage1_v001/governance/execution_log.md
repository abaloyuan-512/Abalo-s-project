# 阶段 1 执行记录

| ID | 计划要求 | 实际动作 | 责任方 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| S1-EX-001 | 用户授权后才能进入阶段 1 | 用户在阶段 0 验收汇报后明确回复“批准” | 用户、主代理 | `manifest.json` | 完成 |
| S1-EX-002 | 建立阶段 1 范围锁 | 冻结只允许辨识最小实验，不改解卦、生产入口或阶段 2 | 主代理、stage1_pmo | `README.md` | 完成 |
| S1-EX-003 | 实现隔离辨识合同 | 新增 `ASK → CONFIRM → COMPLETE` 合同、逐轮原文证据、显式确认/纠正和最多两个不同焦点候选；未接入生产 | 主代理 | `experiment/intake_insight_experiment_v1.py`、专项测试 | 完成 |
| S1-EX-004 | 冻结输入 A/B | A 组只读取阶段 0 快照；B 组使用同一原问题和同四条冻结回答 | 主代理 | 最终候选 run 中 `arm_a_policy`、`same_*` 字段 | 完成 |
| S1-EX-005 | 验证确认与纠正路径 | 完成 4 个主路径和 4 个纠正路径；合成回答只作状态机证据 | 主代理 | `runs/guanxiang_stage1_20260806t132031z_revalidated_v1.json` | 完成 |
| S1-EX-006 | 运行完整回归 | 清除仓库内临时依赖污染后，完整测试 966 项全部通过 | 主代理 | `pytest -q -p no:cacheprovider`，966 passed | 完成 |
| S1-EX-007 | 准备最低负担价值评审 | 生成隐藏甲乙映射的 4 案 × 2 选择材料；仅否定选项需一句原因 | 主代理 | `review/owner_ab_review_packet.md` | 完成 |
| S1-EX-008 | PMO 终验前审查 | 范围、冻结基线、重验真实性和机械门均通过；仅等待产品负责人价值选择 | stage1_pmo | PMO 审查回执、`pmo_checklist.md` | 完成 |
| S1-EX-009 | 产品负责人价值评审 | 完成 4 案 × 2 项选择并提供逐案原因；0 案实现新版双维度明确胜出 | 用户 | `review/owner_ab_review_result.md` | 完成，负向结论 |
| S1-EX-010 | 阶段1验收收口 | 形成“不接生产、不进入阶段2、建议受限阶段1B”的验收报告；PMO以负向结果通过验收 | 主代理、stage1_pmo | `stage1_acceptance_report.md`、PMO终验回执 | 完成 |

文件或测试存在不等于阶段问题已经验证。
