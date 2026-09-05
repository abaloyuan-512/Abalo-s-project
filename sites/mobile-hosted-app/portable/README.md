# 观象 0.5 独立运行适配

这是一条可选的 Node.js 运行路径，复用当前 `sites/mobile-hosted-app` 的页面、素材、API 契约及 Python 排盘服务。默认 Sites 构建与旧网址保留。

**当前状态：本地构建与自动集成测试通过，尚未创建新公网服务；不代表中国大陆无 VPN 已可用。**

## 运行要求

- Node.js 24（本地验证版本 24.19.0），pnpm 支持本项目 lockfile v9。
- 单实例运行；SQLite 数据目录需要持久存储。不能将多副本共用文件当成分布式数据库。
- 面向用户的 HTTPS 入口及正确的公开地址。
- 服务器能访问现有 Python 服务；保持原有引擎密钥在服务器环境变量中，不能进入网页或源码。

## 构建和启动

在 `sites/mobile-hosted-app` 目录安装锁定依赖并运行：

```sh
pnpm install --frozen-lockfile
pnpm run build:portable
pnpm run typecheck:portable
pnpm run start:portable
```

安装时保留开发依赖：vinext、Vite 既参与构建，也有运行时依赖。`build:portable` 将构建复制到 `dist-portable`；现有 portable 构建保存在忽略的 `work` 目录。默认 `pnpm test` 会重建 Sites 的 `dist`，但不会覆盖 `dist-portable`。

启动前配置：

| 变量 | 配置要求 |
| --- | --- |
| `NODE_ENV` | `production` |
| `PORT` | 平台提供的端口，默认 3000 |
| `HOST` | 默认 `0.0.0.0`；本地检查可设 `127.0.0.1` |
| `GUANXIANG_PUBLIC_ORIGIN` | 新入口的完整 HTTPS origin，无路径；Render 可改用其自动提供的 `RENDER_EXTERNAL_URL` |
| `GUANXIANG_SQLITE_PATH` | 持久目录内数据库路径；Render 持久部署应为 `/var/data/guanxiang.sqlite` |
| `PYTHON_ENGINE_URL` | 现有 Python 服务 HTTPS 地址 |
| `PYTHON_ENGINE_KEY` | 与 Python 端一致的秘密值，只在平台密钥设置中配置 |
| `ABALO_PUBLIC_BETA_ENABLED` | 对外匿名试用时设 `true` |
| `ABALO_DIRECT_READING_V2_PREVIEW_ENABLED` | 完整解读入口设 `true` |
| `ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED` | 条件辨识设 `true`，仍需 Python 服务支持 |
| `GUANXIANG_TRUST_PROXY_PEERS` | 默认空；只允许经验证、直接连接本服务的代理 IP，逗号分隔 |

`/healthz` 仅验证网页服务和 SQLite 可用，不能证明模型、外部后端、用户网络或完整业务可用。

## 部署平台设置

可使用支持 Node.js 24 和持久目录的主机。若继续使用现有 Render 账户创建**新的** Web Service：

- Root Directory：`sites/mobile-hosted-app`。
- Build Command：`pnpm install --frozen-lockfile && pnpm run build:portable`。
- Start Command：`pnpm run start:portable`。
- Health Check Path：`/healthz`。
- Node 版本环境变量：`NODE_VERSION=24.19.0`。
- 不替换现有 Python 服务，不修改旧 Sites 入口；来源选择包含本次适配代码的独立分支。
- 新服务成功后，使用平台实际返回的 HTTPS 地址，不能预先假定域名可用，更不能假定大陆直连成功。

持久存储涉及的平台收费需产品负责人确认后再创建。Render 免费服务不能挂持久磁盘，因此默认阻止无持久目录启动。若负责人明确选择**可丢弃数据的短期测试服务**，可显式设置 `GUANXIANG_ALLOW_EPHEMERAL_BETA=true`，但必须提醒：重启/重新部署/休眠后数据和限流记录可能丢失。不能据此宣布正式上线。

平台文档：[Web Services](https://render.com/docs/web-services)、[Persistent Disks](https://render.com/docs/disks)、[Free Instances](https://render.com/docs/free)。收费与平台限制以上线当时信息为准。

## 代理与公开访问边界

独立主机不能信任客户端自带的 `oai-*`、`cf-*` 或转发头。运行入口会清除这些头，仅根据连接来源合成限流身份；经显式信任的代理只读取其最后追加的一跳地址。

在代理关系尚未验证时，多个用户可能共用代理 IP 的每小时 6 次额度。这是保守降级，不是逐用户计费。不要为了提高额度盲目信任任意转发头；生产上线前必须验证平台实际代理链。不要把公开的 SQLite、日志或调试接口用于核查 IP。

## 自动验证

```sh
pnpm run build:portable
pnpm run typecheck:portable
pnpm run test:portable
pnpm test
pnpm run typecheck
pnpm run lint
```

`test:portable` 使用项目根目录 `.venv` 内的 Python；其他位置可设置 `ABALO_TEST_PYTHON`。测试包含真实 Node HTTP 服务、SQLite 和 Python 排盘/HTTP 传输；**模型输出来自已有固定测试样本，不调用真实模型**。

`typecheck` 先构建默认 Sites 产物，再从其配置生成忽略的 `worker-runtime.d.ts`（不含环境变量值），最后检查全项目类型。独立运行代码也可单独使用 `typecheck:portable`。

## 数据及旧版保留

- 本次适配不复制、删除或导出线上 D1 用户记录。
- 新域名不会继承旧域名的设备存储和安装状态；旧数据、旧设备身份与历史记录迁移需要另行验收。
- 原来的 0.5 地址、安装入口、Python 引擎、排盘算法、P1–P9 布局与素材保持不变。
- 回退方式是继续使用旧地址；不需要恢复算法或重新拼装页面。

## 真机验收前的准入条件

1. 新服务实际部署成功，HTTPS、静态素材与公开元数据使用新 origin。
2. 新服务使用真实后端完成 P1–P9（不是固定测试样本）。
3. 验证重启后持久记录与限流保留，或明确标注可丢弃测试环境。
4. 验证代理身份、隐私隔离、错误提示与无重复模型提交。
5. 再交产品负责人：关闭 VPN，分别用移动数据/Wi-Fi、系统浏览器/微信打开新网址，完成一次生成、保存、再次打开及桌面安装。
6. 用至少两种不同屏幕尺寸实测，检查遮挡、横向溢出、输入键盘、底部安全区和 P8/P9 滚动。本地内置浏览器已检查首屏及 P1→P2→P3 推进和输入；实际报告宽度为 390 CSS 像素。其余尺寸覆盖、全流程视觉与跨机型验收尚未完成。

大陆网络验收必须记录实际运营商、网络类型、浏览器及失败截图；某一条线路通过，不能推断全国所有线路都通过。
