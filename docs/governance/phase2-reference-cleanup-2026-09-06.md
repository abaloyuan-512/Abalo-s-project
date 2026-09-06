# 第二阶段冻结后本地与远端引用整理

用户要求：深度清理本地与远端文件，确保同步，避免后续引用错误版本。本轮仅整理资料、版本引用与可重建产物，不修改产品、部署或密钥。

## 当前权威入口

- 根目录 继续观象.md → 本次渠道索引 current-release-index.json → 第二阶段冻结记录。
- GitHub main 同步当前导航，但保留历史产品源树。最新综合源码在 codex/mainland-portable-beta；VPN V11 仅从独立 Sites 源仓库选择。
- 历史手机 V6、按钮 V10 和七月续接入口不再作为当前发布依据；旧内容、标签与 Sites 版本均保留。
- 既有未提交的两份大陆交接补充已逐段核对，保留内容并添加历史状态提示，随本轮文档同步，不丢弃。

## 本地归档

归档根：C:/Users/27622/.codex/worktrees/80c8/phase2-reference-archive-20260906。

- 9 个 portable-build 时间戳目录、3 个旧 public-beta 打包文件、1 套旧嵌套 Git 元数据，共约 1.05 GB，移出活动源码区域，全部可恢复。
- manifest.json 保留原路径/归档路径/字节数。nested-mobile-repository.bundle 经 git bundle verify 确认可恢复完整历史。
- 移动旧隐藏 Git 目录后残留空目录；删除被工具策略阻止，未绕过。Git 已正常解析为上层主仓库，不再误认成旧 Sites 仓库。
- 保留当前构建、VPN V11 发布包、依赖、speed-v1 真实评测证据、测试截图/数据库、所有用户资料。没有永久删除历史版本。
- 第三阶段工作区 2cd9 的 reading_experience_research_v001 七个未提交文件保留；这类独立研究不是废弃版本，不擅自上传公开仓库。

## 远端同步纪律

普通 GitHub Git 连接首次发生 connection reset，间隔重试发生 github.com:443 超时；DNS 正常、github.com TCP/443 不可达、api.github.com TCP/443 可达。未修改代理、永久 Git 配置或权限。改用已有 gh 身份的官方 Git Data API。

同步必须逐提交核对 tree SHA 与 commit SHA，引用只允许非强制快进；冻结标签存在时必须完全一致，不移动。main 仅收文档、索引及工程治理说明，产品目录不得混入。

文档同步提交采用 [skip render]，避免文档变更触发 Render 自动部署。依据：https://render.com/docs/deploys#skipping-an-auto-deploy 。不调用部署/重启/付费资源接口。

远端历史分支和发布版本保留回退价值，以明确历史身份及准确来源解决混用，不靠删除回退证据制造“干净”。

## 核验清单

1. 校验索引 JSON 与完整提交长度、唯一渠道；链接目标存在。
2. 确认本次提交不含运行时源码、密钥、用户出生资料或评测原始记录。
3. 每个同步分支完成后用 GitHub API 重新读取引用，与本地完整 SHA 对照；保存本地核验收据。
4. 其他工作区同步前后核对状态和研究资料摘要，保护未提交文件。
5. Sites V11 只读核对已保存源提交，不发布新版本；历史冻结标签保持不变。
