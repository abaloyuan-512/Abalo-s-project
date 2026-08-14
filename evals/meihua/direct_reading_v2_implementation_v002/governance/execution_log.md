# Execution log

- 2026-08-11: user approved the V002 implementation plan and a maximum of five
  non-production live calls with zero automatic retries.
- 2026-08-11: independent PMO and acceptance agents were created. Both are
  read-only and may not modify scope or implementation.
- 2026-08-11: PMO issued an initial NO-GO until an immutable baseline snapshot
  exists. Baseline file and tree hashes were recorded before V002 edits.
- 2026-08-11: saved the 22-entry baseline archive at
  `snapshots/baseline_candidate.zip`; SHA-256 is
  `37ED9B56A895ADD8B2700C8E0BDCBD3F25C9833AB56210529AA82E764E784044`.
  V002 implementation may now begin without losing the post-V001 candidate.
- 2026-08-11: added `snapshots/baseline_supplement.zip` for the two locked
  legacy entries, frozen high-effort research outputs, and Sites package and
  persistence files; SHA-256 is
  `FB4D1440D3CE7F0992E61DA9252FD3CA16061AC8179B803BAECA7B6378BB2B98`.
- 2026-08-11: implemented Prompt V2, streamed-and-buffered provider events,
  synthetic-only private diagnostics, a public response allow-list, and the
  role-scoped V001 release-gate repair. Direct Reading service tests: 86 pass.
- 2026-08-11: implemented the isolated Python async job path, durable Sites
  request digest/state, owner-only default-off route, lost-after-restart state,
  and a safe React Markdown preview. Python V002-focused tests: 103 pass.
- 2026-08-11: Sites build passed. Existing and V002 Sites tests: 42 pass. New
  Direct Reading files pass ESLint; repository-wide lint still has four
  pre-existing `setState` errors in the unchanged `GuanxiangApp.tsx`.
- 2026-08-11: the first full-suite invocation used an in-repository pytest temp
  directory and correctly triggered 20 legacy evidence-location guards. It was
  rerun with an explicit external temp directory: 1124 pass in 84.78 seconds.
- 2026-08-11: PMO and independent acceptance issued a pre-call NO-GO for a
  cross-layer stage mismatch, missing immediate chart facts, incomplete final
  transport coverage, a 4-versus-6 character contract mismatch, non-monotonic
  progress and exception-log privacy. No model call had occurred.
- 2026-08-11: split deterministic preparation from generation. Python now casts
  once, returns top-level `CAST_READY` chart facts before generation and accepts
  only monotonic stage transitions. The page renders those facts immediately;
  unvalidated model deltas remain private.
- 2026-08-11: the built Sites owner route, D1 contract and real Python transport
  now run in one spawned offline integration. It verifies immediate chart facts,
  polling, FINALIZED persistence, a measured single upstream POST and explicit
  public filtering. The fifth-call runner uses this route and stores synthetic-
  only diagnostics plus internal usage audit outside the public response.
- 2026-08-11: aligned the question minimum to six characters across all three
  layers; added wrong-owner, terminal-gate, stage-regression, synchronous and
  asynchronous log-privacy, final-helper and single-prepare concurrency tests.
  The medium blind rubric, private random assignment, unblinding order and
  summed-latency formula were frozen before live outputs.
- 2026-08-11: after the second independent review, closed the remaining Direct
  submit exception boundary, poll-terminal behavior, private random blind order,
  measured upstream count, single-prepare concurrency proof, synthetic internal
  usage audit and zero-call preflight-before-marker rule. Final offline evidence:
  focused Python 114/114; Sites build, 41 Node tests, 5 TSX tests and targeted
  ESLint all pass. Independent acceptance reran the final full suite at
  1135/1135 in 88.09 seconds before the execution snapshot.
- 2026-08-11: froze the live execution candidate as
  `snapshots/execution_candidate_v3.zip`, SHA-256
  `F5DBF4C38C5F1363CAC3B50ABD56F90A18048600134FDBDD8A233B94A454DB1F`.
  PMO and independent acceptance approved the high Canary and PMO approved the
  final full-chain Canary under the frozen dual-ledger controller.
- 2026-08-11: the high DR-01 Canary passed in 63,086 ms. The medium batch made
  two calls and stopped, without retry, when DR-03 was falsely blocked; DR-04
  was not called. The frozen medium 3/3 gate therefore failed and high was
  selected.
- 2026-08-11: the final owner-only Sites -> D1 -> Python Canary passed with one
  upstream POST and zero retry. It returned `CAST_READY` chart facts in the 202
  response, then `SUCCESS` / D1 `FINALIZED`. Provider latency was 68,416 ms;
  usage was 386 input, 2,938 output and 3,324 total tokens. Run SHA-256 is
  `FF4A00C5913FC0375FEBCC3A926C939C6F6E514AA9C4CD61348B9FDEF525694C`;
  private synthetic audit SHA-256 is
  `3F02CACDAB72DA44D48D56E09CB4F48BAD2133FBA8B0781D93285F166C4C0D67`.
- 2026-08-11: after the final frozen call, repaired Markdown emphasis handling
  in canonical quote comparison. Exact `“**剥之，无咎。**”` now passes while
  `“**剥之，无咎，必成。**”` remains blocked. Focused service tests pass
  94/94; final full pytest passes 1140/1140 in 89.27 seconds; fresh Sites build,
  41 Node tests, 5 TSX tests and targeted ESLint all pass.
