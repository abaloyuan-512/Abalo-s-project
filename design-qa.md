# 观象 P8→P9 冻结候选 · Design QA

## Comparison target

- Source visual truth:
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-36033ac2-ae15-4fd7-981d-c149d846d41b.png`
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-2314d314-9184-4e02-a442-115f2ec896e5.png`
- Browser-rendered implementation:
  - `docs/handoffs/assets/p8-p9-frozen-20260816/p8-fifth-scene.png`
  - `docs/handoffs/assets/p8-p9-frozen-20260816/p9-exclusive.png`
- Combined comparisons:
  - `docs/handoffs/assets/p8-p9-frozen-20260816/p8-before-after.jpg`
  - `docs/handoffs/assets/p8-p9-frozen-20260816/p9-before-after.jpg`
- CSS viewport: 1904 × 906; device pixel ratio 1.
- Source content region: approximately 1919 × 911 after excluding browser chrome; normalized to 1904 × 906 before comparison.
- State: P8 fifth scene active, followed by P9 exclusive finale.

## Findings

- No actionable P0/P1/P2 visual or interaction mismatch remains.
- Fonts and typography: passed. The new CTA reuses the existing P6 `method-cta`/`final-question-cta` text hierarchy and the same Taiji asset; no modern pill-button typography remains.
- Spacing and layout rhythm: passed. The CTA is independently anchored at the lower-right (209 × 62 CSS px, 156 px from the right and 59 px from the bottom at the review viewport). Its bounding box does not overlap the left copy region. The fifth scene remains one viewport.
- Colors and visual tokens: passed. The translucent paper, ink and cinnabar hover/focus values remain inside the established P6/P8 palette.
- Image quality and asset fidelity: passed. The CTA uses the existing production `/fuxi-bagua-taiji.svg`; no CSS approximation or replacement icon was introduced.
- Copy and content: passed. The CTA shows only `进入观象寄语`; P9 contains only the frozen P9 content and actions.

## Interaction and accessibility checks

- Entering P9 unmounts the P8 five-scene stage and the P8 CTA instead of appending P9 below it.
- At P9, `scrollY` remains 0 after an upward wheel gesture; the document height equals the 906 px viewport, so P8 cannot be recovered by scrolling.
- The production P9 offline render contains zero `.page8-kun-stage` and zero `.page8-kun-finale-cta` nodes.
- The CTA remains a semantic button and retains the existing focus-visible behavior.
- Browser console warnings/errors for the reviewed states: none.

## Comparison history

1. User evidence showed a modern cinnabar pill inside the lower-left copy region; after transition, that P8 control remained above P9 and the wheel could return to P8.
2. Fix: moved the control outside the copy region, reused the P6 Taiji-plus-text form, anchored it at the screen lower-right, made P9 replace P8, and restored the global forward-only scroll lock during P9.
3. Post-fix evidence shows the P8 copy unobstructed, the CTA in the requested lower-right position, and a P9-only one-screen state. No further P0/P1/P2 fix was required.

## Verification

- Hosted-app production build: passed.
- Hosted-app test suites: 58/58 passed.
- Focused ESLint: 0 errors (pre-existing warnings only).
- Primary interactions tested: fifth-scene navigation, CTA activation, P8 removal, P9-only render and upward-wheel rollback attempt.

final result: passed
