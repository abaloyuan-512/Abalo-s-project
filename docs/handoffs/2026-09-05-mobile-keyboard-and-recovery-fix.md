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
- In-app browser actual viewport 390x844: submit x=24, y=696.10; focused-input resize to 390x460: same coordinates, casting canvas remained 844px. This emulates keyboard occlusion; actual Huawei IME remains a phone acceptance item.
- Widths 320/360/390/430: all three number fields fit horizontally, no button overlap. At 320x568 canvas client height 568, scroll height 659, submit y=512.10; submit was reachable and completed fixture flow to P7 and P8.

## Deployment/acceptance

Pending at initial commit. New URL remains https://guanxiang-mobile-beta.onrender.com. Do not report live fix or mainland no-VPN success until separately verified.
