# 观象个性化解读可行性验证 · Gate 1

Gate 1只负责冻结“什么样的解读有价值、怎样判断它真的有差异”的产品标准，不开发模型路径，不修改正式网站，不调用外部模型。

## 当前状态

- `GATE_0_STATUS = PASS`
- `GATE_1_STATUS = CALIBRATION_ROUND_5_PLAIN_LANGUAGE_REPAIRS_AWAITING_CONFIRMATION`
- `ROUND_1_INDEPENDENT_PRE_REVIEW = READY_FOR_PRODUCT_CALIBRATION`
- `LOCKED_TEST_SET_STATUS = NOT_CREATED_OR_EXPOSED`
- `DIVINATION_REVIEWER_STATUS = UNASSIGNED`
- 真实模型调用：0
- API费用：0美元

## 文件

- `content_value_spec_v1_draft.md`：内容价值规范草案。
- `calibration_cases.json`：6组产品口味校准案例，每组3个匿名候选答案。
- `product_calibration_packet.md`：产品负责人使用的非技术选择说明。
- `blind_review_rubric_v1_draft.md`：后续匿名盲测评分规则草案。
- `locked_test_governance.md`：锁定测试集的隔离、生成和变更规则。
- `gate1_status.json`：阶段状态和边界的机器可读记录。
- `calibration_round1_result.md`：产品负责人“全部不喜欢”的原始结果与流程纠偏。
- `product_calibration_round2_single_case.md`：基于真实盘面的单案例第二轮校准。
- `calibration_round2_result.md`：产品负责人选择“B的判断骨架＋A的行文风格”的原始反馈与可确认偏好。
- `product_calibration_round2_fusion_candidate.md`：按上述方向生成的同盘面融合确认稿。
- `calibration_round2_fusion_feedback.md`：融合稿70分评价、异常措辞和传统语感要求的原始记录。
- `product_calibration_round3_refined_voice.md`：保留融合稿判断、修正翻译腔并增加自然传统语感的确认稿。
- `calibration_round3_result.md`：传统语感修订稿获85分以上的原始结果和迁移要求。
- `product_calibration_round4_transfer_packet.md`：使用三个Gate 0真实盘面验证推进、有限主动与继续立基三种不同姿态。
- `calibration_round4_result.md`：三案例迁移的逐例评分、部分通过结论与抽象表达问题。
- `product_calibration_round5_plain_language_repairs.md`：保留案例一、三判断方向，改为普通人能直接理解的解释与行动。

独立预审记录见`docs/handoffs/2026-07-20-guanxiang-gate1-pre-review.md`。

## Gate 1完成条件

Gate 1不能由执行Codex自行宣布完成。至少需要：

1. 产品负责人完成能够选出方向的产品校准；Round 3单案例已达85分以上，Round 4部分通过，当前等待案例一、三通俗表达修订确认。
2. Codex根据选择修订内容价值规范，但不得改写选择结果。
3. 产品负责人确认规范、盲测问题和后续通过线。
4. 独立审查确认校准集没有把答案预先引向同一种保守姿态。
5. 锁定测试集仍保持未创建、未暴露；只冻结治理方法和结构蓝图。

完成Gate 1也不自动授权真实模型调用。Gate 2仍需另行批准。
