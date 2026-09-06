# 大陆直连等待与恢复热修复

## 范围和状态

仅修改 `sites/mobile-hosted-app` 的大陆直连发布源。VPN Sites 手机端和冻结网页版未部署变更；Python 排盘、规则、模型、提示词未改动。当前修复已完成本地验证，Render 发布尚未确认。

用户最新反馈：至少一位 iPhone 用户已经完成全流程，尚不能确定对应之前 T3/T4 哪位；P6、P7 等待超过一分钟，部分操作需要重试。该样本不能当成多机成功率验收通过。

## 已修复

- P6 浏览器公开健康唤醒改为与服务端预检并行，不再在提交前串行阻塞最多 65 秒。
- 只有服务端健康预检明确返回 `503 + not_submitted + ENGINE_WAKING/ENGINE_RATE_LIMITED` 才自动等待后继续同一请求编号和相同内容；最多 5 次尝试、150 秒调度窗口，尊重 Retry-After。这些响应发生在任务预留和模型提交之前。
- 提交超时、未知网关响应、模型失败及产品频率限制均不会自动重发 POST。
- 查询遇到断线、HTML 网关、429/5xx 时，只对原任务 GET 进行有界退避恢复。终止性失败立即退出；长 Retry-After 不会被缩短。
- P7 现在展示真实生成阶段，并在停止查询后提供“继续获取解卦”，遵守重试倒计时。修复原来 RECOVERABLE 状态仍只显示“生成中”的死路。
- 修正读取后台 stage 字段的位置，以及超时提示中“可浏览五幕”的不实说明。

## 验证

- TypeScript 检查及 portable 生产构建通过。
- 初次综合检查 34/34，通过移动恢复、公开边界、SQLite、真实 Python 确定性引擎到 portable HTTP 流程；模型采用冻结测试数据，不是付费调用。
- 增加健康预检限流等待覆盖后，相关恢复检查 15/15 通过。
- 无头 Chrome 在手机尺寸下模拟：预检拒绝一次后自动接受；四次查询断线后显示恢复入口；点击恢复后显示 MODEL_STREAMING 进度；恢复不增加 POST 次数。
- 320/390/430px 宽度下进度提示完整位于视口中。图像证据位于忽略目录 `sites/mobile-hosted-app/work/hotfix-p7-mobile.png`。
- 可复测脚本 `sites/mobile-hosted-app/scripts/qa-recovery.mjs`，使用测试页面和拦截的 API，需设置 PLAYWRIGHT_PACKAGE_ROOT（createRequire 的锚点）、QA_BROWSER_PATH；可选 QA_ORIGIN。

## 限制与发布

本补丁不能消除免费服务器休眠，也没有降低模型正文生成时间；未提升套餐、未发起付费模型测试。P8 提前浏览骨架和解读内容缩短留待后续独立验证。

电脑操作工具在获取 Chrome 状态时报告无法可靠确定浏览器 URL，停止本轮接管。没有通过其它途径绕过这个控制台限制。需要在 Render `guanxiang-mobile-beta` 服务上部署本次提交后，再做线上及大陆真机验收；不要将本地通过称为线上发布成功。
