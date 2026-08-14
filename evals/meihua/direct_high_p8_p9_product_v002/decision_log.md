# V002 evidence decision log

- V001 remains `OFFLINE_CANDIDATE_FAIL_STOP`; no V001 candidate byte is repaired or re-reviewed.
- V002 exists only to close V001 D12–D15 evidence completeness gaps.
- The independent contract requires every negative to begin with one complete fixture transaction. Therefore the frozen denominator uses 3 positive and 12 negative rows, each with 1 prepare, 1 deterministic cast, 1 fixture provider/high attempt, and 0 retry.
- Consumer negatives retain their unchanged mapper/Pydantic rejection as intermediate evidence, then pass the tampered payload through the unchanged compiled Sites public boundary; final `BLOCKED_OUTPUT` and all three null-release fields come from that actual boundary response.
- Prepare and fixed-high attempts are counted independently immediately around the authoritative prepare and `process_prepared` service calls; neither count is inferred from provider calls.
- No live call, Router call, deployment, production write, default switch, or P9 artwork is authorized or performed.
