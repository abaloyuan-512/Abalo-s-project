# Sites Meihua API Contract V3

V3 adds a bounded `question_text` and two finite presentation-context fields:
`decision_stage` and `key_uncertainty`. These fields improve the usefulness of
the result page but are never passed into `MeihuaInput`, never alter the chart,
and never become divination evidence.

The deterministic engine remains identical to V2. V3 adds
`SITES_CLARITY_REPORT_V3`, a rule-based, question-aligned decision aid that leads with a direct
answer, observable continue/pause signals, and one reversible next action.

AI narrative remains `UNVERIFIED`; charging and formal report persistence stay
blocked.
