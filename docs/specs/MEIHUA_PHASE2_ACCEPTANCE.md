# Meihua Phase 2 Acceptance

## Required checks

```powershell
.\.venv\Scripts\python.exe -m compileall src tests scripts
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src/abalo_iching --cov-report=term-missing
.\.venv\Scripts\python.exe scripts\verify_wheel_install.py
.\.venv\Scripts\python.exe scripts\verify_interpretation_wheel_install.py
.\.venv\Scripts\python.exe scripts\demo_meihua_interpretation_offline.py
.\.venv\Scripts\python.exe scripts\red_team_interpretation_validator.py
.\.venv\Scripts\python.exe -m pip check
```

Acceptance requires all Phase 1 tests and golden cases to remain green, exactly
64 canonical judgments and 384 canonical line statements, successful normal
wheel installation from an off-repository working directory, no live OpenAI
call, and no modification to `streamlit_app.py` or `iching_tools.py`.

Coverage targets are at least 94% for `src/abalo_iching` overall and 92% for
the interpretation package. Exact-date timing stays disabled.

## Phase 2 baseline result

- Completed: reproducible canonical dataset builders; review-state skeleton;
  deterministic synthesis; strict models and validator; fake and mocked
  providers; optional Responses API adapter; trusted/untrusted serialization
  boundary; offline demo; wheel packaging.
- Automated tests: 319 passed, including the original 142 Phase 1 tests.
- Coverage: 95% overall and 96% for `src/abalo_iching/interpretation`.
- Knowledge: 64 judgments, 384 line statements, 448 `CANONICAL_ONLY`, 0
  `DRAFT`, 0 `REVIEWED`, and 0 `APPROVED` records.
- Real OpenAI calls: 0. Only fake and mocked providers were executed.
- Wheel checks: Phase 1 and Phase 2 normal wheel installation passed from
  isolated off-repository directories.
- Exact-date timing: disabled; candidate date list empty.

Not completed: human line-by-line recension review, modern explanatory
knowledge review/promotion, live API smoke testing, UI, accounts, database,
reports, payment, Four Pillars, and exact-date timing.

## Human review gate

Structural completeness and primary-source provenance can be verified by
automation. Canonical variants and all explanatory knowledge still require
human subject-matter review. Until explanatory records are manually promoted,
the system must remain conservative and treat them as `CANONICAL_ONLY`.

## Phase 2A repair scope

Phase 2A replaces evidence-count voting with two typed relation assessments,
adds section-specific evidence roles, broadens normalized local red-team
checks, enforces the knowledge approval state machine, moves preview access to
an internal service policy, and separates model-generated content from program
metadata. No knowledge item is promoted and no live API call is executed.

The second Phase 2A audit moves every report fact and timing field into
`ProgramOwnedInterpretation`, narrows model output to `AINarrativeContent`, and
adds an independent fixed-case red-team script. The script contains 80 cases,
does not read validator keyword tables or pytest fixtures, and must report
80 pass / 0 fail. Live model availability remains unverified.

The final Phase 2A gate freezes narrative array/claim cardinality, sends an
explicit 2000-token output cap (configurable only from 500–4000), converts
approved/reviewed/draft records into structured K/R/D KnowledgeEvidence, and
stores a separate knowledge trace. Narrative release remains `UNVERIFIED`, so
all current Fake, internal and future opt-in smoke results are preview-only,
non-chargeable and non-persistable as formal reports.
