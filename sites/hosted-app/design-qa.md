# Design QA

- Source visual truth: `C:\Users\27622\.codex\generated_images\019f9969-4b3e-7e22-a7fb-711a4edec794\exec-5cf3e57a-6a65-4e2c-941f-beb5286207ca.png`
- Secondary effect reference: `C:\Users\27622\.codex\generated_images\019f9969-4b3e-7e22-a7fb-711a4edec794\exec-07677041-4d24-4826-8d73-91c458dffc64.png`
- Implementation screenshot: `.artifacts/final-redesign/desktop-hero-v13.png`
- Same-input comparison: `.artifacts/final-redesign/comparison-hero-v13.png`
- Intended viewport: 1440 × 1024 CSS px, device scale factor 1
- Source pixels: 1536 × 1024
- Implementation pixels: 1440 × 1024
- State: homepage, initial load

**Findings**

- [P2] The implementation keeps more of the existing landscape and navigation than the visual study
  - Location: homepage hero.
  - Evidence: the side-by-side comparison shows the same paper, ink, cinnabar, brush-lettering, vertical prompt, and lower landscape language. The implementation preserves the live site's top navigation and uses a more expansive landscape crop, so the title sits higher and the lower-left scenery is denser than the visual study.
  - Impact: this is a deliberate product adaptation rather than a style change; the selected study remains the composition basis while the existing site identity is preserved.
  - Fix: no blocking change. Revisit only if the user asks for a closer pixel match to the study.

- [P2] Ink-bloom motion could not be captured reliably through browser control
  - Location: the quotation “寂然不动，感而遂通天下之故”.
  - Evidence: the resting state renders correctly at 1440 × 1024 and the hover/focus animation is present in CSS, but browser control timed out while moving the pointer and taking the second screenshot.
  - Impact: motion timing still needs a human glance in the published preview; it does not block the static composition or the rest of the product flow.
  - Fix: verify the hover once browser control is stable, without delaying the AI intake implementation.

**Required Fidelity Surfaces**

- Fonts and typography: visually verified in the deployed desktop capture; the local brush face and Kai-style supporting text retain the selected hierarchy.
- Spacing and layout rhythm: desktop hero visually verified at 1440 × 1024; mobile rules compile but are not yet browser-captured in this pass.
- Colors and visual tokens: existing paper, ink, mist, pine, and cinnabar tokens are preserved.
- Image quality and asset fidelity: the deployed capture confirms the existing landscape, ink texture, seal, and paper grain render sharply at the target viewport.
- Copy and content: verified through server-rendered HTML tests.

**Full-view comparison evidence**

- Completed in `.artifacts/final-redesign/comparison-hero-v13.png`, with the source and implementation shown side by side at 1440 × 1024.

**Focused region comparison evidence**

- The horizontal `观象` lockup and resting quotation region were verified in `.artifacts/final-redesign/desktop-hero-v13.png`.
- Motion-state capture remains pending because the browser-control handoff timed out after pointer movement.

**Primary interactions checked**

- Build-level behavior and server-rendered routes were tested.
- The published homepage route and server-rendered structure were checked in Chrome.
- Hover-state capture and the full guided-intake/journal/download path remain pending for the next stable browser-control pass.
- The page loaded without a product console error in the captured initial state; browser-control telemetry itself reported unrelated connectivity timeouts.

**Comparison history**

- Initial pass: local addresses were blocked.
- Published pass: private Sites deployment opened successfully; source and implementation were compared together at 1440 × 1024. No P0 or P1 visual mismatch was found.

**Implementation Checklist**

- Capture the selected visual and homepage implementation at the same viewport. — done
- Verify the hero landscape crop and brand lockup scale. — done
- Verify the ink-bloom hover/focus effect around the classic quotation.
- Exercise the full guided-intake conversation and final-question edit.
- Verify `/journal`, save/open behavior, and HTML download.
- Check desktop and mobile console output.

final result: passed for the static desktop hero; interaction and mobile capture remain follow-up QA
