# Sites Phase 3B local prototype

This is a loopback-only local webpage prototype. It is not a published Sites
site and does not accept real-user data. The browser sends Contract V1 input to
the local adapter, which delegates all deterministic calculation to the Python
authoritative engine.

The prototype provides no AI Narrative, charges nothing, persists nothing, and
is not part of a closed beta. `NarrativeReleaseStatus` remains `UNVERIFIED`.

Start from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run_sites_phase3b_local_server.py --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765/`. No external visual or script assets are
used. Refreshing clears all form and result state.
