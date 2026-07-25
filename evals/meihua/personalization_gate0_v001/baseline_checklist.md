# Gate 0 基线清单

## 仓库状态

- 仓库：`D:\效率工具--GitHub\文件储存夹\Abalo-s-project`
- 分支：`codex/mvp-runnable-baseline`
- 产品行为基线：`7e96712c1ffc2c3209063c0efd60c33f8f1916ef`。
- 治理工作基线：`e75594208643232ae35134a70b41be1aeea74229`。
- 治理工作基线与`origin/codex/mvp-runnable-baseline`同步。
- Sites私有基线：v16。
- AI Narrative：`UNVERIFIED`。

开始Gate 0前已存在、且本次未触碰的未跟踪视觉验收产物：

- `sites/hosted-app/.artifacts/product-audit-2026-07-19/`
- `sites/hosted-app/.artifacts/qa/`

## Gate 0新增内容

- `evals/meihua/personalization_gate0_v001/`
- `scripts/build_personalization_gate0_baseline.py`
- `tests/test_personalization_gate0_baseline.py`
- 本交接记录中的Gate 0状态更新。

## 明确未修改

- `src/abalo_iching/meihua/`确定性排盘引擎；
- `src/abalo_iching/application/sites_meihua_service_v3.py`；
- `src/abalo_iching/application/sites_clarity_report_v3.py`；
- `contracts/sites_meihua_v3/`；
- `src/abalo_iching/interpretation/prompts/`；
- `src/abalo_iching/interpretation/validators.py`；
- `src/abalo_iching/interpretation/release.py`；
- `sites/hosted-app/app/`及全部视觉文件；
- `streamlit_app.py`与`iching_tools.py`；
- 解释知识状态与术数规则版本。

## 验证

- 固定生成器重复运行：4个生成产物哈希一致。
- 384个完整确定性结果具有固定汇总SHA-256。
- 4组自由问题对照保存完整输入、请求哈希与报告输出。
- Python版本、固定时钟和时区写入`baseline_manifest.json`。
- 生成器与`.gitattributes`统一JSON为UTF-8＋LF；Manifest哈希直接对应Git提交中的文件字节。
- Gate 0与V3定向测试：15 passed。
- 全仓测试：766 passed。
- `git diff --check`：通过。
- 真实模型调用：0。
- API费用：0美元。

全仓测试出现1条既有环境警告：当前Windows沙箱拒绝更新`.pytest_cache`。测试本身全部通过，该警告没有改变代码、输出或验收结论。

## 当前阶段状态

Gate 0证据候选包已经生成并通过工程验证，等待独立复验。锁定测试集状态为`NOT_CREATED_OR_EXPOSED`，术数审核者状态为`UNASSIGNED`。未经下一阶段授权，不进入Gate 1。
