# Risk log

| ID | Risk | Initial control | Status |
|---|---|---|---|
| R-V002-001 | Natural-language fact validation may falsely block good text | role-scoped hard assertions, warning separation, adversarial tests | OBSERVED DEFECT FIXED OFFLINE; RESIDUAL REGEX RISK OPEN |
| R-V002-002 | Prompt injection may alter the task | untrusted JSON envelope and deterministic chart authority | OFFLINE CLOSED |
| R-V002-003 | Duplicate requests may create duplicate model charges | request-id plus payload digest, lock, immutable terminal result | OFFLINE CLOSED |
| R-V002-004 | Raw Markdown may execute active content | React text rendering only, no raw HTML, URL deny rules | OFFLINE CLOSED |
| R-V002-005 | High reasoning latency harms product experience | immediate deterministic state, progress events, bounded medium comparison | OPEN: HIGH 63-68s; PERCEIVED DELAY MITIGATED, NOT SOLVED |
| R-V002-006 | Diagnostics may expose a user question or model text | synthetic-only private sink; public response and logs never include raw text | OFFLINE CLOSED |
| R-V002-007 | A dirty worktree may make the live run irreproducible | baseline and pre-call execution archives with SHA-256 | LIVE V3 CLOSED; POST-FINAL REPAIR SEPARATELY FROZEN |
| R-V002-008 | Python and Sites may disagree on progress/fact fields | top-level typed contract plus spawned cross-layer integration | OFFLINE CLOSED |
| R-V002-009 | Background exception may place user text in ordinary logs | stable code-only logging plus captured-log negative test | OFFLINE CLOSED |
| R-V002-010 | A missing result after a started marker may invite an extra call | marker is conservatively counted as consumed; no rerun | CONTROL FROZEN |
| R-V002-011 | Markdown emphasis around a correct classic quote can trigger a false block | preserve evidence; select high; repair normalization only after frozen final canary | CLOSED BY POST-FINAL REGRESSION; MEDIUM VERDICT UNCHANGED |
