# 来源索引

## 仓库内来源

| 用途 | 来源 | 证据边界 |
| --- | --- | --- |
| 4 个失败案例 | `evals/meihua/personalization_gate0_v001/question_text_pair_outputs.json` | 合成确定性输出；没有辨识逐轮对话和真实用户反馈 |
| 失败结论与 384 盘统计 | `evals/meihua/personalization_gate0_v001/audit_report.md` | 证明 V3 模板行动和自由文本敏感性问题，不证明所有 V4 都忽略卦象 |
| 4 个中间候选输入 | `evals/meihua/live_eval_v001/dataset.json` | 全部为公开合成案例 |
| 中间候选评审状态 | `evals/meihua/live_eval_v001/human_review_schema.json` | human score 尚未完成 |
| 当前辨识冻结基线 | `guided_intake_synthetic_inputs.json` 与 `baselines/current_guided_intake_snapshots.json` | 阶段 0 新增的合成逐轮现状记录；不是用户反馈，也未改变 Prompt 或产品实现 |
| 当前解卦安全快照 | `baselines/current_reading_safe_snapshots.json` | 历史真实模型输出的脱敏完整副本，加同一确定性链重建的盘面与证据目录 |
| 保护案例一 | `evals/meihua/personalization_gate1_v001/product_calibration_round3_refined_voice.md` 与 `calibration_round3_result.md` | 产品负责人 85 分以上；实验性解释，不是正式规则 |
| 保护案例二 | `evals/meihua/personalization_gate1_v001/product_calibration_round4_transfer_packet.md` 与 `calibration_round4_result.md` | 产品负责人 85 分通过；实验性解释，不是正式规则 |

## 仓库外只读来源

4 个中间候选的历史真实模型输出来自：

`D:\效率工具--GitHub\文件储存夹\Abalo-s-project_phase2c_live_eval_v001_live_results_r2\config_results.jsonl`

该文件存在且包含 16 条合成配置结果。诊断集复制 CASE-001、CASE-005、CASE-006、CASE-008 的 low 叙述正文和非敏感成本指标，并用同一固定确定性链重建盘面、program content 与 evidence catalog；不复制 response ID、request ID 或密钥。4 例 program hash 与历史结果完全一致，但历史 catalog hash 未保存，因此 catalog 只标为同链路重建。

## 已确认不存在或不可用的来源

- 仓库内真实用户完整案例：0；
- 历史仓库内完整辨识逐轮对话：0（阶段 0 已新增 4 个合成冻结基线）；
- 案例本人反馈：0；
- 已指定易学评审：0；
- Gate 2 C.3 文档声明的仓库外原始证据目录：当前机器路径不存在，不能引用为案例正文。

生产数据库表设计包含 `question`、`intakeJson`、`resultJson` 和可能带联系方式的 `feedback`。本阶段没有读取生产数据。若以后需要，必须由主代理向用户单独报告隐私范围并获得确认。
