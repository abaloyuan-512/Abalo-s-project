# Direct Reading V2 V002 acceptance report

## Outcome

`V002_ENGINEERING_PASS`

`PRODUCTION_MIGRATION_NOT_AUTHORIZED`

The stage validates that a user can provide only an original question and
three numbers, receive an immediate deterministic chart, and then receive a
complete question-specific reading without completing discernment or question
framing. The final full private chain passed. Production remains unchanged.

## Validated product result

- deterministic chart facts are produced once by the existing engine and are
  visible at `CAST_READY` before model completion;
- the model never casts and receives only the original question plus the
  versioned chart/classic packet used by the validated research design;
- the answer directly decides the user's question and connects base, mutual,
  moving line and changed hexagram into one reasoning chain;
- it includes what to do, what not to do, reverse risks and observable signals
  that would change the recommendation;
- output is fail-closed for incompleteness, wrong chart facts, unsupported
  dates, guarantees, mind-reading, invented reality and unsafe markup;
- the owner-only transport is durable and idempotent, exposes only public
  allow-listed fields and submits upstream exactly once.

## Live evidence

- high semantic Canary: PASS, one call, zero retry, 63,086 ms;
- medium batch: formal FAIL because the frozen 3/3 set stopped after a
  validator false positive; high therefore remains selected;
- final Sites -> D1 -> Python Canary: PASS, one upstream submission, zero
  retry, `CAST_READY` -> `SUCCESS`, D1 `FINALIZED`, 68,742 ms wall time;
- cumulative V002 actual calls: 4; authorized slots consumed: 5; automatic
  retries: 0. The V002 live budget is closed.

## Defects and disposition

1. The V001 role-heading validator could mistake a correct cross-role sentence
   for a wrong heading. V002 fixed it with section/role-scoped checks. Closed.
2. Correct canonical text wrapped in Markdown emphasis could be falsely
   rejected. A post-final normalization repair and exact positive/negative
   regression close the reproduced defect. Closed; historical medium result is
   not rewritten.
3. Python/Sites stage shape, immediate chart display, monotonic state,
   terminal polling, sync/async log privacy, owner gating, durable idempotency
   and measured upstream count all had pre-call gaps. Each was repaired and
   independently retested. Closed.
4. High reasoning still takes about 63-68 seconds in the two accepted calls.
   Immediate chart facts and progress states reduce perceived waiting, but raw
   model latency remains unresolved. Medium cannot be adopted from this stage's
   incomplete frozen comparison. Open, solvable in a separately authorized
   performance phase.
5. Natural-language safety checks remain regex-based and can still have future
   false positives or negatives. The known defect is fixed and adversarial
   coverage is broad, but ongoing telemetry and regression cases are needed
   before production. Residual risk open.

## Verification

- focused Direct Reading service: 94/94 passed;
- full Python suite: 1140/1140 passed in 89.27 seconds;
- fresh Sites build: passed;
- Node route/legacy tests: 41/41 passed;
- TSX safe renderer/page tests: 5/5 passed;
- targeted Direct Reading ESLint: passed;
- deterministic engine, specs, legacy V4, Streamlit and `iching_tools.py`
  remained locked for the live run; production is still disabled.

## Next recommendation

Do not return to discernment as a mandatory prerequisite. If the user approves
the next phase, connect this validated Direct Reading path to a private product
preview first, retain discernment/question framing only as an optional
enhancement, and run a small real-user acceptance and performance exercise.
Production migration, default-path replacement and deletion of old flows each
remain separate decisions.
