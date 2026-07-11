# Meihua Knowledge Contract V1

Status: Phase 2 baseline. Data version: `MEIHUA_CANONICAL_TEXTS_V1`.

## Scope and provenance

The canonical dataset contains the received-text judgment and six line
statements for each of the 64 King Wen hexagrams: exactly 64 judgments and 384
line statements. It intentionally excludes Tuan, Xiang, Wenyan, and the Qian
and Kun `用` statements.

The frozen primary transcription is the public Wang Bi received-text mirror
identified by `primary_source`, `source_sha256`, and `source_accessed_at` in
`hexagram_canonical_texts_v1.json`. It is a frozen primary transcription, not a
completed cross-recension review. Chinese Text Project and Chinese Wikisource
are pending human comparison targets; recording their URLs does not mean every
line has been checked. `cross_check_status` therefore remains
`PENDING_HUMAN_LINE_BY_LINE_REVIEW`. Variants must be documented and must never
be silently combined.

Only public-domain canonical text is permitted. Modern translations,
commentaries, web articles, and paid editions must not be copied into either
dataset without a separate rights review and a new data version.

`scripts/build_canonical_texts.py` performs exact structural extraction. It
does not generate, paraphrase, or interpret canonical text.

## Review states

- `CANONICAL_ONLY`: canonical text is present; no domain interpretation is approved.
- `DRAFT`: internal draft only, excluded by default.
- `REVIEWED`: human-reviewed explanatory knowledge.
- `APPROVED`: human-approved knowledge eligible to become cited evidence.

Machine-generated content must never be labelled `REVIEWED` or `APPROVED`.
The Phase 2 baseline contains 64 hexagram records and 384 line records, all at
`CANONICAL_ONLY`; it contains no draft or approved explanatory content.

## Runtime boundary

The runtime fails closed unless coverage is exactly King Wen 1..64 with line
positions 1..6. `CANONICAL_ONLY` records may be displayed as source material,
but they do not add strong evidence. `DRAFT` requires the explicit internal
`INTERNAL_DRAFT_PREVIEW` service policy. `INTERNAL_REVIEW` may expose REVIEWED
records. `PRODUCTION` exposes only fully valid APPROVED records. Non-production
results are marked preview, are non-chargeable, and cannot be persisted as a
formal report. The external request model contains no draft-access switch.

Status transitions are schema gates: REVIEWED requires reviewer, review time,
and complete core content; APPROVED additionally requires approver, approval
time, prohibited inferences, evidence direction, and evidence strength. A
blank record cannot be promoted with `model_copy`. DRAFT and REVIEWED never
receive formal K evidence IDs.

Selected records are converted into typed `KnowledgeEvidence`, not bare IDs.
Production APPROVED records use `K-H-55` / `K-L-55-2`; REVIEWED previews use
`R-` and DRAFT previews use `D-`. Prefix, status, source type, and preview flag
are cross-validated. Production accepts only K records. R/D content is exposed
only in the corresponding internal preview policy and is always non-chargeable
and non-persistable.

Each KnowledgeEvidence includes its content, boundaries, polarity, strength,
version and review provenance. Prompt payloads carry structured evidence, not
just IDs. Validator indexing combines Phase 1 Evidence and selected
KnowledgeEvidence for existence, direction and prohibited-inference checks.
Program reports retain KnowledgeEvidence in a separate trace; it is never
inserted into the frozen Phase 1 chart Evidence tuple.

`reviewed_at` and `approved_at` are timezone-aware datetime fields. Naive or
invalid datetimes are rejected, and approval cannot precede review. Reviewer
and approver identifiers are trimmed and require at least three characters;
fixtures use non-personal stable identifiers.

Knowledge records may not alter the Phase 1 chart, moving line, body/use,
five-element relations, evidence, or timing output.

Canonical data version: `MEIHUA_CANONICAL_TEXTS_V1`.
Interpretation knowledge version: `MEIHUA_INTERPRETATION_KNOWLEDGE_V1`.

Normalization is limited to whitespace trimming, `無 → 无`, punctuation
normalization, and the documented source-format repair for hexagram 8.
