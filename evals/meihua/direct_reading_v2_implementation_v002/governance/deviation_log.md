# Deviation log

## DEV-V002-001 — initial full-suite temp location

The first full-suite command placed pytest temporary files inside the
repository. Twenty legacy live-evaluation tests correctly rejected that
location. No product code was changed to bypass the guards. The suite was
rerun with an explicit repository-external directory and passed 1124/1124.

## DEV-V002-002 — repository-wide lint baseline

The complete Sites lint command remains red because the unchanged legacy
`GuanxiangApp.tsx` contains four `react-hooks/set-state-in-effect` findings and
34 existing image warnings. All files created or edited for Direct Reading V2
pass their targeted ESLint run. V002 does not change the production-default
application merely to clean unrelated lint debt.

## DEV-V002-003 — Windows local-prototype connection reset

The first post-fix full suite exposed a deterministic Windows TCP reset in the
pre-existing loopback Phase 3B prototype when it returned HTTP 415 without
draining a five-byte rejected request body. The isolated test failed again on
immediate rerun. The local review server now drains only a bounded declared
body before its 415 response; its focused regression passes and the subsequent
full suite passes 1134/1134. This does not change any divination rule, formal
API contract, production route or legacy user entry point.

## DEV-V002-004 — medium stopped on a release-gate false positive

The medium batch produced one SUCCESS and then stopped on DR-03-Q2 as frozen.
The second answer had the correct chart and moving line, but formatted the
verified line text as bold Markdown inside quotation marks. `_normalized_quote`
retained the `**` markers, so exact canonical matching emitted both
`UNSUPPORTED_CLASSIC_QUOTE` and `MOVING_LINE_MISMATCH`. This is a validator
false positive, not a model or divination-fact error. Medium nevertheless fails
the frozen 3/3 gate; DR-03 and the uncalled DR-04 are not rerun. The validator
repair is deferred until after the frozen final canary and will require a new
test/freeze, not retrospective alteration of this evidence.

## DEV-V002-005 — local shell timeout before the final marker

The first local command wrapper used a one-second process timeout and stopped
during preflight. Read-only inspection found no final marker, no surviving
process and no model call. The same authorized phase was then executed with an
adequate wait window. This event consumed neither a model attempt nor a retry;
the successful frozen runner still recorded exactly one final attempt.

## DEV-V002-006 — intentional post-final validator drift

After the final V3 result was durably written, the validator and its tests were
changed to close DEV-V002-004. V3 consequently no longer matches the current
working files, by design. The final run remains reproducible from the preserved
V3 archive and predates the edit. Current post-final files are frozen under a
separate remediation snapshot and must not be represented as the live Canary
implementation.
