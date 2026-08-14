# 执行记录

| 记录 | 计划要求 | 实际动作 | 责任方 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| EX-001 | 建立阶段 0 范围锁 | 冻结只允许诊断集、盲评材料和治理记录 | 主代理 | `README.md` | 完成 |
| EX-002 | 盘点可用案例 | 只读检查 Gate 0、Live Eval、Gate 1、Gate 2 和数据库结构 | 主代理、case_inventory | `source_index.md` | 完成 |
| EX-003 | PMO 独立监管 | PMO 只提交符合性、风险和验收清单，未修改项目目标 | stage0_pmo | `pmo_checklist.md` | 完成 |
| EX-004 | 固定 4/4/2 分层 | 建立 10 例索引，失败、中间候选、保护组比例符合方案 | 主代理 | `case_index.json` | 完成 |
| EX-005 | 建立三类评价表 | 用户价值、易学结构、产品边界三表分离 | 主代理、diagnostic_schema | `review/` | 完成 |
| EX-006 | 组装完整案例正文 | 10 例正文与参考判断包已组装；4 个中间候选补齐完整确定性盘面、历史输出和证据映射 | 主代理、case_inventory | `cases.json`、`baselines/current_reading_safe_snapshots.json` | 完成 |
| EX-007 | 冻结当前辨识基线 | 用当前冻结的 contract、Prompt 与模型对 4 个合成案例逐轮运行；3 例完成，1 例四次回答后仍为 ASK | 主代理 | `guided_intake_synthetic_inputs.json`、`baselines/current_guided_intake_snapshots.json` | 完成 |
| EX-008 | 生成真正盲包 | 角色分包，使用中性编号，分层、来源、旧反馈和作者信息仅存密封揭盲表 | 主代理、diagnostic_schema | `review/reviewer_cases/`、`review/reveal_key.json` | 完成 |
| EX-009 | 复核历史解卦证据 | 4 例 program hash 与历史结果完全一致；历史 catalog hash 未保存，明确标为同链路重建 | 主代理、case_inventory | `baselines/current_reading_safe_snapshots.json` | 完成 |
| EX-010 | 外部调用异常处置 | 中文经命令管道被替换为问号，24 次返回全部作废并禁止进入诊断样本 | 主代理 | `deviation_log.md`、`risk_log.md` | 完成 |
| EX-011 | 人工盲评 | 普通目标用户、易学评审与产品边界评审尚未指派 | 用户后续指定；主代理统一协调 | `review/` | 未开始 |
| EX-012 | 完整性与隐私校验 | 13 个 JSON 全部可解析；3 个盲包各 10 例；payload 哈希一致；禁用字段与敏感模式扫描为 0 | 主代理 | 命令输出与 manifest 哈希 | 完成 |
| EX-013 | 全量工程回归 | 首轮 955 通过、1 个本地 HTTP 连接被主机中止；单例复跑通过；禁用 cacheprovider 后全量 956 通过 | 主代理 | `pytest -q -p no:cacheprovider` | 完成 |
| EX-014 | PMO 第二闸门语义校验 | PMO 发现盲包规则说明被编码成连续问号；阻断交付后逐项修复，并新增连续问号、替换字符和典型乱码扫描 | stage0_pmo 发现；主代理修复 | `review/reviewer_cases/`、`review/reveal_key.json` | 完成 |
| EX-015 | PMO 最终闸门 | 复核乱码修复、payload/reveal 哈希、禁用字段、manifest 哈希、范围锁与独立全量测试 | stage0_pmo | `pmo_checklist.md` | PASS，允许送人工盲评 |
| EX-016 | 指派人工评审角色 | 用户确认由本人承担用户价值、易学结构和产品边界三类评审；已记录非独立性限制 | 用户、主代理 | `review/review_assignment.json` | 完成 |
| EX-017 | 生成三角色盲评工作簿 | 由三套 reviewer packet 生成4张工作表；重新导入检查34个公式、7项下拉规则、盲字段0命中，并完成全部工作表视觉核验 | 主代理 | `outputs/guanxiang_stage0_review_20260805/观象阶段0三角色盲评工作簿.xlsx` | 完成，待用户填写 |
| EX-018 | PMO增量工作簿闸门 | 核验同一评审人限制、XLSX盲字段、工作簿哈希和阶段0边界 | stage0_pmo | `review/review_assignment.json` | PASS，可交用户填写 |
| EX-019 | 冻结人工评审结果 | 保存用户填写原件、生成只读标准化结果并记录双重哈希；冻结完成后才揭盲 | 主代理 | `review/submissions/OWNER_REVIEWER_01/`、`review/reveal_key.json` | 完成 |
| EX-020 | 复核评审数据质量 | 逐例区分有效自由评论、不可校准分类评分和产品边界误解；剔除 R-3F76 一条与原文不符的子论据 | 主代理、stage0_pmo | `owner_feedback_evidence_v1.md` | 完成 |
| EX-021 | 建立评分锚点 V2 | 为用户价值、易学结构和产品硬门补充可观察正反例；CANNOT 不再作为中间分 | 主代理、rubric_anchor_review | `review/*_v2.json` | 完成 |
| EX-022 | 重做产品边界客观核验 | 按原文与 V2 规则逐项检查；纠正 9/10 日期误判和明确建议/替用户决定混淆 | 主代理、boundary_objective_audit | `review/objective_product_boundary_audit_v1.json` | 完成 |
| EX-023 | 形成阶段 0 收口判断 | 将技术基线、负责人质性反馈、客观边界审计与限制合并，判断两个核心问题是否得到有效验证 | 主代理 | `stage0_acceptance_report_v2.md` | 完成，`PASS_WITH_OPEN_ITEMS` |
| EX-024 | PMO 阶段 0 收口终验 | 复核范围、证据分层、11 个逐字硬失败证据、V2 锚点、开放项和阶段边界 | stage0_pmo | `pmo_checklist.md`、`governance/validation_report.json` | 完成，`PASS_WITH_OPEN_ITEMS` |

执行记录只描述已发生的动作。文件存在不等于阶段问题已经验证。
