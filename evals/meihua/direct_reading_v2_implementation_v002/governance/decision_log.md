# Decision log

## DEC-V002-001 — parallel non-production path

V002 uses a new owner-only Direct Reading transport and preview. It does not
replace or delete the V4 personalized route or the existing application flow.

## DEC-V002-002 — Prompt V2

The validated V1.1 content requirements remain, while the original question is
encoded as untrusted data and may not override the deterministic chart or
system constraints. This prompt change requires fresh semantic validation.

## DEC-V002-003 — staged output

Streaming lifecycle events may update internal job progress, but model deltas
are buffered. Only a completed and validated answer is released to the user.

## DEC-V002-004 — bounded latency experiment

At most five live calls are authorized: one high-effort correctness canary,
three representative medium-effort latency candidates, and one final selected
configuration end-to-end canary. Any incomplete or hard failure stops the
current sequence. There are no automatic retries.

## DEC-V002-005 — deterministic preparation precedes generation

The service validates and casts once before starting the model.  The resulting
base, mutual, moving-line and changed facts are exposed through the public
allow-list while the unvalidated model output remains private.  Polling and
duplicate submissions never recast or invoke the provider again.

## DEC-V002-006 — medium adoption and blind order

`medium_evaluation_contract.md` freezes the three comparators, six hard gates,
six product-value dimensions, private random A/B assignment, unblinding order and the
latency formula before any live result exists.  Medium is adopted only with
3/3 quality non-inferiority and at least 25% summed-latency improvement;
otherwise high remains selected.

## DEC-V002-007 — markers consume authorization conservatively

Once a live phase `.started` marker exists, the phase is treated as possibly
consumed even when its result file is absent or corrupt.  The phase is never
rerun.  This prevents a crash or evidence failure from silently creating an
extra paid call.

## DEC-V002-008 — final canary covers the private transport

The fifth call runs through the built Sites owner route, the persistent D1 job
contract and the actual Python async transport.  The Python server receives an
explicit synthetic-only private diagnostic sink, while the route and page
receive only the public allow-list.  This replaces the earlier Python-only
canary design.

## DEC-V002-009 — actual calls and consumed authorization slots are separate

The medium phase stopped after its second actual call, so actual cumulative
calls are three (one high plus two medium).  Its phase marker closes all three
authorized medium slots, so four slots are conservatively consumed.  The final
controller requires both facts (`actual=3`, `slots=4`) before it may use the
fifth authorization slot.  Neither number may be rewritten to disguise the
stopped case.

## DEC-V002-010 — high remains selected

The medium batch did not complete the frozen three-case acceptance set. It is
therefore a formal failure even though the stopped answer's content was sound.
High is selected for the final Canary. No medium case is rerun and the missing
third comparison is not reconstructed after the fact.

## DEC-V002-011 — post-final remediation is separate from live evidence

The live final Canary remains attributable to frozen execution candidate V3.
The subsequent Markdown canonical-normalization repair is an offline
post-final remediation with its own tests and snapshot. It does not alter the
medium verdict or claim that the repaired validator ran during the final call.

## DEC-V002-012 — V002 live budget is closed

The stage closes with four actual calls, five consumed authorization slots and
zero automatic retries. No further V002 model call is permitted. Production
and the production-default journey remain disabled pending a separately
authorized migration stage.
