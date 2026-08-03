import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("page eight review is a five-scene forward-only data experience", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  assert.match(source, /type Page8SceneId = "BASE_HEXAGRAM" \| "MUTUAL_HEXAGRAM" \| "CHANGED_HEXAGRAM" \| "MOVING_LINE" \| "BODY_USE_STRENGTH"/);
  assert.match(source, /function Page8ModelReview/);
  assert.match(source, /const \[activeIndex, setActiveIndex\] = useState\(0\)/);
  assert.match(source, /Math\.min\(index \+ 1, reading\.scenes\.length - 1\)/);
  assert.doesNotMatch(source, /setActiveIndex\(\(index\) => index - 1\)/);
  assert.match(source, /卦象依据/);
  assert.match(source, /结合所问/);
  assert.match(source, /仍不能据此断定/);
  assert.match(source, /五幕数据已经展示完毕。此处停止，不进入第九页，也不展示行动建议。/);
});


test("page eight model review stays one viewport and keeps later sections hidden", async () => {
  const source = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(source, /className="future-result-sections" hidden aria-hidden="true"/);
  assert.match(source, /response\.page8_reading \? <Page8ModelReview/);
  assert.match(css, /\.page8-model-review \{[^}]+height: 100svh;[^}]+overflow: hidden;/);
  assert.match(css, /@media \(max-width: 760px\)[\s\S]+\.page8-model-review \{[^}]+min-height: 100svh;/);
});
