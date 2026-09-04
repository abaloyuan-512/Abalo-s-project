# P1 Mobile Motion Study — Design QA

- Frozen website: out of scope and unchanged.
- Isolated implementation: `sites/hosted-app/app/p1-motion-preview/`
- Local preview: `http://localhost:4173/p1-motion-preview`
- Approved terminal artwork: `public/p1-motion-ink-realm-v1.png`
- V2 pre-reveal base: `public/p1-motion-pre-reveal-base-v2.png`
- Commit/publish/deploy: none.

## V1 — Rejected

User verdict: **FAIL**.

- The repeated full-artwork layers read as a static image that briefly blurred and sharpened.
- The CSS radial mask exposed a rectangular raster/mask boundary instead of a believable ink drop.
- The result did not create an authored water-and-ink event and must not be reused.

## V2 — Rejected

User verdict: **FAIL**.

- The falling ink drop did not read clearly as a drop arriving from above.
- The noisy reveal field appeared as mosaic-like cells rather than water ripples.
- The blocky reveal conflicted with the continuous ink-wash language and must not be reused.

## V3 — Current candidate

State: **BUILT / AWAITING USER VISUAL ACCEPTANCE**.

- A separate transparent ink-drop asset visibly falls from above before impact.
- The impact ripple is extracted from the approved artwork itself, preserving the original water-and-ink language.
- The artwork reveal uses a continuous radial water field with smooth feathering. There is no block sampling, grid, random noise or mosaic texture.
- The sequence is: still xuan paper → visible falling drop → impact ripple expands → approved scene is continuously revealed → exact approved raster settles.
- No full-frame blur, focus pulse, rectangular mask, tile transition or endless decorative loop is used.
- The terminal frame remains the exact approved P1 artwork.
- `prefers-reduced-motion` shows the final artwork immediately.

### V3.1 — Original-drop registration correction

- Replaced the separately generated falling-drop artwork with a crop taken from the approved P1 artwork itself.
- Source registration was measured exactly: the full source crop maps to `x=388, y=395` in the 853×1844 terminal artwork; the animated top-drop crop is 26×27 pixels and its visible painted bounds match the original top droplet.
- The falling path crosses the original three painted-drop waypoints before reaching the existing impact ripple.
- At the first registered waypoint, the animated droplet is at the exact original position and scale; there is no substitute droplet shape or guessed alignment.

## Verification

- Build: PASS; `/p1-motion-preview` is present in route output.
- Scoped lint: PASS, 0 findings.
- Impeccable detector: PASS, `[]`.
- Local server: running on port 4173 for user inspection.
- Visual browser automation: not claimed as completed; the in-app browser connection could not initialize because its local runtime dependency is unavailable. User visual acceptance is therefore the next gate.
- Model/API use by preview: none.
- Frozen repository/site change: none.

V3.1 result: **rejected and superseded by the selected concept-film workflow**.

The position and size correction is deterministically registered to the source pixels, but the local in-app browser could not be programmatically captured for a same-frame visual comparison. Do not record final visual PASS until the user inspects the refreshed motion preview.

## Selected concept 1 — local implementation candidate

State: **BUILT / AUTOMATED VISUAL QA BLOCKED / AWAITING USER INSPECTION**.

- The user selected concept film `01-one-drop-opens-the-realm.mp4` from the three animatic options.
- The implementation uses a dedicated 852×1844, 4.5-second H.264 asset: `public/p1-mobile-motion-selected-v1.mp4`.
- The selected film is the single authored P1 moment. The previous canvas/radial-field implementation and separate CSS drop/ripple choreography are no longer used by the preview route.
- Before playback is ready, the approved pre-reveal artwork remains visible. At film completion, the exact approved high-resolution terminal artwork replaces the compressed video frame.
- Autoplay is muted and inline. `prefers-reduced-motion` bypasses the film and displays the terminal artwork immediately.
- The existing transparent CTA hit area is active only after the terminal artwork settles.
- No API/model request, commit, saved site version, deployment or publication occurred.

### Verification

- Isolated build: PASS; `/p1-motion-preview` is present in the route output.
- Scoped lint: PASS, 0 findings.
- Local page response: HTTP 200.
- Motion asset response: HTTP 200, `video/mp4`, 1,535,455 bytes.
- Motion asset metadata: 852×1844, 16 fps, 4.5 seconds, H.264.
- In-app browser control: BLOCKED by a missing runtime-module resolution in the local browser-control bridge. The preview was opened in the Codex browser panel, but no automated screenshot/interaction claim is made.

## Product-owner acceptance

- Acceptance time: 2026-08-20 20:46:03 (Asia/Shanghai).
- Product-owner verdict: **APPROVED / P1 MOBILE VISUAL AND MOTION FROZEN**.
- Accepted direction: concept 1, “one drop opens the realm”.
- Automated browser capture remained unavailable, but the product owner completed direct inspection in the local preview and explicitly approved the result.
- This approval freezes the P1 mobile visual direction and motion asset only. It does not authorize commit, deployment, publication, or any change to the currently frozen website.

Final result: **PASS_BY_PRODUCT_OWNER / P1_MOBILE_VISUAL_FROZEN**.
