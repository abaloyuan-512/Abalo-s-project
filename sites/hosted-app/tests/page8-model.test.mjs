import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("page eight renders the approved five-scene visual order without changing model order", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  assert.match(source, /type Page8SceneId = "BASE_HEXAGRAM" \| "MUTUAL_HEXAGRAM" \| "CHANGED_HEXAGRAM" \| "MOVING_LINE" \| "BODY_USE_STRENGTH"/);
  assert.match(source, /const PAGE8_VISUAL_ORDER: Page8SceneId\[\] = \[\s*"BASE_HEXAGRAM",\s*"MUTUAL_HEXAGRAM",\s*"MOVING_LINE",\s*"CHANGED_HEXAGRAM",\s*"BODY_USE_STRENGTH",\s*\]/);
  assert.match(source, /function Page8KunStory/);
  assert.match(source, /reading\.scenes\.find\(\(scene\) => scene\.scene_id === sceneId\)/);
  assert.match(source, /page8-ben-gua-background-v6\.png/);
  assert.match(source, /page8-hu-gua-background-v6\.png/);
  assert.match(source, /page8-dong-yao-background-v6\.png/);
  assert.match(source, /page8-bian-gua-background-v6\.png/);
  assert.match(source, /page8-wang-shuai-background-v6\.png/);
});


test("page eight is a sticky five-screen scroll story with persistent environmental motion", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(source, /className="page8-kun-stage"/);
  assert.match(source, /className="page8-kun-mist"/);
  assert.match(source, /className="page8-kun-breath"/);
  assert.match(source, /className="page8-kun-progress"/);
  assert.doesNotMatch(source, /<span>鲲游五境<\/span>/);
  assert.doesNotMatch(source, /page8-kun-kicker|page8-kun-motif/);
  assert.doesNotMatch(source, /page8-kun-scroll-cue/);
  assert.doesNotMatch(source, /向下观象/);
  assert.doesNotMatch(css, /\.page8-kun-kicker|\.page8-kun-motif|\.page8-kun-scroll-cue/);
  assert.doesNotMatch(css, /\.page8-kun-reading \{[^}]*border-top:/);
  assert.doesNotMatch(css, /\.page8-kun-interpretation \{[^}]*border-top:/);
  assert.doesNotMatch(css, /\.page8-kun-notes \{[^}]*border-top:/);
  assert.match(source, /progress \* orderedScenes\.length - \.5/);
  assert.match(css, /\.page8-kun-story \{[\s\S]*?height: calc\(\(var\(--page8-scene-count\) \+ 1\) \* 100svh\);/);
  assert.match(css, /\.page8-kun-stage \{[\s\S]*?position: sticky;[\s\S]*?height: 100svh;[\s\S]*?overflow: hidden;/);
  assert.match(css, /@keyframes page8-mist-breathe/);
  assert.match(css, /@keyframes page8-kun-breathe/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.page8-kun-mist/);
});


test("page eight adds one continuous photon river and source-based brush oracle marks", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(source, /function Page8PhotonRiver\(\)/);
  assert.match(source, /const PAGE8_PHOTON_COUNT = 1500;/);
  assert.equal((source.match(/<Page8PhotonRiver \/>/g) ?? []).length, 1);
  assert.match(source, /className="page8-photon-river"/);
  assert.match(source, /getContext\("2d", \{ alpha: true \}\)/);
  assert.match(source, /globalCompositeOperation = "lighter"/);
  assert.match(source, /window\.requestAnimationFrame\(animate\)/);
  assert.match(source, /new ResizeObserver/);
  assert.match(source, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(source, /page8-kun-shared-trail-v1\.png|page8-kun-shared-flow|Page8GoldSilkBundle|page8-gold-silk|page8-white-cloud/);
  assert.match(css, /\.page8-photon-river \{[\s\S]*?opacity: \.9;/);
  assert.match(css, /@media \(max-width: 760px\)[\s\S]*?\.page8-photon-river \{ opacity: \.78; \}/);
  assert.doesNotMatch(css, /page8-kun-shared-flow|page8-flow-band|page8-gold-silk|page8-metal-glint|page8-white-cloud/);
  assert.match(source, /function Page8OracleMark/);
  assert.match(source, /page7-yao-brush-v1\.png/);
  assert.match(source, /page7-yao-brush-short-v1\.png/);
  assert.match(source, /is-full-hexagram/);
  assert.match(source, /is-moving-line is-variant-a/);
  assert.match(source, /is-moving-line is-variant-b/);
  assert.match(source, /is-body-use is-variant-/);
  assert.match(source, /const \[movingVariant, setMovingVariant\] = useState<Page8ReviewVariant>\("A"\)/);
  assert.match(source, /const \[strengthVariant, setStrengthVariant\] = useState<Page8ReviewVariant>\("B"\)/);
  assert.match(source, /className=\{`page8-oracle-zone \$\{className\}\$\{isEngaged \? " is-oracle-engaged" : ""\}`\}/);
  assert.match(source, /className="page8-oracle-hit-area"/);
  assert.match(source, /className="page8-oracle-moving-body"/);
  assert.match(source, /--page8-oracle-shift-x/);
  assert.match(source, /--page8-oracle-shift-y/);
  assert.doesNotMatch(source, /page8-oracle-focus-layer|focusMode/);
  assert.match(css, /\.page8-oracle-mark\.is-full-hexagram \{[\s\S]*?--page8-oracle-rest-opacity: \.1;[\s\S]*?--page8-oracle-focus-opacity: \.58;/);
  assert.match(css, /\.page8-oracle-mark\.is-oracle-focused \.page8-oracle-moving-body \{[\s\S]*?translate3d\(var\(--page8-oracle-shift-x, 0\), var\(--page8-oracle-shift-y, 0\), 0\) scale\(2\);/);
  assert.match(css, /\.page8-oracle-mark\.is-oracle-returning \.page8-oracle-moving-body \{[\s\S]*?translate3d\(0, 0, 0\) scale\(1\);/);
  assert.match(css, /\.page8-oracle-mark\.is-moving-line\.is-variant-a \.page8-brush-line\.is-active-line \{[\s\S]*?transform: none;/);
  assert.doesNotMatch(css, /page8-oracle-focus-layer|is-focus-oracle/);
  assert.match(css, /\.page8-oracle-mark\.is-body-use\.is-variant-b \.page8-trigram-mark \{[\s\S]*?left: 50%;[\s\S]*?transform: translateX\(-50%\);/);
  assert.match(css, /@media \(max-width: 760px\)[\s\S]*?\.page8-oracle-mark\.is-body-use\.is-variant-b \.page8-trigram-mark \{[\s\S]*?top: 50%;[\s\S]*?transform: translateY\(-50%\);/);
});


test("page eight opens from page seven and keeps all later reserved sections hidden", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(source, /className="future-result-sections" hidden aria-hidden="true"/);
  assert.match(source, /response\.page8_reading \? <Page8KunStory/);
  assert.match(source, /className="result-detail-button"[\s\S]*?onClick=\{openDetailedReading\}/);
  assert.doesNotMatch(source, /className="result-detail-button"[^>]+disabled/);
  assert.match(source, /className="result-overview scroll-section viewport-page" data-reveal hidden=\{readingStarted\}/);
  assert.match(source, /document\.getElementById\("result-reading"\)\?\.scrollIntoView/);
  assert.match(source, /id="page8-model-review" className="page8-kun-story is-incomplete"/);
  assert.match(source, /page8Pending \? "详细解卦正在生成，完成后将在这里自动展开。"/);
  assert.match(source, /setResponse\(\(current\) => current\?\.page8_reading \? current : payload\)/);
  assert.match(source, /page8ScrollIsOpen/);
  assert.match(source, /root\.classList\.add\("page8-reading-open"\)/);
  assert.match(source, /root\.classList\.remove\("page8-reading-open"\)/);
  assert.match(css, /\.page8-reading-open \.flow-shell \{ height: auto; min-height: 100svh; overflow: visible; \}/);
  assert.match(source, /五境阅毕 · 第九页尚未开启/);
});
