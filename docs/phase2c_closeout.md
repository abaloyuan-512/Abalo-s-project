# Phase 2C Closeout and External Live Validation Block

## Frozen status

```text
ENGINEERING_STATUS=COMPLETE
OFFLINE_VALIDATION_STATUS=PASSED
LIVE_V5_PATH_VALIDATION_STATUS=BLOCKED_BY_EXECUTION_POLICY
NARRATIVE_RELEASE_STATUS=UNVERIFIED
CLOSED_BETA_ALLOWED=false
SHOULD_CHARGE=false
FORMAL_REPORT_PERSISTENCE_ALLOWED=false
SITES_PHASE_3A_STATUS=ALLOWED_WITH_RELEASE_RESTRICTIONS
```

This record freezes the Phase 2C boundary. Engineering completion and offline
acceptance do not constitute production validation of the new V5 live path.

## Baseline and completed work

- Feature branch: `v2/meihua-live-eval-phase2c`
- Engineering baseline: `932d5bd279e580d066de871d4619606f6ae1e7a5`
- Provider contract: `MEIHUA_AI_NARRATIVE_DRAFT_SCHEMA_V3`
- Narrative assembly: `MEIHUA_NARRATIVE_ASSEMBLY_V1`
- Evidence reference catalog: `MEIHUA_EVIDENCE_REFERENCE_CATALOG_V1`
- Interpretation prompt: `MEIHUA_INTERPRETATION_PROMPT_V5`
- Repair prompt: `MEIHUA_REPAIR_PROMPT_V4`
- Historical compatibility resolver: `MEIHUA_LEGACY_EVIDENCE_RESOLVER_V1`
- Historical compatibility deduplicator: `MEIHUA_LEGACY_EVIDENCE_DEDUPLICATOR_V1`
- Guarded low-effort Smoke entry points: `CASE-001` and `CASE-007`
- Historical attempt-1 response replay: 16 of 16 completed and passed
- Full test suite: 522 passed
- Interpretation validator red team: 80 of 80 passed
- `pip check`: passed

Historical real evaluation established that the OpenAI Responses base call
chain, parsing path, Validator and Repair foundations, safe API-result
recording, `should_charge=false`, and formal-persistence gates can work. That
historical V3 evidence is not evidence that the V5 live combination below has
been validated.

## Outstanding live validation and residual risk

The sole critical remaining external validation is a real Responses API run of
this exact combination:

- `MEIHUA_INTERPRETATION_PROMPT_V5`
- `MEIHUA_AI_NARRATIVE_DRAFT_SCHEMA_V3`
- `MEIHUA_EVIDENCE_REFERENCE_CATALOG_V1`
- `MEIHUA_NARRATIVE_ASSEMBLY_V1`
- `CASE-007`
- `reasoning_effort=low`

The unresolved risks are whether:

1. the real model emits only legal `EV` short references;
2. each claim avoids duplicate `EV` references;
3. live deterministic mapping from `EV` to canonical Evidence completes;
4. the live Provider response satisfies the current Draft Schema; and
5. CASE-007 passes the Validator with no more than one Repair attempt.

The 16-of-16 offline replay does not fully eliminate these risks.

## Execution-policy block

The user explicitly authorized the narrowly scoped export of Prompt V5, the
fixed synthetic CASE-007 input, its required program conclusions, and its
Evidence Catalog. The Codex safety approval layer nevertheless rejected the
operation because the destination was not established as trusted for private
workspace-derived data.

The rejection occurred before any Responses API attempt. Consequently:

- Responses API attempts added: 0
- CASE-007 output directory created: no
- source, tests, prompts, rules, datasets, and historical responses changed: no
- workaround, indirect retry, or alternative data-export path used: no

This is an execution-environment policy block. It is not a Provider failure,
model failure, validation failure, or code failure. No credential or API-key
information is recorded here. This block must not be bypassed through Codex
permissions, alternate commands, scripts, or indirect execution.

## Release gates

Until the V5 live path is validated:

- `NarrativeReleaseStatus` must remain `UNVERIFIED`;
- `should_charge` must remain `false`;
- `persist_as_formal_report_allowed` must remain `false`;
- closed beta must not begin;
- AI Narrative must not be released as a formal user report;
- Phase 2C must not be described as production-validated; and
- existing release gates must not be removed or weakened.

## Conditions for a future CASE-007 Smoke

A future live Smoke is allowed only when all of these conditions hold:

1. it runs in a trusted execution environment that explicitly permits this data export;
2. export approval explicitly covers Prompt V5, fixed synthetic CASE-007, its
   program conclusions, and its Evidence Catalog;
3. no real user data, secret, token, or credential is sent;
4. the existing guarded Runner is used;
5. only CASE-007 with low reasoning is run;
6. at most two attempts are permitted, with attempt 2 restricted to the existing Repair flow;
7. a new repository-external output directory is used;
8. neither Legacy Resolver nor Legacy Deduplicator is used on the live path; and
9. a passing result still receives independent human review of its acceptance bundle.

Codex permission workarounds are not an acceptable means of satisfying these
conditions.

## Sites-first Phase 3A boundary

Sites-first Phase 3A may start offline under release restrictions. Allowed work:

- frontend structure, pages, and user flows;
- frontend/backend API contracts;
- wrappers around the authoritative Python engine;
- local or mock-data end-to-end flows;
- login, quota, question-entry, and report-state design;
- HTML report presentation adaptation; and
- explicit error and `UNVERIFIED` state presentation.

Phase 3A must not:

- publish real-user AI reports;
- charge users;
- formally persist AI Narrative;
- begin closed beta;
- bypass any Phase 2C release gate;
- treat Sites or frontend logic as the authoritative casting engine; or
- assign deterministic calculation to a model.

