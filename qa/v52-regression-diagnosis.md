# Sites v52 regression diagnosis

Date: 2026-08-02

## Evidence

- Page 6 user screenshot: `qa/v52-regression-page6-user.png`
- Page 3 user screenshot: `qa/v52-regression-page3-user.png`
- Page 6 finalized implementation evidence: `C:/Users/27622/.codex/worktrees/4f6b/Abalo-s-project/sites/hosted-app/design-qa-casting-left-inputs-comparison.png`
- Page 3 finalized v11 evidence: `qa/inquiry-cloud-horizontal-v11-final-t1.png`

## 1. Page 6 — interaction and layout regression

Health: broken / blocking.

- The three numeric `input` elements and their React `onChange` handlers still exist and are not disabled.
- A live-flow check reached Page 6 and confirmed the first spinbutton can receive focus. The user's Chrome report that no digits can be entered remains a blocking compatibility/interaction defect and must be retested after layout restoration.
- The finalized Page 6 CSS from worktree `4f6b` was later overridden by commits `24332f5` and `86206dc` while enforcing one-screen flow.
- The overrides reduced heading padding, title margins, contemplation margin/gap/font size, and the margin above the three-breath number field. They also absolutely positioned the whole left heading block and limited it to `min(510px, 31vw)`.
- The empty inputs have no border or placeholder. After the width and spacing regression, the remaining hit area is visually blank and focus feedback is effectively invisible, creating the reported “click does nothing” experience.

Required repair: restore the finalized `4f6b` Page 6 composition and spacing, preserve the one-screen container only, then verify mouse focus, keyboard entry for all three fields, visible values, validation, and the `成卦` transition at the user's desktop viewport.

## 2. Page 3 — incorrect image composition

Health: broken visual composition.

- v52 renders `question-cloudfall-base-v6.png`, a clipped patch from the full `question-cloudfall-final-v7.png`, and the separate animated `question-pine-tree-v2.png` at the same time.
- The patch is cut with `clip-path: polygon(0 71%, 12% 72%, 22% 78%, 30% 88%, 38% 100%, 0 100%)`. Its raster tone does not match the surrounding live composite, so the boundary reads as a curved/diagonal patch.
- The clipped full image contains the original lower trunk and rocks while the animated pine contains another complete trunk. Because the two layers do not move together, the visible root disconnects and appears to grow from the middle of the trunk.
- v52 also forces every inquiry ink layer to `object-position: center bottom`. On a wide viewport, `object-fit: cover` therefore crops much more from the top, pushes the mountain peak upward, and removes the broad upper cloud-sea band seen in the finalized v11 composition.

Required repair: remove the clipped raster patch approach; return to one continuous finalized landscape coordinate system, position the full scene lower as in v11, and preserve pine motion with a mask/anchor that never separates the crown/trunk from the fixed root and rocks.

## Evidence limits

- Screenshot evidence proves the visual regressions.
- The live DOM proves the numeric inputs exist and can receive focus in the in-app browser. The user's exact Chrome failure still needs a post-fix real-browser typing test; it should not be dismissed as solved by the DOM focus result alone.
