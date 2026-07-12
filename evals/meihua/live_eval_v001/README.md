# Meihua Live Eval V001

仅包含12个固定合成案例；low运行12例，medium对照4例。真实结果必须输出到Git仓库外。状态只允许 `COMPLETED_PENDING_HUMAN_REVIEW`。

## 人工审核工作簿辅助生成器

`scripts/build_meihua_live_eval_review_xlsx.mjs` 仅用于读取仓库外的评测汇总和配置结果，生成人工审核 XLSX 工作簿与可选 PNG 预览。它不是核心评测运行时依赖，也不会调用 OpenAI。输入结果目录和输出目录必须位于 Git 仓库外，不得将真实评测结果提交到 Git。人工调用时，实际命令参数以脚本的 `--help` 或现有参数定义为准。
