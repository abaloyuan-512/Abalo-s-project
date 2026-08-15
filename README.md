# Abalo-s-project（观象）

当前主产品是九页“观象”体验。确定性程序负责三数成卦；AI只参与现有的条件辨识与解卦，不参与排盘。

## 当前产品治理基线（2026-08-15）

- P1首页、P2观象之法与准备、P3正问、P7卦象、P8读卦五幕、P9观象寄语均以各自最终定稿为准，不擅自改写。
- 无歧义：`P3 → P6`。有歧义：`P3 → P4（现有系统最多问一次）→ P5 → P6`。
- P6三数取数由确定性程序排盘，AI不参与。
- P7不呈现用户所问问题，只呈现既定卦象信息及详细读卦入口。
- P9文本和内核冻结；缺少经过批准的P9动态内容时，不得用旧五面板或临时生成文案替代。

完整基线见 [`docs/governance/guanxiang-release-baseline-v4-2026-08-15.md`](docs/governance/guanxiang-release-baseline-v4-2026-08-15.md) 与 [`docs/specs/MEIHUA_SITES_EXPERIENCE_SPEC_V4.md`](docs/specs/MEIHUA_SITES_EXPERIENCE_SPEC_V4.md)。这不等同于部署或发布证明。

## 现在打开产品

旧版入口仍保留：

```powershell
.\scripts\start_local_product.ps1
```

看到 `http://127.0.0.1:8765/` 后，用浏览器打开这个地址。保持 PowerShell 窗口开启；结束时按 `Ctrl+C`。

九页集成本地预览需要有效的 `OPENAI_API_KEY`、Python 3.12环境和已安装的前端依赖：

```powershell
cd .\sites\hosted-app
pnpm install
cd ..\..
$env:OPENAI_API_KEY = "<仅设置在当前终端，不要写入仓库>"
.\scripts\start_conditional_p1_p8_preview.ps1
```

脚本只监听 `127.0.0.1`，会输出站点地址、两个进程ID和日志位置；不会部署到公网。

### 首次准备

只有在 `.venv` 不存在时才需要执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

项目严格使用 Python 3.12。当前网页只监听本机地址 `127.0.0.1`，同一网络中的其他设备也无法访问。

## 当前产品边界

- 已有：结构化提问、三数起卦、本卦/互卦/变卦、体用与旺衰、规则型导师导读、可逆行动建议。
- 暂无：个性化 AI 深度解读、账户、云端保存、支付、公开部署。
- 安全边界：结果是传统文化下的结构化思考参考，不保证事件结果；重要决定以现实事实和专业意见为准。

## v2 Phase 1 development status

The repository now contains a deterministic Meihua Yishu chart engine under
`src/abalo_iching/meihua`. It calculates the chart from three integers, a
timezone-aware casting time and an IANA timezone without asking an AI model to
perform chart arithmetic.

The existing `streamlit_app.py` and `iching_tools.py` remain the unchanged v1
prototype entry points. They have not yet been migrated to the v2 engine.

### Phase 1 verification

```powershell
.\.venv\Scripts\python.exe -m compileall src tests scripts
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src/abalo_iching --cov-report=term-missing
.\.venv\Scripts\python.exe scripts\verify_wheel_install.py
.\.venv\Scripts\python.exe scripts\demo_meihua_engine.py
```

Phase 1 does not implement accounts, databases, reports, Four Pillars, payment,
AI interpretation or exact-date timing.

## v2 Phase 2 interpretation layer (development baseline)

Phase 2 adds a conservative, structured interpretation pipeline without
changing the Phase 1 casting engine. It includes a versioned 64-hexagram / 384-
line canonical text dataset, deterministic conclusion synthesis, strict local
validation, an offline fake provider, and an optional OpenAI Responses API
adapter. The explanatory knowledge baseline is `CANONICAL_ONLY`; it is not
presented as human-approved interpretation. Canonical source text and
explanatory knowledge are stored separately; draft knowledge is not production
knowledge and is disabled by default.

Program-owned rendering now produces the conclusion, chart facts, Evidence
sections, uncertainty and timing. The optional model can return only typed
plain-language explanations, action options, conditions to verify and review
questions; it has no schema field for chart facts, conclusions, timing or free
summaries.

Narrative release is currently `UNVERIFIED`. Offline and any future explicitly
authorized live-smoke output is preview-only, cannot consume a paid report
credit, and cannot be persisted as a formal report until a versioned live-model
evaluation is approved in the repository.

Run the fully offline demonstration (it never calls OpenAI):

```powershell
.\.venv\Scripts\python.exe scripts\demo_meihua_interpretation_offline.py
```

The live adapter reads `OPENAI_API_KEY` from the environment and the optional
model override from `ABALO_OPENAI_MODEL`. Do not store secrets in the
repository. See `docs/specs/MEIHUA_OPENAI_ADAPTER_V1.md` for the adapter
contract and explicit live-smoke safeguards.
OpenAI calls are off by default; the smoke script requires both the environment
key and `--confirm-live-call`. Phase 2 does not add a website UI, account
system, database, payment, or report generator.
