# 观象个性化解读可行性验证 · Gate 0

本目录冻结观象 Sites v16 的确定性内容基线，用于量化当前解读的同质化机制。它只包含合成输入、确定性排盘与本地统计，不调用 OpenAI 或其他外部模型。

## 权威基线

- 分支：`codex/mvp-runnable-baseline`
- 产品行为基线：`7e96712c1ffc2c3209063c0efd60c33f8f1916ef`
- 治理工作基线：`e75594208643232ae35134a70b41be1aeea74229`
- Sites：v16
- 数据集：`GUANXIANG_PERSONALIZATION_GATE0_V001`
- AI Narrative：`UNVERIFIED`
- 模型调用：0
- API费用：0美元

## 文件

- `fixed_cases.json`：固定合成输入、384盘面穷举规则、8个代表案例及4组自由问题对照。
- `baseline_outputs.json`：8个代表盘面的完整确定性报告输出。
- `question_text_pair_outputs.json`：4组自由问题对照的完整输入、请求哈希和报告输出。
- `audit_summary.json`：盘面敏感性、自由问题敏感性和结构化选项敏感性统计。
- `baseline_manifest.json`：基线版本、Release Gate状态和文件哈希。
- `audit_report.md`：供产品负责人验收的中文结论与文件级证据。

## 复现

```powershell
.\.venv\Scripts\python.exe scripts\build_personalization_gate0_baseline.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate0_baseline.py
```

生成器固定服务端时间与全部输入，并强制使用UTF-8＋LF写入JSON；`.gitattributes`也固定本目录JSON的仓库换行。重复运行应得到相同的四个JSON产物与清单哈希。`audit_summary.json`还保存384个完整确定性结果的汇总哈希。它不读取API Key，也没有任何外部网络路径。

## 范围边界

Gate 0只回答“当前到底有多重复、重复由什么造成”。本目录不定义新Prompt、新判断签名、新术数规则、锁定测试集或模型实验方案。锁定测试集尚未创建或暴露，术数审核者尚未指定。Gate 0通过独立复验前，不进入Gate 1。
