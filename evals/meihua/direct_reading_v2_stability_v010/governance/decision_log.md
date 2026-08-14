# Decision log

| ID | Decision | Basis |
|---|---|---|
| D-001 | Use two new cases only | Minimum coverage of commitment and stop-loss anti-bias axes |
| D-002 | Execute sequentially and stop on first failure | Failure remains in denominator; prevents replacement or budget creep |
| D-003 | Keep 12000 only as truncation headroom | V009 used 3755 output tokens; length target remains unchanged |
| D-004 | Do not touch existing product/UI differences | They are outside the frozen candidate and belong to existing worktree WIP |
