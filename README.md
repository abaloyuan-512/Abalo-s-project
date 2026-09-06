# Abalo-s-project（观象）

**当前状态：第二阶段 Beta 交付基线冻结；第三阶段聚焦解卦系统与文本价值优化。**

跨设备、跨任务继续时，只从 [继续观象.md](继续观象.md) 开始，再读 [工程规则](AGENTS.md)。不要按旧文件的“最新进展”或目录名称猜测版本。

## 当前渠道

| 渠道 | 基线 | 源码选择 |
| --- | --- | --- |
| 网页版 | Sites V72，保持冻结 | 既有 V72 冻结来源，不改动 |
| VPN 手机端 | Sites V11 | 独立 Sites 源仓库；不要用大陆目录替代 |
| 大陆直连免费 Beta | 8e1e2da 发布基线 | codex/mainland-portable-beta 分支中的 sites/mobile-hosted-app |
| 共享解卦后端 | 8e1e2da，手机端选用 concise-medium-v1 | 按完整发布提交选取，禁止用默认分支最新版推断线上版本 |

完整提交、网址、验收边界及来源见 [渠道索引](docs/governance/current-release-index.json) 和 [冻结记录](docs/governance/guanxiang-phase2-beta-freeze-2026-09-06.md)。

两个手机渠道共用产品改进，但部署、身份与存储不同，不要求字节完全一致。main 的产品源树保留历史状态，仅同步当前说明入口；后续实现从准确基线建立独立候选分支。

## 不变边界

确定性程序负责排盘，AI 不参与成卦计算。不得伪造日期、卦象证据或测试结果。未经授权不改冻结产品，不发布、不升级付费资源、不发起付费模型测试。最新补丁真机复核留待用户下一次真实问题。

旧版入口 streamlit_app.py、iching_tools.py 继续保留。使用旧本地脚本前，先检查其对应版本和是否调用模型。

## 历史材料

原 README 的本地启动、工程 Phase 1/2 说明已保存在 [历史快照](docs/archive/project-readme-before-phase2-cleanup.md)，不能用其中“暂无公开部署”等旧状态描述当前产品。版本化术数规范仍以 docs/specs/ 为准。

整理范围与保留项见 [清理记录](docs/governance/phase2-reference-cleanup-2026-09-06.md)。
