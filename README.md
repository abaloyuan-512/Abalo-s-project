# Abalo-s-project

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
