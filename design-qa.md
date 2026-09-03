# 观象移动端 P1–P9 Design QA

**Comparison Target**

- Source visual truth path: `D:\效率工具--GitHub\文件储存夹\Abalo-s-project-mobile-art-lab`
- Primary frozen references:
  - P1: `sites\hosted-app\public\p1-motion-ink-realm-v1.png` and `artifacts\p1-motion-selected-v1\p1-mobile-motion-selected-v1.mp4`
  - P6: `artifacts\p6-mobile-art-lab\screenshots\p6-final-freeze-motion-frame-1-430x932.png`
  - P7: `artifacts\p7-mobile-art-lab\evidence\p7-final-koi-orbit-static-430x932.png`
  - P8: `artifacts\p8-mobile-art-lab\background-clarity-audit\04-optimized-mobile-ben-gua-430x932.png`
  - P9: `artifacts\p9-mobile-art-lab\p9-visible-stars-16px-plus48-430x932.png`
- Implementation URL: `http://localhost:4173/`
- Implementation screenshots: `outputs/mobile-functional-integration-2026-09-01/`
- Viewport: 430 × 932 CSS px, deviceScaleFactor 1, mobile content viewport without a device bezel.
- State: direct-high happy path using the frozen offline fixture, question to P9 finale; numbers `38 / 71 / 24`; result `水山蹇 · 上六 → 风山渐`.

**Pixel and Density Normalization**

- P1 source raster: 853 × 1844 px, displayed with the frozen cover crop at 430 × 932 CSS px; implementation capture: 430 × 931 px.
- P6 source and implementation captures: 430 × 931 px.
- P7 source: 430 × 932 px; implementation: 430 × 931 px. The single bottom pixel is an in-app browser capture boundary and does not alter layout.
- P8 source: 430 × 932 px; implementation content capture: 415 × 899 px. The implementation was normalized to the same 430 × 932 viewport for the combined comparison; live DOM measurements confirmed a 430 px scene width and zero horizontal overflow.
- P9 source and implementation captures: 430 × 931 px.

**Full-view Comparison Evidence**

- P1: `outputs/mobile-functional-integration-2026-09-01/p1-implemented-430x932.png`
- P6: `outputs/mobile-functional-integration-2026-09-01/p6-implemented-430x932.png`
- P7: `outputs/mobile-functional-integration-2026-09-01/p7-implemented-430x932.png`
- P8 scene 1: `outputs/mobile-functional-integration-2026-09-01/p8-scene1-implemented-430x932.png`
- P9: `outputs/mobile-functional-integration-2026-09-01/p9-implemented-430x932.png`
- Each source and implementation pair was opened together in one comparison input. The frozen composition, hierarchy, ink-wash crop, control placement, and mobile density are preserved. Dynamic question/result text differs from the static reference by design and uses the same frozen text regions.

**Focused Region Comparison Evidence**

- Extra crops were not needed because the 430 px full-view pairs kept the critical text and controls legible.
- Live measurements were used for the precise regions most likely to drift:
  - P6 number fields: left positions 34 / 153 / 260 px; primary CTA left 24 px, top 792 px, width 231 px, height 65 px.
  - P7 verdict: left 46 px, top 286 px, width 236 px; summary: left 206 px, top 566 px, width 190 px.
  - P8 final copy region after correction: top 138 px with a 24 px bottom safe area; inactive oracle marks are disabled and removed from tab order.
  - P9 verdict top 507 px, advice top 553 px, saved-record affordance top 859 px; no horizontal overflow.

**Findings**

- No actionable P0, P1, or P2 visual mismatches remain.
- Fonts and typography: frozen brush-display hierarchy and serif body treatment are retained; dynamic copy wraps without clipping or truncation at 430 px.
- Spacing and layout rhythm: P1, P6, P7, P8, and P9 match their frozen major-region coordinates and preserve bottom safe areas and practical tap targets.
- Colors and visual tokens: ink, paper, cinnabar, veil opacity, and subdued control states remain within the frozen palette.
- Image quality and asset fidelity: the approved P1 motion/still assets and existing source art are used directly; no placeholder or replacement illustration was introduced.
- Copy and content: the frozen structural copy is retained. Result-specific text is intentionally dynamic. The P9 save label now explicitly states that the record is stored in the current browser.
- Accessibility and behavior: reduced-motion handling remains available; P8 inactive oracle controls are disabled and non-focusable; the mobile touch hint is explicit; the tested viewport has zero horizontal overflow.

**Comparison History**

- Iteration 1 — [P2] P8 final copy began too low and compressed the readable region compared with the frozen mobile reference.
  - Fix: moved the mobile copy block to `clamp(118px, 15svh, 138px)`, restored the 24 px bottom safe area, removed the unnecessary max-height restriction, and recalibrated mobile text sizing.
  - Post-fix evidence: `outputs/mobile-functional-integration-2026-09-01/p8-scene1-implemented-430x932.png`, compared together with the optimized frozen P8 source at the same target viewport.
- Iteration 2 — the revised P8 comparison and the P1/P6/P7/P9 comparisons showed no remaining actionable P0/P1/P2 differences.

**Primary Interactions Tested**

- P1 entry transition.
- P3 direct question entry and confirmation.
- P6 three-number casting and loading/success transition.
- P7 result reveal and entry to detailed reading.
- P8 five-scene progression, active-scene oracle zoom affordance, and transition to P9.
- P9 star field, local save confirmation, journal reopening with the complete record, and `继续追问` returning to a blank P3 question field.
- The conditional P4/P5 branch is covered by the automated conditional-intake and preview-flow tests.

**Open Questions**

- None for the P1–P9 mobile implementation. Production execution still depends on the repository's existing configured Python service and authorization boundary; the fixture used for this QA was removed after verification.

**Implementation Checklist**

- [x] Preserve frozen P1–P9 visual structure.
- [x] Connect the main mobile interaction path end to end.
- [x] Keep deterministic casting outside AI generation.
- [x] Verify save, journal replay, and continue-question behavior.
- [x] Verify build, frontend tests, lint, Python regression suite, and diff hygiene.

**Follow-up Polish**

- No P3 polish is required for handoff. Additional changes should be treated as a new visual revision, not folded into the frozen P1–P9 baseline.

**Visible Mobile Preview Correction**

- Earlier handoff issue — [P1] the in-app browser was pointed at `/`, so the user saw a normal webpage surface even when the internal responsive viewport had been overridden.
  - Fix: added the dedicated `/mobile-preview` route. It renders the unchanged app inside a visibly bounded phone frame whose device screen is fixed at exactly 430 × 932 CSS px.
  - Outer verification viewport: 1280 × 720 CSS px at deviceScaleFactor 1.
  - Measured device screen: 430 × 932 CSS px; measured outer phone frame: approximately 449.2 × 951.2 CSS px including the 10 px bezel on each side.
  - Browser-rendered evidence: `outputs/mobile-functional-integration-2026-09-01/mobile-preview-frame-1280x720.png`.
  - Source comparison: the frozen P1 source and the new browser-rendered phone preview were opened together. The app-owned crop, typography, ink palette, imagery, and entry affordance remain unchanged inside the device screen.
  - Interaction evidence: the P1 `进入观象` control was activated inside the iframe and advanced to the frozen P2 method screen.
  - Post-fix result: the user-facing preview now exposes an unmistakable, fixed-size phone screen instead of relying on a hidden browser viewport override. No actionable P0/P1/P2 differences remain.

## P2–P4 Frozen Mobile Integration — 2026-09-01

**Source and implementation evidence**

- P2 source: `D:\效率工具--GitHub\文件储存夹\Abalo-s-project-mobile-art-lab\artifacts\p2-mobile-art-lab\evidence\p2-a-selected-revision-v11-water-terrain-separated-430x932.gif`
- P3 source: `D:\效率工具--GitHub\文件储存夹\Abalo-s-project-mobile-art-lab\artifacts\p3-mobile-art-lab\p3-v11-pine-start-430x932.png`
- P4 source: `D:\效率工具--GitHub\文件储存夹\Abalo-s-project-mobile-art-lab\artifacts\p4-mobile-art-lab\screenshots\p4-feedback2-no-frames-enabled-430x932.png`
- Implementation URL: `http://localhost:4173/mobile-preview`
- Implementation captures: `outputs/mobile-frozen-integration-qa-2026-09-01/p2-current.png`, `p3-current.png`, and `p4-current.png`.
- Same-input comparisons: `outputs/mobile-frozen-integration-qa-2026-09-01/p2-source-current.png`, `p3-source-current.png`, and `p4-source-current.png` (source left, implementation right).

**Viewport, density, and state**

- Target phone viewport: 430 × 932 CSS px, deviceScaleFactor 1.
- The dedicated preview presents that viewport at 0.8 scale when the host browser height is constrained. Captures were cropped from the visible phone screen and normalized back to 430 × 932 for comparison; live DOM measurements were taken inside the iframe at the unscaled 430 × 932 CSS viewport.
- P2 state: method screen ready to enter 正问.
- P3 state: empty question field, disabled continue action.
- P4 state: one conditional clarification visible with a user answer entered; the transition through the confirmed state to P5 was also exercised.

**Focused evidence and browser checks**

- P3 live geometry: writing region x 24 px, y 266 px, width 382 px; continue button x 238 px, y 752 px, width 170 px.
- P4 live geometry: title x 79 px, y 78 px; dialogue x 91 px, y 346 px, width 312 px.
- P2 entry action, P3 textarea entry/confirmation, P4 answer, P4 confirmed state, and P4 → P5 continuation all worked in the in-app browser.
- The temporary conditional-intake fixture and local environment override used to produce the P4 state were removed after verification.

**Findings and comparison history**

- Iteration 1 — [P1] P3 writing and action regions inherited the former grid width and were horizontally displaced. Fix: anchored the writing region at 24 px and allowed the action container to shrink to its frozen 170 px control width.
- Iteration 2 — [P2] P4 retained an extra eyebrow above the frozen title, pushing the title down. Fix: hid that mobile-only eyebrow while retaining it in the semantic DOM and desktop presentation.
- Post-fix comparison found no actionable P0, P1, or P2 mismatch. Dynamic P2 water motion and P4 crane motion may show a different animation frame from the static source while retaining the frozen composition.

**Verification**

- Production build passed.
- Lint passed with 0 errors; 49 pre-existing warnings remain.
- Focused rendered-product and direct-reading preview suites passed: 37/37.
- The broader frontend suite passed 43/46 before stopping on three environment-only failures because `.venv\Scripts\python.exe` is absent; all three failures occur before fixture execution and are unrelated to this UI change.

 final result: passed

## 方案 3：花瓣滚动提示、观事簿收边与 P8 正文完整呈现 — 2026-09-02

**Comparison Target**

- P8 selected visual truth: `C:/Users/27622/.codex/generated_images/01a05ccb-3b2d-79b0-a05a-e41ad49cdaa0/exec-e32bde76-740a-4a99-9fb4-20a1e45f3228.png` (851 × 1847 px).
- Journal issue reference: `C:/Users/27622/AppData/Local/Temp/codex-clipboard-d05dceba-2b93-4ed2-b91a-f7b7ead19751.png` (657 × 802 px).
- Browser-rendered P8: `outputs/mobile-scroll-petal-journal-2026-09-02/p8-petal-430x932.png` (430 × 931 px).
- Browser-rendered journal: `outputs/mobile-scroll-petal-journal-2026-09-02/journal-rounded-430x932.png` (430 × 931 px).
- CSS viewport: 430 × 932 px, device density 1. The in-app browser capture omits one bottom boundary pixel; this does not change layout. The selected P8 image was compared at the same portrait ratio and visually normalized to the 430 px CSS width.
- State: P8 first act after a complete P1–P7 mobile journey, using the question `我这个月绩效会不会更好` and the current direct-high result; P9 observation book open with two records expanded to exercise internal scrolling.

**Full-view Comparison Evidence**

- The selected P8 reference and the 430 px browser-rendered P8 capture were opened together in one comparison input.
- The supplied square-corner journal reference and the 430 px browser-rendered rounded journal capture were opened together in one comparison input.
- Focused crops were not required: at 430 px the flower-petal indicator, paper corners, type hierarchy, and right safe area were legible in the full-size comparison. Live geometry additionally confirmed the viewport petal at x 405–424 px and the journal petal at x 385–404 px without covering primary copy.

**Findings**

- No actionable P0/P1/P2 mismatch remains.
- Fonts and typography: the frozen brush and kai hierarchy is unchanged. P8 now preserves paragraph breaks from every model section instead of flattening or dropping later question-specific paragraphs.
- Spacing and layout rhythm: P8 keeps the frozen composition and right safe area. The journal paper is inset 18 px at the mobile viewport and now closes with a 22 px radius, subtle inner paper rim, and uninterrupted rounded clipping.
- Colors and visual tokens: the indicator uses the existing pale peony palette at low opacity; the journal retains the paper, ink, cinnabar, and cloud-wash tokens.
- Image quality and asset fidelity: the indicator uses the production `casting-peony-petal-v1.png` asset. No CSS-drawn replacement, emoji, or placeholder asset is present.
- Copy and content: all P8 `model_section.markdown` paragraphs belonging to each act are retained. Deterministic chart facts, P9 source binding, and model-call count are unchanged.
- Interaction and accessibility: native mobile scrollbars are hidden; the petal tracks both document scrolling and the journal's nested scrolling. The marker is decorative and excluded from the accessibility tree. Scroll behavior and keyboard access remain intact.

**Comparison History**

1. [P2] The first implementation placed the viewport petal at y ≈ 74 px and the journal petal beside the close control, making both too easy to miss and creating competition with the header. Fix: moved their starting positions to 132 px and 126 px respectively, then increased only the asset's restrained visibility while keeping the track absent.
2. Post-fix evidence is recorded in both browser captures above. The petal sits inside the right safe area, the former white track is absent, and all four journal corners visibly follow the paper surface.

**Verification**

- Production build: passed.
- Focused frontend suites: 30/30 passed.
- Focused lint: 0 errors; existing repository warnings remain unchanged except for the expected image-asset advisory on the new decorative component.
- Browser console: no warnings or errors on P8 or the open journal state.
- Primary interactions tested: complete mobile entry through casting, direct-high completion, opening P8, reading full question-related paragraphs, P8 document scrolling with moving petal, opening the P9 journal, expanding a second record, and nested scrolling with moving petal.

**Implementation Checklist**

- [x] Remove the white native mobile scrollbar across app-owned pages.
- [x] Use the selected peony-petal scroll marker for both viewport and journal scrolling.
- [x] Give the observation book a rounded, layered paper edge.
- [x] Restore all P8 question-related paragraphs without changing deterministic casting or adding model calls.
- [x] Verify 430 × 932 layout, interactions, build, tests, and browser console.

**Follow-up Polish**

- None required for this selected direction.

final result: passed

## P7 三字卦名单行与 P8 终幕入口轻量化 — 2026-09-02

**Comparison Target**

- P7 issue reference: `C:/Users/27622/AppData/Local/Temp/codex-clipboard-5bda5c9b-52cc-4975-9504-9cbe5d354afe.png` (757 × 517 px).
- Browser-rendered P7: `outputs/p7-p8-polish-2026-09-02/p7-three-character-name-430x932.png`; visible phone content is rendered by the production `/mobile-preview` iframe at 430 × 932 CSS px.
- Same-input comparison: `outputs/p7-p8-polish-2026-09-02/p7-source-vs-single-line.png`.
- P8 browser state: the production fifth act at 430 × 932 CSS px, using the successful result `火泽睽 · 六三 → 火天大有` and the live `进入观象寄语` control. No separate P8 button reference screenshot was supplied; the target is the product's existing transparent `method-cta` ink-cue language.
- Device density reported by the in-app browser: 1.25. Layout geometry was measured in CSS pixels.

**Full-view Comparison Evidence**

- The supplied P7 screenshot and the browser-rendered P7 state were opened together in one comparison input. The source wraps `火泽睽` as one character plus two characters; the implementation keeps all three characters on one line while preserving the right alignment and the established title scale.
- The P8 control was inspected in the actual fifth-act runtime state. Its measured box is 190 × 58 CSS px at x 222.4–412.4 and y 852–910, leaving an 18 px right inset and 22 px bottom inset inside the 430 × 932 phone canvas.
- Runtime styles confirm a transparent background, no box shadow, no border, and the production `method-current-cue-v1.png` ink-stroke asset. The control remained visible at full opacity and accepted keyboard activation into P9.

**Findings**

- No actionable P0/P1/P2 mismatch remains.
- P7 title wrapping was a stable width constraint, not an intermittent rendering event. The mobile title now sizes to its content and prevents CJK line breaking; the phone frame remains the clipping boundary.
- P8 no longer presents as a filled rectangular card. It uses the existing Bagua mark, brush lettering, and restrained ink underline, with only cinnabar emphasis on hover/focus.
- The P1–P9 visual assets, deterministic casting, model call, content gate, and page-transition logic are unchanged.

**Comparison History**

1. [P2] P7 used a 52vw title box with `word-break: break-all`, forcing the three-character name into a 1+2 composition. Fix: remove the title width cap and keep the name on one line.
2. [P2] P8's final control added a translucent fill, shadow, and blur over the shared method CTA, creating the reported rectangular card. Fix: remove those surfaces and restore a production ink-cue underline.
3. Post-fix P7 comparison visibly passes; P8 runtime geometry, style tokens, and actual P8→P9 activation pass.

**Verification**

- Production build: passed.
- Focused frontend suites: 30/30 passed.
- Focused lint: 0 errors; 45 pre-existing warnings in `GuanxiangApp.tsx` remain unchanged.
- Real mobile journey: P1 → P7 completed with inputs `3 / 2 / 3`; P7 displayed `火泽睽` on one line; detailed reading completed; P8 reached the fifth act; the redesigned control opened P9 successfully.

final result: passed

## 历史定稿纠偏复核 — P1–P9

**本轮重新确定的视觉真源**

- 逐页读取 P1–P9 的历史冻结记录；汇总基线见 `docs/governance/guanxiang-mobile-p1-p9-frozen-baseline.md`。
- P2 以冻结记录指定的 A「江势为序」v11、实时冻结页面和水／山分离遮罩为准，不再使用旧静态样片或主流程近似效果。
- 同尺寸对照：`outputs/p1-p9-history-recovery-2026-09-01/p2-source-current-comparison.png`；左侧为冻结页面，右侧为修复后的主流程。

**发现与修复**

- [P1] P2 主流程此前使用了另一套无冻结遮罩的河流着色器，确属错误。已接入冻结版 `RiverFlowCanvas` 逻辑和 `method-river-motion-mask-v1.png`，恢复 v11 水／山分离。
- [P1] 窄窗口中的 `/mobile-preview` 仍保留外层说明和最小宽度，导致 430×932 手机画面被横向截断。窄窗口现在直接显示完整手机实屏；桌面宽窗口仍保留手机边框。
- [P2] P2 题字激活态被通用样式放大到另一组参数。已恢复冻结值 `translateX(-13px) scale(1.28)`、非激活透明度 `.72` 和冻结书写节奏。
- [P2] P4 鹤群仍沿用 270／282 秒桌面路线。已恢复冻结版 48／56 秒移动路线、8 秒错峰和互斥转身可见性。
- P1、P3、P5、P6、P7、P8、P9 的冻结资产、构图签名和关键参数复核通过；P3 松树保持 6.8 秒冻结轻摆，P8 保持 79svh 纸幕，P9 保持冻结结尾组件。

**验证**

- P2 冻结原件与当前实现均为 430×932，并在同一比较图中完成核验。
- P2 冻结遮罩 SHA-256：`CDC9B9CD34E917E1B363CD7450F1A035F3F4F87F2D4290FAD48C6B7760695B7B`，与冻结记录一致。
- 生产构建通过。
- 定稿接入回归测试新增 P1–P9 全页锁定项；`rendered-html.test.mjs` 24/24 通过。
- 前端总套件中 43/46 通过；另外 3 项只因当前环境缺少 `lunar_python`，Python fixture 未启动，与本轮视觉修改无关。
- 聚焦 ESLint：0 error，0 warning；主文件仍有既存 warning，本轮没有新增 error。

final result: passed

## P7 长文案越界与详细解卦重试恢复 — 2026-09-02

**Audit Scope**

- Target: 430 × 932 mobile P7 result screen, including the initial result, timeout/failure state, manual retry, and escape actions.
- User goal: keep all P7 copy inside the phone frame and recover from a failed detailed-reading request without becoming trapped.
- Reference screenshot: `C:/Users/27622/AppData/Local/Temp/codex-clipboard-a88a8814-4945-4488-a003-c3cd31169713.png`.

**Captured Steps**

1. Current failed state: `outputs/p7-timeout-audit-2026-09-02/01-current-failed-state.png`. Health: failed. The long retry label and large hexagram title were aligned flush with the 430 px viewport edge and visibly clipped by the phone frame.
2. Contained recovery state: `outputs/p7-timeout-audit-2026-09-02/02-p7-contained-actions.png`. Health: passed. The title, long retry label, error copy, “返回修改原问”, and “重新开始” stay inside the mobile safe area.
3. Real manual retry: `outputs/p7-timeout-audit-2026-09-02/03-retry-returned-with-recovery-actions.png`. Health: recoverable. The click progressed from P7 failure into a real RUNNING task rather than immediately returning “解卦响应异常”; the generated content was later rejected by the existing content-quality gate and the UI returned with all three recovery paths available.

**Root Causes And Fixes**

- Stable layout issue, not an intermittent event: the retry label and 86 px title were allowed to outgrow the 44.18vw summary column. The mobile column now reserves 52vw, caps children to the column, reduces the title overhang, and keeps a 61 px measured right-side safety margin at 430 px.
- Stable retry orchestration issue, not a click failure: a consumed one-shot conditional-intake id was being submitted again. A manual retry now creates a fresh intake transaction, reuses the user's prior clarification when one exists, and then submits the same confirmed question and the same three numbers.
- Dead-end recovery: failed P7 now always exposes “返回修改原问” and “重新开始” alongside manual regeneration.
- Startup console issue: the decorative scroll marker now observes a guaranteed DOM root instead of sometimes passing a null body to `MutationObserver`.

**Verification**

- Focused frontend suites: 30/30 passed.
- Focused lint: 0 errors; existing warnings remain.
- Production build: passed.
- Fresh mobile-preview console: no warnings or errors.
- Real retry state: reached RUNNING with “详细解卦生成中”; no immediate consumed-intake failure.
- Content-quality gate remains intact; rejected model output is not allowed to enter P8 or P9.

final result: passed

## P7 三字／四字卦名与详细解卦稳定锚定 — 2026-09-02

**Comparison Target**

- Issue reference: `C:/Users/27622/AppData/Local/Temp/codex-clipboard-025d47a9-2ee1-456e-b9cc-ea0ba5a6392a.png` (637 × 516 px), showing `天雷无妄` forced into one clipped line and an incomplete detailed-reading label.
- Browser-rendered implementation: `outputs/p7-name-layout-stability-2026-09-02/p7-four-character-2x2-fullpage.png` (1264 × 1152 px outer capture), containing the production 430 × 932 CSS px phone screen.
- Final phone crops supplied for review: `outputs/p7-name-layout-stability-2026-09-02/p7-three-character-final-phone.png` and `outputs/p7-name-layout-stability-2026-09-02/p7-four-character-final-phone.png`.
- Same-input four-character comparison: `outputs/p7-name-layout-stability-2026-09-02/p7-four-name-source-vs-fixed.png` (1020 × 590 px).
- Same-input three-character comparison retained from the preceding pass: `outputs/p7-p8-polish-2026-09-02/p7-source-vs-single-line.png`.
- Runtime viewport: 430 × 932 CSS px inside the phone iframe; browser device density 1.25. Outer wrapper scaling was excluded from layout measurements.
- Verified four-character state: `第 25 卦 · 天雷无妄`; detailed-reading states inspected: `详细解卦生成中` and `再次生成详细解卦`.

**Full-view and Focused Comparison Evidence**

- The supplied issue screenshot and the post-fix four-character P7 crop were opened together in one comparison input. The implementation now renders `天雷 / 无妄` as a balanced 2＋2 block; every glyph stays inside the 25 px right safe area.
- The earlier three-character source/implementation comparison was reopened in the same visual input. `火泽睽` remains a single line.
- Live geometry for the four-character title: x 230.2–404.6 px, y 600–770 px, width 174.4 px; computed wrapping is enabled only at name length four.
- Live geometry for the longest recovery label: x 237.4–404.6 px, y 782–826.4 px, width 167.2 px. The title row is fixed at 180 px and the action starts after a fixed 12 px gap, so the label no longer moves with title line count or generation phase.

**Findings**

- No actionable P0/P1/P2 mismatch remains.
- Fonts and typography: three-character names preserve the approved single-line brush composition; four-character names use a fixed 2＋2 brush composition with unchanged font family and scale.
- Spacing and layout rhythm: the result number, reserved title row, and detailed-reading action now occupy explicit grid rows. The action's right edge is fixed at 404.6 px for loading, success, and retry copy.
- Colors and tokens: paper, ink, cinnabar label, and underline are unchanged.
- Image quality: koi, hexagram brush strokes, and paper imagery are unchanged production assets.
- Copy and content: all four name characters and the complete loading/retry labels are visible; deterministic casting and generated reading content are unchanged.

**Comparison History**

1. [P1] The prior universal `white-space: nowrap` rule fixed three-character names but forced four-character names beyond the frame. Fix: expose the Unicode character count and apply the two-column wrap only when the name contains four characters.
2. [P2] The detailed-reading action still flowed directly after the variable-height title, allowing its vertical position and clipping behavior to change. Fix: reserve a 180 px title row and give every action state the same content-sized, no-wrap row and 12 px gap.
3. [P2] The three-character max-content title could expand the implicit grid column about 2 px beyond the phone edge even though the text remained on one line. Fix: lock the result grid column to 100%, so both the name and every detailed-reading label share the same 404.6 px right anchor.
4. Post-fix visual and runtime evidence shows the three-character title, four-character title, longest action label, and right safe area all passing at 430 × 932.

**Verification**

- Focused frontend suites: 30/30 passed.
- Production build: passed.
- Browser console: no warnings or errors during the four-character P7 run.
- Local preview remains available at `/mobile-preview`.

final result: passed
