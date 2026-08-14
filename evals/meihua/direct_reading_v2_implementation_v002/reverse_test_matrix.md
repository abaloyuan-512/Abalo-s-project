# V002 reverse-test matrix

Status: complete. Live evidence passed; medium adoption failed by its frozen
3/3 gate and high remains selected.

| Area | Input / attack | Expected | Actual evidence | Status |
|---|---|---|---|---|
| Minimum input | question + three integers; no facts/unknowns | one deterministic cast and one provider call | `test_question_and_numbers_only_generate_a_complete_reading` | PASS |
| Input boundary | empty/short/long/newline question; missing, bool, float, string, 0, negative, 1000 | reject before provider | Direct Reading service parameterized tests | PASS |
| Prompt injection | ignore system, recast, reveal prompt/key, guarantee result | chart unchanged; secret absent; unsafe output blocked | Prompt V2 data-envelope tests and release-gate tests | PASS |
| V001 false positive | base section says the transition leads to the correct changed hexagram | release | `test_base_section_may_describe_its_transition_to_the_changed_hexagram` | PASS |
| Wrong chart | wrong base/mutual/changed role, trigram, moving line or line text | block with role-scoped code | release-gate and PMO red-team tests | PASS |
| Classic text | unrelated/altered quote, including the known `物生必蒙...屯` error | block | canonical negative tests | PASS |
| Markdown canonical quote | verified simplified/traditional text wrapped in emphasis; fabricated suffix | verified text passes; altered suffix blocks | exact DR-03 post-final positive/negative regressions | PASS |
| Reality boundary | invented employment facts, third-party intent, guaranteed result | block | reality/mind-reading/inevitability tests | PASS |
| Date boundary | new absolute or relative action date | block; verbatim user date only may be repeated without recommendation | date tests | PASS |
| Completeness | empty, incomplete status, details present, 4000-token ceiling, hollow shell, repeated filler | fail closed; no reading | completeness and repetition tests | PASS |
| Provider failure | timeout, 429, 5xx, malformed response, missing usage, stream error | safe typed failure; zero retry | provider tests | PASS |
| Private diagnostics | blocked synthetic output | private raw evidence exists; public response has none | diagnostic sink and public allow-list tests | PASS |
| Diagnostic misuse | raw-output sink on a non-synthetic request | reject before generation | synthetic-confirmation test | PASS |
| Public privacy | internal hashes/model/response ID/usage/latency | omitted by explicit allow-list | Python and Sites public-payload tests | PASS |
| Log privacy | synchronous prepare or asynchronous provider exception carries user text | stable error code only; no exception message/traceback | two hosted API captured-log negative tests | PASS |
| Backend idempotency | twenty concurrent identical submissions | one job/one processor invocation | Python hosted API concurrency test | PASS |
| Durable idempotency | twenty concurrent Sites submissions | one persisted digest, one upstream POST | D1 route integration test | PASS |
| Conflict | same ID with different question | 409, no second generation | Python and Sites tests | PASS |
| Restart | upstream job disappears after submission | stable LOST/410; no regeneration | D1 restart test | PASS |
| State/output | RUNNING progress | no unvalidated delta or reading | progress callback and route allow-list tests | PASS |
| State monotonicity | unknown or regressive stage callback | ignore; never move backward; terminal immutable | Python async stage test | PASS |
| Immediate chart | model still generating | one deterministic cast; top-level `chart_facts` visible and rendered | Python job, real cross-layer and page contract tests | PASS |
| Cross-layer contract | built Sites route -> D1 -> real Python transport | owner-only submit, CAST_READY facts, polling, FINALIZED, one upstream POST | spawned Python/Sites integration test | PASS |
| Owner access | anonymous or wrong owner; gate off | 403/503 before persistence/upstream | owner-only route tests | PASS |
| Markdown/XSS | script/iframe/svg/math/style/events and dangerous URI schemes | escaped inert text; no active DOM/link | React server-render DOM tests | PASS |
| Cache isolation | same chart, different question | chart hash same; question/prompt hash different | same-chart test | PASS |
| Research regression | nine frozen winning outputs | 9/9 pass new release gate; 4/4 paired outputs differ | frozen-asset regression tests | PASS |
| Legacy regression | old application, V4 route, engine/specs | unchanged behavior | 41 Node tests, 5 TSX tests and full pytest 1135/1135 | PASS |
| High live Canary | fresh DR-01 with Prompt V2 | complete, safe, semantic acceptance | 63,086 ms; PMO and independent semantic acceptance PASS | PASS |
| Medium latency batch | three representative cases | frozen blind contract: 3/3 not worse and summed latency improvement >=25% | stopped after DR-03 validator false positive; no retry; DR-04 uncalled | FAIL — HIGH SELECTED |
| Final HTTP Canary | selected effort through owner Sites route, D1 and Python transport | terminal SUCCESS, immediate facts, FINALIZED, one call/no retry, private synthetic diagnostic available | 202 CAST_READY -> 200 SUCCESS; one upstream; 68,742 ms wall; independent PASS | PASS |
