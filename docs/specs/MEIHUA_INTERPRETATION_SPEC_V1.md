# Meihua Interpretation Specification V1

## Trust boundary

Phase 1 is the sole authority for deterministic casting. An untrusted chart
payload is accepted only through `chart_from_untrusted_json`, which rebuilds
the chart from its original input and rejects any mismatch in derived fields.
The interpretation layer cannot calculate or overwrite a chart.

The service accepts one normalized question in one closed domain:
`RELATIONSHIP`, `CAREER`, or `FINANCE_COOPERATION`. Real-world context is user
data, not hexagram evidence, and is delimited as `user_data_untrusted` in the
prompt payload.

## Deterministic synthesis

`ConclusionSynthesizer` consumes only Phase 1 deterministic relation evidence.
Approved knowledge may enrich wording but cannot alter the conclusion level.
Each initial/changed `RelationAssessment` takes direction from body/use; body
and use seasonal strength may only modify strength, conditions, and warnings.
Seasonal evidence never votes independently. The synthesizer uses named rules,
not scores or percentages, and emits one of:

- `CLEARLY_FAVORABLE`
- `CONDITIONALLY_FAVORABLE`
- `MIXED_OR_UNSETTLED`
- `CLEARLY_UNFAVORABLE`
- `INSUFFICIENT_EVIDENCE`

Conflicting initial and changed body/use directions force a mixed result.
Unreviewed knowledge cannot strengthen the conclusion.

## Program-owned report and AI narrative

`ProgramOwnedInterpretation` is rendered entirely in code. It owns the direct
conclusion template, conclusion level, chart facts, current situation,
conflict, supporting and blocking Evidence, timing, uncertainties, and the
Evidence trace. `MEIHUA_PROGRAM_INTERPRETATION_V1` maps every conclusion level
to one fixed tested sentence.

The model parses only `AINarrativeContent`: lists of typed claims for plain
language explanation, real-world action options, conditions to verify, and
review questions. Each claim has Evidence IDs, narrative kind, subject scope,
and epistemic basis. There is no free `summary`, chart field, conclusion field,
supporting/blocking field, or timing field in the AI schema. The final report
contains `program_content`, `ai_content`, and program-attached metadata.

Content cardinality is frozen: explanation, advice, and review questions each
require 1–4 claims; conditions allow 0–4. Claim text is 4–300 characters and
each claim cites 1–6 unique Evidence IDs. Empty or oversized content fails
schema validation, receives at most one repair attempt, and never produces a
chargeable or persistable report.

Local validation rejects unsupported or role-incompatible Evidence IDs, any AI
restatement of program-owned chart facts, all AI timing content, absolute
guarantees, mind-reading, medical/financial instructions, semantic Evidence
direction reversal, secret-like material, and internal paths. Program timing
echoes only the exact request horizon, moving-line stage, TimingLevel, and fixed
disclaimer. `exact_date` remains false and `candidate_dates` remains empty.

AI authority is limited to wording a structured explanation from supplied
facts. It may not cast again, select a moving line, change body/use or seasonal
strength, invent traditional meanings, or promote knowledge review status.
Narrative kind and epistemic basis freeze Evidence roles for each AI list.
User context can never be relabelled as chart Evidence. Mind-reading and
absolute assertions remain prohibited even when requested by the user. Local
pattern and role checks are one defence layer; they do not claim to solve every
possible prompt injection or semantic bypass.

One validation repair attempt is permitted. A second invalid response raises
`InterpretationValidationError`, retains safe provider/token metadata for both
attempts, returns no partial interpretation, and has `should_charge = False`.
Provider failures also have `should_charge = False`.

## Narrative release gate

`NarrativeReleaseStatus` defaults to `UNVERIFIED`. The current snapshot has no
live-eval version, model or completion time and has case count zero. In this
state Fake, internal, and explicitly authorized live-smoke results are preview
only: `should_charge=false` and formal persistence is disabled. Ordinary
environment variables cannot promote the status. A repository-reviewed,
versioned live-eval approval mechanism is required before closed beta and is
not implemented in Phase 2A.

Regex and keywords are only an auxiliary defence. Structured output guarantees
shape, not semantic truth. A fixed real-model evaluation suite is mandatory
before any release promotion.

## Versioning

Prompt version: `MEIHUA_INTERPRETATION_PROMPT_V1`.
Knowledge version: `MEIHUA_INTERPRETATION_KNOWLEDGE_V1`.
Changes to deterministic rules require a new version and full pytest coverage.
