# Mobile keyboard and upstream recovery fix

## Scope

Only the portable beta frontend branch; preserve the frozen Sites deployment and Python service. No algorithm, prompt, credential, compute-plan or database-schema changes. Free Render idle wake-up splash is a hosting constraint, not removed by this patch.

## Evidence and changes

- Phone screenshot overlap: PwaRuntime previously drove all canvas heights from visualViewport.height. Mobile number inputs had fixed top offsets while the submit action was bottom-anchored. IME shrink therefore moved the action into the inputs.
- Separate casting canvas baseline holds through keyboard opening and focusout/closing animation. Real width changes recalculate the baseline. Minimum 660px canvas scrolls within shorter screens; fields use proportional horizontal placement. Last numeric Enter dismisses focus instead of submitting.
- Actual upstream logs at 21:12–21:14 showed non-JSON HTTP 429 for intake and submit. This is distinct from the application's JSON six-per-hour gate. Exact gateway policy is not established; do not claim cold start alone explains 429.
- Portable-only read-only health probe precedes model submission. Unready service returns not_submitted and Retry-After; no automatic model POST replay.
- Non-JSON/429 submission responses preserve the original request for query-only recovery. Missing chart facts in an idempotent 202 response no longer encourage regeneration. Primary/recovery controls observe cooldown and preserve uncertain request identity.
- Diagnostic logging remains metadata-only; no keys, questions or response bodies.

## Local checks

- Portable build and TypeScript checks passed.
- Portable integration + recovery unit tests: 10 passed. Real Python deterministic/HTTP code is used, but model text is a fixture, not a live quality check.
- Sites regression suite: 51 Node tests + 13 TSX tests passed. Default Sites build also passed.
- Lint: zero errors, 51 warnings.
- Python regression: 1477 passed in 169.13 seconds. No engine source changes.
- In-app browser actual viewport 390x844: submit x=24, y=696.10; focused-input resize to 390x460: same coordinates, casting canvas remained 844px. This emulates keyboard occlusion; actual Huawei IME remains a phone acceptance item.
- Widths 320/360/390/430: all three number fields fit horizontally, no button overlap. At 320x568 canvas client height 568, scroll height 659, submit y=512.10; submit was reachable and completed fixture flow to P7 and P8.

## Deployment/acceptance

Commit 9fd85f001fd4829db95d38f9924b17da1cb3f1d1 uploaded via GitHub Git Data API with exact tree/commit verification and non-force fast-forward. Render Free manual deploy dep-dae29hfqj5pc73a03lmg started at 22:18:45 GMT+8. New URL remains https://guanxiang-mobile-beta.onrender.com. Do not report live fix or mainland no-VPN success until separately verified.

## Cold backend reproduction and follow-up

- First live request drv2-157d77b8761c4dcd89cf47f1a1f5f7bd returned 503/not_submitted because server-to-server health returned 429 immediately.
- Ordinary client GET to the backend's public /healthz took 43.441 seconds then returned 200 with unchanged backend commit 12c5f4307b16.
- Reusing the same unsubmitted ID then returned 202/CAST_READY; subsequent query returned SUCCESS with product_presentation and page9_finale, automatic_retries=0. This is a real live generation, unlike the local model fixture.
- This isolates a cold-backend connection problem: waking the backend through the ordinary public client made the same server-to-server path work. Exact platform 429 policy remains unverified.
- Follow-up: user entering the app initiates a single-flight browser GET to the public Render /healthz. It sends no question, numbers, credentials or referrer, uses no-cors, and never interprets an opaque response as proof of readiness. Intake/submission await this bounded wake attempt, then the server still checks actual JSON health before any model request. No background keep-alive loop, service upgrade, backend modification or model replay.
- The portable-only /api/service-wakeup endpoint exposes only a validated public HTTPS *.onrender.com health URL; internal, credential-bearing and non-Render URLs are rejected.

## Final checkpoint

- Follow-up commit b4919759648014eaed4ce7fdc7b10f61722f1233 was verified on GitHub and deployed to the same Free service. Render UI showed Deploy succeeded|Live, start 22:35:57 GMT+8, duration 1m49s. No paid plan or old backend/Sites changes.
- Final build/type checks passed. Tests: 51 Node + 13 TSX + 13 portable/recovery; Python 1477 passed. The small extra hint/error spacing change was verified in the actual local browser.
- Simulated 429 UI: countdown and retry button disabled; error explicitly says not submitted. At 390x844, submit bottom 761, error top 764/bottom 779, recovery top 795. Under focused resize to 390x460, submit y remained 696.10; keyboard hint bottom 268.85, input field top 299.80, no overlap.
- From 22:27 until after 22:43, no deliberate backend probes were made. Only normal entry at the new URL was then attempted through the browser. Browser control interrupted during this flow. At 22:49 the new frontend submitted drv2-788a54762a504896b15eee4214d1dc84 and received 202/CAST_READY, showing the connection path worked without a second manual backend wake-up. Do not overstate this as a complete real-phone cold-start test or independently confirmed sleep event.
- That second real generation ended BLOCKED_OUTPUT / OUTPUT_VALIDATION_FAILED / failure_stage CONTENT, retryable=false. No result was published, no automatic retry, and no validator/prompt/algorithm relaxation. The earlier live request succeeded, so end-to-end content reliability is NOT fully accepted. This content-quality issue remains separate from the repaired transport parsing and keyboard layout bugs.
- Mainland no-VPN/Huawei actual IME acceptance remains with the user. Free frontend idle-loading splash remains expected.
