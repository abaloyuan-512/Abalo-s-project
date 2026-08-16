# P9 天地北斗终章 · Design QA

## Comparison target

- Source visual truth: `C:/Users/27622/.codex/generated_images/01a000bd-73ef-7c90-9b44-a17316089997/exec-c8356fe9-ba2d-4b0a-973a-d663bd1a0602.png`
- User-reported state: `C:/Users/27622/AppData/Local/Temp/codex-clipboard-939368b2-8c2f-44e1-a079-929ee980bc06.png`
- Implementation: `http://localhost:4174/direct-reading-v2-preview?offline-p9=1`（development-only）
- Final implementation screenshot: `docs/handoffs/assets/p9-offline-design/qa/p9-final-buttons-1280x720.jpg`
- Full-view combined comparison: `docs/handoffs/assets/p9-offline-design/qa/p9-source-vs-final-buttons.jpg`
- Focused control comparison: `docs/handoffs/assets/p9-offline-design/qa/p9-controls-source-vs-final-buttons.jpg`

## Normalization and state

- Source pixels: 1536 × 1024. Implementation pixels and CSS viewport: 1280 × 720; device pixel ratio 1.
- The source was resized to 1280 × 720 for the combined comparison, matching the implementation's explicit full-frame fill policy. Both sides show the same gua, answer and idle constellation state.
- The source still contains the superseded button copy; geometry, typography, palette and art direction—not old action semantics—are the visual comparison target.

## Required fidelity surfaces

- Fonts and typography: passed. The existing brush/Kai stack, title hierarchy, gua label, two approved answer lines and button optical weight are preserved.
- Spacing and layout rhythm: passed. P9 remains one viewport with no scroll or cropped constellation. Actions remain fully visible at 1280 × 720.
- Colors and visual tokens: passed. Background, ink, cinnabar and gold retain the approved pale xuan-paper balance. Star animation applies no CSS filter, so its hue is identical to the star asset.
- Image quality and asset fidelity: passed. The 1536 × 1024 WebP background and transparent PNG star asset are reused; no CSS-drawn substitute replaces the artwork.
- Copy and content: passed. Primary actions are now `继续追问` and `分享解卦`; the automatic save notice is subordinate to both actions.

## Interaction and accessibility checks

- Star overlay anchors were recalculated from the background source pixels. The PNG's alpha-weighted visual center is used (`40.87% 49.85%`), eliminating geometric-center drift during scale.
- Browser samples showed every animated visual center equal to its CSS anchor within 0.001 CSS px, including while scaled. At 1280 × 720, sampled anchors were `(229.938, 68.175)` through `(637.837, 83.713)`.
- Each cycle selects 1–3 unique stars. The animation lasts 7.2 seconds, with a slow rise to the 46–54% plateau and a slow fall. Computed `filter` is `none`; sampled opacity changed continuously while the anchor stayed fixed.
- `prefers-reduced-motion: reduce` cancels the star and answer animations.
- `继续追问` is an explicit query-gated path only. Browser verification reached existing P3, showed the textarea, removed the one-shot query parameter and focused `#primary-question`.
- Every completed P9 record is written automatically to the local observation book. The subordinate `本次已自动存入观事簿` control opens a modal containing the exact current question, gua and two-line answer.
- `分享解卦` first attempts system file sharing; if unsupported or rejected, it downloads a portable HTML. Browser verification reached the fallback success notice.
- The latest exported HTML was 21,968,323 bytes and contained P3 once, P7 once, five P8 acts, P9 once, nine embedded images and zero external HTTP asset references.
- Buttons retain semantic link/button behavior, focus-visible treatment, 52 px target height and the finalized four-corner concave rounded contour. Modal Escape/focus restoration and `aria-live` status remain intact.
- Browser console check found no error-level entries.

## Comparison history

1. Earlier user evidence showed P1 constellation cropping and imperceptible star motion. The art plane and safe-area constellation asset were corrected.
2. A later comparison found P2 tone drift and a control-shape mismatch. The pale source tone and finalized corner language were restored.
3. This round found P1 star-overlay drift from using the PNG rectangle center rather than the visible star center, P2 animation speed/hue drift, and P1 action-flow gaps.
4. Fixes: pixel-derived star anchors plus alpha-weighted transform origin; 7.2-second filter-free breathing; explicit P3 continuation; automatic record saving; resilient system-share-to-HTML fallback; enlarged rounded concave button corners and a lighter paper fill.
5. Post-fix full-view and focused comparisons show complete constellation containment, aligned star centers, source-consistent palette and the approved control silhouette. No actionable P0/P1/P2 visual difference remains.

## Verification

- Focused component tests: 11/11 passed.
- Local Vinext production build: passed.
- Browser interactions: continue to P3, textarea focus, automatic observation-book entry, modal review, resilient share fallback and exported HTML structure all passed.
- Offline boundary preserved: no deployment, no default-flow switch, no real model call, and no changes to P8, deterministic casting, Direct Reading high prompt/validator, nine-chapter mapping, Router STOP history or legacy entries.

final result: passed

---

# P8 五幕设计验收

## Comparison setup

- Source visual truth:
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-b1258599-3f9b-4662-b28b-b487cd07de4a.png`
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-30f43ad1-815e-4f81-8c84-ad8d7b97605a.png`
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-ba35f955-f8fc-49af-9adf-affdd1916859.png`
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-cac238ca-9098-42d6-8ff0-40c53161b9f8.png`
  - `C:/Users/27622/AppData/Local/Temp/codex-clipboard-4b5a38ab-cd8b-4ee8-a017-c0ccb58ecc04.png`
- Implementation evidence:
  - `outputs/p8-ux-fix-20260816/local-p8-base.jpg`
  - `outputs/p8-ux-fix-20260816/local-p8-mutual.jpg`
  - `outputs/p8-ux-fix-20260816/local-p8-moving-line.jpg`
  - `outputs/p8-ux-fix-20260816/local-p8-changed.jpg`
  - `outputs/p8-ux-fix-20260816/local-p8-body-use.jpg`
- Source pixels: 1919 × 1018 including browser chrome; source content region is approximately 1919 × 908.
- Implementation CSS viewport: 1920 × 910 at device-pixel-ratio 1.
- Implementation capture: 1905 × 902 after the in-app browser's native scrollbar/crop.
- State: P8 detailed-reading mode, one active scene at a time, desktop viewport.
- Normalization: comparison used the same desktop content height and scene state; browser chrome was excluded from implementation evidence and ignored in the source.

## Findings

- No actionable P0/P1/P2 mismatch remains.
- Fonts and typography: existing brush, kai and body-font hierarchy is preserved. Enlarged trigram names, moving-line position and the fifth-scene summary remain readable without crowding or clipping.
- Spacing and layout rhythm: all five scenes fit the desktop viewport. The former footer/debug block is absent, “结合所问” uses the released space, and the fifth-scene CTA remains visible without an inner scroll.
- Colors and visual tokens: the existing paper, ink, cinnabar, mist and gold-photon tokens are unchanged. The CTA uses the product's cinnabar family and has a visible focus/hover state.
- Image quality and asset fidelity: all original water-ink backgrounds and overlays are unchanged. Trigram evidence reuses the existing production brush-line raster assets; no placeholder or synthetic icon was introduced.
- Copy and content: the moving-line scene now contains a modern Chinese explanation after the classical text. Body-use and seasonal-strength values use the frozen Chinese rule labels “用生体、体克用、比和、体生用、用克体” and “旺、相、休、囚、死”. No source hash, model note or user-irrelevant disclaimer is shown.
- Accessibility and behavior: the oracle zoom target is keyboard focusable and labeled. Five-scene navigation, moving-line hover/focus zoom, P9 wheel gate and explicit P9 CTA were exercised. Console error/warning log was empty for the QA route.

## Comparison history

1. Source finding: user-facing source hashes and disclaimers occupied the bottom of every scene; the fifth scene overflowed; deterministic enum values leaked in English; moving-line copy repeated only the classical text; P9 followed the scroll path.
2. Fix: removed the footer/debug presentation, localized frozen enums, reused brush-line assets for trigram evidence, selected the explanatory moving-line paragraph, compacted the fifth scene, and gated P9 behind the “进入观象寄语” button.
3. Post-fix evidence: all five implementation screenshots show the complete scene inside the 1920 × 910 viewport. Scrolling at scene five leaves P9 unrendered; clicking the CTA renders and enters P9.

## Implementation checklist

- [x] Five common footer/debug blocks removed.
- [x] Upper/lower trigram graphics added to base, mutual and changed scenes.
- [x] Moving-line position enlarged and hover guidance added.
- [x] Modern moving-line explanation shown after the canonical line text.
- [x] Body-use and seasonal-strength values localized from frozen specifications.
- [x] Initial/changed use trigram graphics added.
- [x] Fifth scene fits one desktop screen.
- [x] Explicit P8 → P9 button added; wheel no longer enters P9.

final result: passed
