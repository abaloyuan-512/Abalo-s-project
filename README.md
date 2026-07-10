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
