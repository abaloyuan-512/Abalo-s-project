# Codex 与 Git 网络故障运行手册

更新时间：2026-07-20

## 适用情况

用于 `git fetch`、`git pull --ff-only` 或 GitHub 访问出现 443 超时、连接重置、DNS 异常，或 Codex 沙盒内外表现不一致时。

## 先判断是哪一层

1. 确认 Codex 当前任务允许联网，而不是直接关闭沙盒。
2. 分别检查 `github.com:443`、`api.github.com:443` 和 DNS。
3. 检查 `git config --global --get http.sslBackend`，本机治理基线为 `openssl`。
4. 检查 VPN、代理、防火墙、路由器或公司网络是否改变。
5. 最多做两次有间隔的重试；持续超时后停止重复连接，保存完整报错。

如果 DNS 成功、`api.github.com` 可达，但 `github.com:443` 持续超时，应先归类为外部链路问题，不要通过永久扩大 Codex 权限解决。

## 安全续接顺序

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git log --oneline -1 origin/codex/mvp-runnable-baseline
```

只有确认工作区无冲突、目标远端引用已存在并且能够快进时，才在用户批准 Git 写操作后执行：

```powershell
git merge --ff-only origin/codex/mvp-runnable-baseline
```

不得在网络失败时改用强制重置、覆盖本地文件或猜测远端已经同步。若对象已在本地但网络暂时不可用，可以先核对远端跟踪引用和目标提交；任何快进仍需记录来源和验收结果。

## 交接证据

故障后至少记录：时间、网络环境、完整报错、DNS/TCP结果、当前 branch/HEAD、远端跟踪引用、实际采用的恢复路径和测试结果。项目业务交接仍以根目录 `继续观象.md` 指向的最新交接记录为准。
