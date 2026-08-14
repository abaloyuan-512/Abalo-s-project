# V017 decision log

- Keep V015 live and V016 offline verdicts permanently FAIL/STOP.
- Repair only receipt atomicity, request binding, mixed/reused receipt rejection, and the missing frozen failure rows.
- Use an internally issued opaque instance token. Only its SHA enters the public projection; callers cannot inject it through the processing API.
- Bind the projection to the current case and original-question SHA. A fixture response is immutable and can be consumed once.
- Reuse V016's frozen usage validation and conservative cost snapshot without changing Router semantics or pricing claims.
- V017 is fixture-only. A future real receipt still requires a newly authorized live call.
