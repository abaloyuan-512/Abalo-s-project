# Medium reasoning evaluation contract (frozen before live calls)

## Cases and high-effort comparators

The three medium candidates are `DR-01-Q1`, `DR-03-Q2`, and `DR-04-Q2`.

- `DR-01-Q1` is compared with the fresh V002 Prompt V2 high canary.
- `DR-03-Q2` and `DR-04-Q2` are compared with the already frozen V1.1
  high-effort candidate outputs in `direct_reading_v2_research_v0011/runs/remaining_run.json`.

The latter two comparisons are product-quality/performance references, not a
pure one-variable model experiment, because their prompt version predates V2.

## Blind order and rubric

After all three medium calls are complete, the builder creates a fresh
cryptographically random 256-bit private seed and uses it to assign A/B.  The
seed and mapping are written only to the private mapping file; the blind pack
contains neither.  The independent acceptance reviewer receives only the pack
and its hash and must freeze its scores before the private mapping is opened.

Each answer first faces six hard gates: complete natural ending; correct
base/mutual/moving/changed facts; direct answer to the question; all four
layers play distinct roles; contains do/not-do/reverse-risk/turning-condition;
and no invented facts, date, guaranteed result, mind-reading, or unsafe quote.
Any hard-gate failure loses that case.

If both pass, the reviewer chooses A, B, or TIE using six equal product-value
dimensions: directness, four-layer reasoning chain, question specificity,
actionability and boundaries, factual discipline, and overall user value.

Quality adoption gate: MEDIUM must pass all hard gates and be no worse than
HIGH (win or tie) in all 3 cases.  Otherwise V002 retains HIGH.

## Latency formula

The comparison uses the sum of the three recorded end-to-end provider
latencies for each arm:

`improvement = 1 - (sum_medium_latency_ms / sum_high_latency_ms)`

MEDIUM passes the latency gate only when improvement is at least 25%.  The
frozen high latencies for the two research comparators are 74,331 ms
(`DR-03-Q2`) and 81,373 ms (`DR-04-Q2`); the fresh V002 high canary supplies
the third value.  Token counts are recorded but are not an adoption gate.

MEDIUM is selected only if both the 3/3 quality gate and the >=25% latency gate
pass.  In every other outcome, including incomplete evidence, HIGH is selected.

## Call marker discipline

Creation of a phase `.started` marker means the phase may have consumed its
authorized calls.  If its result file is missing or corrupt, the phase must be
counted conservatively as consumed and must not be rerun.
