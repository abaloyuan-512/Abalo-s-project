# V014 decision log

- The orchestrator consumes only strict builtin JSON data; it never executes Router code.
- PASS has no fields, ASK_ONCE has only a typed ambiguity kind, and FAILED has only a stable failure code.
- Fixed clarification prompts are owned by the program.
- High uses the authoritative prepare/process service with an internally constructed offline fixture provider.
- Router callback executions and Router casts are structurally zero, not inferred from a runtime hook.
- `deterministic_cast_count=1` means authoritative prepare returned `DirectReadingPreparedRequest`; that return is reachable only after the frozen service completed deterministic cast and packet construction. Runtime counted-cast tests independently verify the same invariant; the offline ledger is a path record, not a standalone instrument.
