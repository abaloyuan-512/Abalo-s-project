# Direct Reading V2 non-production implementation V002

Status: `IMPLEMENTATION_AND_LIVE_VALIDATION_COMPLETE_POST_FINAL_REMEDIATION_VERIFIED`.

This stage implements an isolated owner-only Direct Reading path whose required
business input is only the original question and three deterministic casting
integers. It does not change the production-default journey, the deterministic
Meihua rules, canonical texts, or the legacy entry points.

## Scope

- repair the V001 false-positive release-gate path;
- isolate untrusted question data in Prompt V2;
- add private diagnostics for synthetic canaries without exposing raw text in
  public responses or ordinary logs;
- add an idempotent asynchronous non-production transport;
- add an owner-only preview with safe Markdown rendering;
- validate latency with a maximum of five new live calls and zero automatic
  retries;
- complete independent PMO and acceptance review.

## Fixed boundaries

- AI never casts or changes the chart;
- no new date is generated when the program did not supply one;
- reality assumptions may not be presented as chart evidence;
- production remains disabled and legacy routes remain available;
- any live call requires a frozen execution snapshot and a PMO GO decision.

## Stage result

- the isolated Direct Reading V2 path passed its high-effort semantic Canary
  and its final Owner Sites -> D1 -> Python HTTP Canary;
- the final path returned deterministic chart facts immediately, then one
  complete validated answer after exactly one upstream submission;
- V002 used four actual model calls, consumed all five authorized slots and
  performed zero automatic retries; no further V002 model call is permitted;
- the medium experiment did not meet its frozen 3/3 acceptance contract, so
  `high` remains the selected reasoning effort;
- a post-final, offline-only normalization repair closes the observed false
  block for correctly quoted canonical text wrapped in Markdown emphasis;
- production remains disabled. This stage does not authorize migration or
  deployment.
