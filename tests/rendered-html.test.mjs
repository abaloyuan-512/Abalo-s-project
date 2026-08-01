import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";

async function worker() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  return (await import(workerUrl.href)).default;
}

const env = {
  ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
};
const context = { waitUntil() {}, passThroughOnException() {} };

test("server-renders the Guanxiang product", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), env, context);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<title>观象 · 寂然不动，感而遂通天下之故<\/title>/);
  assert.match(html, /寂然不动，感而遂通天下之故/);
  assert.match(html, /心有所问 静观其象/);
  assert.match(html, /hero-entry-wide-v6\.webp/);
  assert.match(html, /hero-entry-square-v6\.webp/);
  assert.match(html, /hero-entry-mobile-v6\.webp/);
  assert.match(html, /entry-hero-final/);
  assert.match(html, /hero-entry-mist-wide-v2\.webp/);
  assert.match(html, /hero-entry-mist-square-v2\.webp/);
  assert.match(html, /hero-entry-mist-mobile-v2\.webp/);
  assert.doesNotMatch(html, /entry-(?:ink-drop|ripple|taiji)/);
  assert.match(html, /entry-bird-flock/);
  assert.match(html, /hero-boat-v1\.png/);
  assert.doesNotMatch(html, /entry-waterfall/);
  assert.match(html, /hero-title-hotspot/);
  assert.match(html, /<button[^>]+class="hero-scroll-cue"/);
  assert.doesNotMatch(html, /<a[^>]+class="hero-scroll-cue"/);
  assert.match(html, /在天成象/);
  assert.match(html, /在地成形/);
  assert.match(html, /变化见矣/);
  assert.doesNotMatch(html, /在天成象，|在地成形，|变化见矣。/);
  assert.doesNotMatch(html, /遇事不决，可问春风/);
  assert.match(html, /开始正问/);
  assert.match(html, /<button[^>]+id="method-ready"[^>]+aria-pressed="false"/);
  assert.match(html, /method-cta-label/);
  assert.doesNotMatch(html, /method-cta-mini-seal/);
  assert.doesNotMatch(html, /<a[^>]+class="method-cta"/);
  assert.match(html, /href="#method"/);
  assert.match(html, /接下来/);
  assert.match(html, /我们尝试观象/);
  assert.match(html, /请闭上眼睛/);
  assert.match(html, /做三个呼吸/);
  assert.doesNotMatch(html, /一步一步看清心中的疑惑|慢慢做三个呼吸|三个呼吸之后，我们进入「正问」/);
  assert.doesNotMatch(html, /观象不会替你决定，也不会预先写好结果/);
  assert.doesNotMatch(html, /程序依规则完成排盘/);
  assert.doesNotMatch(html, /aria-label="观象四步"/);
  assert.match(html, /\/fuxi-bagua-taiji\.svg/);
  assert.match(html, /question-pine-cloud-base-v2\.webp/);
  assert.match(html, /question-mountain-occluder-v3\.png/);
  assert.match(html, /question-pine-tree-v2\.png/);
  assert.match(html, /inquiry-cloud-stream-far/);
  assert.match(html, /inquiry-cloud-stream-near/);
  assert.match(html, /你真正想问的问题/);
  assert.doesNotMatch(html, /写下一件<br\/>真实具体的事/);
  assert.match(html, /把心里的这一问，写在这里/);
  assert.match(html, /下一步，我们会陪你慢慢辨清事实、未知与真正的需要/);
  assert.match(html, /确定性排盘 · 个性化解读/);
  assert.doesNotMatch(html, /约三分钟/);
  assert.doesNotMatch(html, /第二阶段 · 明法/);
  assert.match(html, /观象之法 · 壹/);
  assert.match(html, /这段关系一直没有进展，我还要继续主动吗/);
  assert.match(html, /<h2[^>]+id="inquiry-title"[^>]*>正问<\/h2>/);
  assert.match(html, /<div[^>]+class="inquiry-future-flow"[^>]+hidden/);
  assert.match(html, /写好了，继续辨识/);
  assert.match(html, /观象之法 · 贰/);
  assert.match(html, /<h3>辨识<\/h3>/);
  assert.match(html, /为了能结合卦象，给你更具实际意义的建议，我还有几个问题请你回答/);
  assert.match(html, /<section[^>]+id="final-question"[^>]+hidden/);
  assert.match(html, /id="final-question-title"[^>]*>定问<\/h3>/);
  assert.match(html, /请心中再次默念你的问题，深呼吸/);
  assert.match(html, /开始卜卦/);
  assert.doesNotMatch(html, /最终问卦题目/);
  assert.match(html, /<section[^>]+class="inquiry-step inquiry-panel number-step casting-number-step"[^>]+hidden/);
  assert.doesNotMatch(html, /class="inquiry-step inquiry-panel cast-step"/);
  assert.match(html, /<h3[^>]+id="casting-title"[^>]*>成卦<\/h3>/);
  assert.match(html, /casting-peony-bloom-1-v1\.png/);
  assert.match(html, /casting-peony-bloom-2-v1\.png/);
  assert.match(html, /casting-peony-bloom-3-v1\.png/);
  assert.match(html, /casting-peony-petal-v1\.png/);
  assert.match(html, /心中再默念一遍所问之事/);
  assert.match(html, /三息之间，收束心念/);
  assert.match(html, /取1-999之间的数字，填入上方文字右侧/);
  assert.doesNotMatch(html, /casting-peony-wind-v1\.png/);
  assert.match(html, /凭当下所感，取三个数/);
  assert.match(html, /<button[^>]+class="cast-button"[^>]+disabled[^>]*>[\s\S]*观卦<\/button>/);
  assert.doesNotMatch(html, /闭上眼睛，缓缓呼吸三次/);
  assert.match(html, /观事簿/);
  assert.doesNotMatch(html, /何为观象|冻结规则|当前不收费|当前为视觉验收版|PRIVATE PREVIEW/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("renders public method, privacy and usage pages", async () => {
  const app = await worker();
  for (const [path, expected] of [["/about", /MEIHUA_RULE_SPEC_V1/], ["/privacy", /只有当你主动点击/], ["/guide", /一次观象通常需要一至三分钟/]]) {
    const response = await app.fetch(new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }), env, context);
    assert.equal(response.status, 200);
    assert.match(await response.text(), expected);
  }
});

test("does not ship a separate preview product page", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/preview", { headers: { accept: "text/html" } }), env, context);
  assert.equal(response.status, 404);
});

test("journal rejects requests without a private device key", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/journal"), env, context);
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { error: "无法识别这本观事簿。" });
});

test("API fails safely until the Python engine is configured", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/v2/meihua", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_version: "SITES_MEIHUA_API_CONTRACT_V2" }),
  }), env, context);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { error: "排盘服务尚未连接，请稍后再试。" });
});

test("V3 API fails safely until the Python engine is configured", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/v3/meihua", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_version: "SITES_MEIHUA_API_CONTRACT_V3" }),
  }), env, context);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { error: "排盘服务尚未连接，请稍后再试。" });
});

test("formal personalized API fails safely until the Python engine is configured", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/v4/meihua", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1" }),
  }), env, context);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { error: "个性化解读服务尚未开放。" });
});

test("method lines retain the replayable writing interaction", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /methodWritingRun/);
  assert.match(appSource, /method-writing-layer/);
  assert.match(appSource, /onPointerLeave=.*setPreviewMethodLine\(null\)/);
  assert.match(cssSource, /method-ink-line\.is-writing[^}]+scale\(2\)/s);
  assert.match(cssSource, /method-ink-line:focus-visible:not\(\.is-writing\)[^}]+font-weight: 700[^}]+scale\(1\.34\)/s);
  assert.match(cssSource, /prefers-reduced-motion:[^}]+reduce[\s\S]+method-writing-layer i/);
});

test("question scene keeps cloud and pine motion accessible", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /function InquiryInkScene/);
  assert.match(cssSource, /question-cloud-stream-v3-tile\.png/);
  assert.match(cssSource, /@keyframes inquiry-cloud-stream-far/);
  assert.match(cssSource, /@keyframes inquiry-cloud-stream-near/);
  assert.match(cssSource, /--cloud-cycle: 100vw/);
  assert.match(cssSource, /background-position: calc\(0px - var\(--cloud-cycle\)\)/);
  assert.match(cssSource, /100%[^}]+background-position: 0/s);
  assert.match(cssSource, /@keyframes inquiry-pine-breeze/);
  assert.match(cssSource, /prefers-reduced-motion:[^}]+reduce[\s\S]+inquiry-cloud-stream, \.inquiry-pine-tree[^}]+animation: none/s);
});

test("discernment mirrors the primary-question hierarchy and shows only the current turn", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /className="inquiry-step inquiry-panel discernment-step"/);
  assert.match(appSource, /className="eyebrow">观象之法 · 贰/);
  assert.doesNotMatch(appSource, /<div className="step-heading"><span>贰<\/span>/);
  assert.doesNotMatch(appSource, /className="dialogue-history"/);
  assert.match(appSource, /const previousAnswer = answers\[answers\.length - 1\]/);
  assert.match(appSource, /const previousTurn = turns\[turns\.length - 1\]/);
  assert.match(appSource, /className="discernment-echo"/);
  assert.match(appSource, /className="discernment-current"/);
  assert.match(appSource, /key=\{`local-echo-\$\{answers\.length\}`\}/);
  assert.match(appSource, /key=\{`local-prompt-\$\{turn\}`\}/);
  assert.match(appSource, /discernment-current[^\n]+fuxi-bagua-taiji\.svg/);
  assert.doesNotMatch(appSource, /discernment-current[^\n]+bagua-seal\.png/);
  assert.match(appSource, /跳过这一问/);
  assert.match(appSource, /已经说清，提前结束/);
  assert.match(appSource, /信息足够即结束 · 最多 8 问/);
  assert.match(appSource, /type DiscernmentCompletionReason = "ENOUGH" \| "MAX_TURNS" \| "USER_EARLY"/);
  assert.match(appSource, /nextTurns\.length >= 8[\s\S]+setReview\(payload\); setReviewReason\("MAX_TURNS"\); setCurrentPrompt\(""\); setMode\("REVIEW"\)/);
  assert.match(appSource, /onCompletionReason\("USER_EARLY"\)/);
  assert.match(appSource, /《周易·系辞下》/);
  assert.match(appSource, /穷则变，变则通，通则久/);
  assert.doesNotMatch(appSource, /你选择了提前结束，或已经达到本次最多八问|不必为了问完而继续回答|AI 改写建议/);
  assert.match(appSource, /FIRST_DISCERNMENT_QUESTION = "这件事现在具体走到了哪一步？"/);
  assert.match(appSource, /前 \{turns\.length\} 个回答都还在/);
  assert.match(appSource, /onClick=\{retryTurn\}>继续这一轮/);
  assert.match(appSource, /className="discernment-mist-scroll"/);
  assert.match(appSource, /discernment-mist-scroll-v1\.png/);
  assert.doesNotMatch(appSource, /开始 AI 辨识|重新连接 AI 辨识|正在静心听你所问/);
  assert.match(cssSource, /discernment-step[^}]+min-height: 100svh[^}]+grid-template-columns/s);
  assert.match(cssSource, /discernment-heading h3[^}]+clamp\(88px, 8\.3vw, 132px\)/);
  assert.match(cssSource, /discernment-current img[^}]+object-fit: contain/);
  assert.match(cssSource, /discernment-echo[^}]+discernment-echo-away/);
  assert.match(cssSource, /discernment-mist-scroll img[^}]+discernment-mist-pass/);
  assert.doesNotMatch(cssSource, /discernment-working-line/);
  assert.match(cssSource, /prefers-reduced-motion:[^}]+reduce[\s\S]+discernment-echo/);
});

test("final question offers a concise user-controlled question decision", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  await fs.access(new URL("../public/final-question-sunset-reeds-v1.webp", import.meta.url));
  assert.match(appSource, /通过跟你的沟通，我建议你在卜卦之前，把问题更换为/);
  assert.match(appSource, /采取建议/);
  assert.match(appSource, /保持原题/);
  assert.match(appSource, /\{decisionMade \? "那现在" : "现在"\}已经更清晰你的现状，我们准备开始取数卜卦了/);
  assert.match(appSource, /我感受到你想尽快进入取数卜卦的环节，现在请心中再次默念你的问题，深呼吸/);
  assert.match(appSource, /请心中再次默念你的问题，深呼吸/);
  assert.match(appSource, /开始卜卦/);
  assert.doesNotMatch(appSource, /最终问卦题目|final-question-input|question-compare/);
  assert.match(appSource, /onSuggestion\(\{ question: review\.suggested_question, reason: review\.question_change_reason \}\)/);
  assert.match(appSource, /<FinalQuestion hidden=\{!intakeComplete\}/);
  assert.match(appSource, /number-step casting-number-step" hidden=\{!finalQuestionConfirmed\}/);
  assert.match(appSource, /className="final-question-sky-drift"/);
  assert.match(appSource, /className="final-question-bird"/);
  assert.match(appSource, /理清脉络之后<br \/>确认最终问题/);
  assert.match(appSource, /<BaguaMark className="final-question-bagua" \/><span className="method-cta-label">/);
  assert.match(cssSource, /final-question-step[^}]+min-height: 100svh/);
  assert.match(cssSource, /final-question-backdrop[^}]+final-question-sunset-reeds-v2\.png/);
  assert.match(cssSource, /final-question-backdrop[^}]+left: calc\(50% - 30px\)[^}]+width: calc\(100vw \+ 4px\)/);
  assert.match(cssSource, /final-question-backdrop::before[^}]+background-position: calc\(50% - 38px\) center/);
  assert.match(cssSource, /final-question-backdrop::after[^}]+background-position: calc\(50% \+ 44px\) center/);
  assert.match(cssSource, /final-question-backdrop::before[^}]+final-question-reed-sway-near/);
  assert.match(cssSource, /final-question-backdrop::after[^}]+final-question-reed-sway-mid/);
  assert.match(cssSource, /@keyframes final-question-reed-sway-near/);
  assert.match(cssSource, /final-question-sky-drift::before[^}]+final-question-sky-flow/);
  assert.match(cssSource, /@keyframes final-question-sky-flow/);
  assert.match(cssSource, /@keyframes final-question-sky-flow-soft/);
  assert.match(cssSource, /final-question-bird[^}]+final-question-bird-sprite-v1\.png/);
  assert.match(cssSource, /@keyframes final-question-bird-flap/);
  assert.match(cssSource, /final-question-cta::after[^}]+content: none/);
  assert.match(cssSource, /final-question-ready[^}]+border: 0/);
  assert.match(cssSource, /prefers-reduced-motion:[^}]+reduce[\s\S]+final-question-backdrop::before[^}]+animation: none/);
  assert.match(cssSource, /final-question-cta/);
});

test("casting uses a borderless windblown peony scene without changing number roles", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  const petalMotionSource = appSource.match(/const PEONY_PETAL_MOTIONS = \[([\s\S]*?)\] as const;/)?.[1] ?? "";
  assert.match(appSource, /className="eyebrow">观象之法 · 肆/);
  assert.match(appSource, /id="casting-title"[^>]*>成卦/);
  assert.match(appSource, /PEONY_BREATHS\.map/);
  assert.match(appSource, /casting-peony-petal-v1\.png/);
  assert.equal((petalMotionSource.match(/\{ left:/g) ?? []).length, 18);
  assert.match(petalMotionSource, /size: 10/);
  assert.match(petalMotionSource, /size: 108/);
  assert.match(petalMotionSource, /duration: 8\.5/);
  assert.match(petalMotionSource, /duration: 23\.2/);
  assert.match(appSource, /心中再默念一遍所问之事/);
  assert.match(appSource, /三息之间，收束心念/);
  assert.match(appSource, /取1-999之间的数字，填入上方文字右侧/);
  assert.doesNotMatch(appSource, /placeholder="1—999"/);
  assert.match(appSource, /aria-describedby="casting-range-note"/);
  assert.doesNotMatch(appSource, /casting-peony-wind-v1\.png/);
  assert.match(appSource, /peony-number-field[\s\S]+casting-range-note[\s\S]+casting-submit[\s\S]+className="cast-button"/);
  assert.doesNotMatch(appSource, /className="inquiry-step inquiry-panel cast-step"/);
  assert.match(appSource, /peony-bloom-image[\s\S]+peony-petal-layer[\s\S]+peony-petal-origin[\s\S]+peony-falling-petal/);
  assert.match(appSource, /凭当下所感，取三个数/);
  assert.match(appSource, /guidance: "上卦取数"/);
  assert.match(appSource, /guidance: "下卦取数"/);
  assert.match(appSource, /guidance: "动爻取数"/);
  assert.doesNotMatch(appSource, /闭上眼睛，缓缓呼吸三次，在心中再默念一遍确认后的问题/);
  assert.doesNotMatch(appSource, /第一数定上卦，第二数定下卦，第三数定动爻/);
  assert.doesNotMatch(appSource, /三个数字只交给程序/);
  assert.doesNotMatch(appSource, /className="breath-ritual"/);
  assert.match(cssSource, /casting-peony-backdrop[^}]+casting-peony-background-v3\.webp/);
  assert.match(cssSource, /casting-heading h3[^}]+font-family: var\(--brush\)/);
  assert.match(cssSource, /casting-number-step[^}]+overflow: visible/);
  assert.match(cssSource, /casting-number-step::before[^}]+z-index: -3[^}]+background: #f1ede5/);
  assert.match(cssSource, /casting-peony-scene[^}]+width: 100vw[^}]+aspect-ratio: 16 \/ 9/);
  assert.doesNotMatch(cssSource, /peony-bloom-image[^}]+animation:/);
  assert.match(cssSource, /peony-falling-petal[^}]+peony-petal-fall var\(--petal-duration\) linear/);
  assert.match(cssSource, /peony-number \{[^}]+grid-template-columns:[^}]+align-items: center/);
  assert.match(cssSource, /peony-petal-layer \{[^}]+z-index: 2/);
  assert.match(cssSource, /peony-bloom \{[^}]+z-index: 1/);
  assert.match(cssSource, /casting-heading \.peony-number-field[^}]+grid-template-columns: repeat\(3/);
  assert.match(cssSource, /casting-contemplation span:nth-child\(2\)[^}]+margin-left: 0/);
  assert.match(cssSource, /peony-number-copy[^}]+justify-items: start[^}]+text-align: left/);
  assert.match(cssSource, /casting-submit \.cast-button[^}]+margin: 10px auto 0 0[^}]+justify-content: flex-start/);
  assert.match(cssSource, /casting-submit \.cast-button::after[^}]+content: none/);
  assert.match(cssSource, /@media \(max-width: 760px\)[\s\S]+\.casting-heading \{[^}]+display: block/);
  assert.doesNotMatch(cssSource, /peony-number-wind/);
  assert.match(cssSource, /peony-falling-petal[^}]+mix-blend-mode: normal/);
  assert.match(cssSource, /@keyframes peony-petal-fall[\s\S]+rotateX\([^)]+\)[\s\S]+rotateY\([^)]+\)/);
  assert.match(cssSource, /@keyframes peony-petal-fall[\s\S]+0% \{ opacity: 1;/);
  assert.match(cssSource, /@keyframes peony-petal-fall[\s\S]+24% \{ opacity: 1;/);
  assert.match(cssSource, /@keyframes peony-petal-fall[\s\S]+47% \{ opacity: 1;/);
  assert.doesNotMatch(cssSource, /casting-contemplation span:nth-child\(1\)[^{]*\{[^}]*border-bottom/);
  assert.match(cssSource, /prefers-reduced-motion:[^}]+reduce[\s\S]+peony-falling-petal[^}]+display: none/);
  assert.doesNotMatch(cssSource, /discernment-step::before[^}]+content:/);
  assert.doesNotMatch(cssSource, /final-question-step::before[^}]+content:/);
});

test("sixth page submits directly and seventh page gates detailed reading", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /const numbersReady = numbers\.every/);
  assert.match(appSource, /disabled=\{loading \|\| !numbersReady \|\| !acknowledged\}/);
  assert.match(appSource, /const \[readingStarted, setReadingStarted\] = useState\(false\)/);
  assert.match(appSource, /className="eyebrow">观象之法 · 肆/);
  assert.match(appSource, /className="result-canonical"><b>卦辞<\/b>/);
  assert.doesNotMatch(appSource, /className="result-question"/);
  assert.match(appSource, /aria-controls="result-reading" aria-expanded=\{readingStarted\}/);
  assert.match(appSource, />详细解卦<\/button>/);
  assert.match(appSource, /id="result-reading" hidden=\{!readingStarted\}/);
  assert.match(appSource, /window\.matchMedia\("\(prefers-reduced-motion: reduce\)"\)/);
  assert.match(cssSource, /result-overview[^}]+min-height: 100svh/);
  assert.match(cssSource, /result-aside button:focus-visible/);
});

test("AI guided intake fails safely until the Python engine is configured", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contract_version: "SITES_GUIDED_INTAKE_CONTRACT_V1",
      session_id: "intake-test-001",
      question_text: "这次合作，我还应该继续投入吗？",
      turns: [],
      locale: "zh-CN",
    }),
  }), env, context);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { error: "辨识服务暂时未连接。" });
});

test("AI guided intake accepts later CJK turns within the engine transcript limit", async () => {
  const app = await worker();
  const response = await app.fetch(new Request("http://localhost/api/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contract_version: "SITES_GUIDED_INTAKE_CONTRACT_V1",
      session_id: "intake-cjk-size-001",
      question_text: "这次合作，我还应该继续投入吗？",
      turns: Array.from({ length: 5 }, (_, index) => ({
        question: `这是第${index + 1}个需要辨清的问题？`,
        answer: "现实".repeat(600),
      })),
      locale: "zh-CN",
    }),
  }), env, context);
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: "辨识服务暂时未连接。" });
});

function createBudgetDb() {
  let row = null;
  const requests = new Map();
  const rateLimitRequests = new Map();
  return {
    get row() { return row; },
    prepare(sql) {
      let values = [];
      return {
        bind(...next) { values = next; return this; },
        async run() {
          if (sql.includes("CREATE TABLE IF NOT EXISTS owner_preview_budget") || sql.includes("CREATE TABLE IF NOT EXISTS owner_preview_requests") || sql.includes("CREATE TABLE IF NOT EXISTS public_request_rate_limits") || sql.includes("CREATE INDEX IF NOT EXISTS public_request_rate_limits")) return { meta: { changes: 0 } };
          if (sql.includes("DELETE FROM public_request_rate_limits")) {
            for (const [requestId, request] of rateLimitRequests) {
              if (request.created_at < values[0]) rateLimitRequests.delete(requestId);
            }
            return { meta: { changes: 0 } };
          }
          if (sql.includes("INSERT OR IGNORE INTO public_request_rate_limits")) {
            const [requestId, subjectHash, createdAt, countedSubject, windowStart, limit] = values;
            if (rateLimitRequests.has(requestId)) return { meta: { changes: 0 } };
            const count = [...rateLimitRequests.values()].filter((request) => request.subject_hash === countedSubject && request.created_at >= windowStart).length;
            if (count >= limit) return { meta: { changes: 0 } };
            rateLimitRequests.set(requestId, { request_id: requestId, subject_hash: subjectHash, created_at: createdAt });
            return { meta: { changes: 1 } };
          }
          if (sql.includes("INSERT OR IGNORE INTO owner_preview_budget")) {
            if (!row) row = { window_id: values[0], status: "METERING", reserved_calls: 0, reserved_micro_usd: 0, actual_micro_usd: 0, last_result_status: null, created_at: values[1], updated_at: values[2] };
            return { meta: { changes: 1 } };
          }
          if (sql.includes("INSERT OR IGNORE INTO owner_preview_requests")) {
            const [requestId, createdAt, updatedAt] = values;
            if (requests.has(requestId)) return { meta: { changes: 0 } };
            requests.set(requestId, { request_id: requestId, result_status: null, finalized: 0, actual_micro_usd: 0, created_at: createdAt, updated_at: updatedAt });
            return { meta: { changes: 1 } };
          }
          if (sql.includes("SET reserved_calls = reserved_calls + 1")) {
            const [updatedAt, windowId] = values;
            if (row && row.window_id === windowId) {
              row.reserved_calls += 1;
              row.status = "METERING";
              row.updated_at = updatedAt;
              return { meta: { changes: 1 } };
            }
            return { meta: { changes: 0 } };
          }
          if (sql.includes("SET actual_micro_usd = actual_micro_usd +")) {
            if (!row || row.window_id !== values[3]) return { meta: { changes: 0 } };
            row.actual_micro_usd += values[0];
            row.last_result_status = values[1];
            row.updated_at = values[2];
            return { meta: { changes: 1 } };
          }
          if (sql.includes("UPDATE owner_preview_requests")) {
            const [resultStatus, actualMicroUsd, updatedAt, requestId] = values;
            const request = requests.get(requestId);
            if (!request || request.finalized) return { meta: { changes: 0 } };
            request.result_status = resultStatus;
            request.actual_micro_usd = actualMicroUsd;
            request.updated_at = updatedAt;
            request.finalized = 1;
            return { meta: { changes: 1 } };
          }
          throw new Error(`Unexpected SQL: ${sql}`);
        },
        async first() {
          if (sql.includes("FROM public_request_rate_limits")) {
            const request = rateLimitRequests.get(values[0]);
            return request ? { subject_hash: request.subject_hash } : null;
          }
          if (sql.includes("FROM owner_preview_requests")) {
            const request = requests.get(values[0]);
            return request ? { result_status: request.result_status, finalized: request.finalized } : null;
          }
          return row ? { ...row } : null;
        },
      };
    },
    async batch(statements) { return Promise.all(statements.map((statement) => statement.run())); },
  };
}

test("personalized reading usage status starts without an upstream call", async () => {
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  try {
    const app = await worker();
    const db = createBudgetDb();
    const response = await app.fetch(new Request("http://localhost/api/v4/meihua", {
      headers: { "oai-authenticated-user-email": "owner@example.com" },
    }), { ...env, DB: db }, context);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), {
      status: "METERING",
      hard_limit_enabled: false,
      total_attempts: 0,
      actual_total_usd: 0,
      request_limit: null,
      remaining_calls: null,
    });
    assert.equal(db.row.reserved_calls, 0);
  } finally {
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("owner preview meters repeated attempts without blocking on count or reserved spend", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  let upstreamCalls = 0;
  globalThis.fetch = async (_url, init) => {
    upstreamCalls += 1;
    const requestId = JSON.parse(init.body).request_id;
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "SUCCESS",
      personalized_reading: { core_judgment: "test" },
      preview_meta: { actual_api_cost_usd: upstreamCalls === 1 ? 0.02 : 0.03 },
    });
  };
  try {
    const app = await worker();
    const db = createBudgetDb();
    let requestNumber = 0;
    const request = () => new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.10", "oai-authenticated-user-email": "owner@example.com" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: `owner-test-${++requestNumber}` }),
    });
    for (let number = 1; number <= 7; number += 1) {
      assert.equal((await app.fetch(request(), { ...env, DB: db }, context)).status, 200);
    }
    assert.equal(upstreamCalls, 7);
    assert.equal(db.row.reserved_calls, 7);
    assert.equal(db.row.reserved_micro_usd, 0);
    assert.equal(db.row.actual_micro_usd, 200_000);
    assert.equal(db.row.status, "METERING");
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});

test("owner preview submission allows enough time for a sleeping Render service to wake", async () => {
  const previousFetch = globalThis.fetch;
  const previousTimeout = AbortSignal.timeout;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  let requestedTimeout = null;
  AbortSignal.timeout = (milliseconds) => {
    requestedTimeout = milliseconds;
    return previousTimeout(1_000);
  };
  globalThis.fetch = async (_url, init) => {
    const upstreamBody = JSON.parse(init.body);
    assert.equal(upstreamBody.contract_version, "SITES_OWNER_PREVIEW_CONTRACT_V1");
    assert.equal(upstreamBody.user_acknowledgements.no_formal_persistence, true);
    const requestId = upstreamBody.request_id;
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "RUNNING",
    }, { status: 202 });
  };
  try {
    const app = await worker();
    const response = await app.fetch(new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.11", "oai-authenticated-user-email": "owner@example.com" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: "cold-start-test" }),
    }), { ...env, DB: createBudgetDb() }, context);
    assert.equal(response.status, 202);
    assert.equal(requestedTimeout, 90_000);
  } finally {
    globalThis.fetch = previousFetch;
    AbortSignal.timeout = previousTimeout;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});

test("owner preview upstream failure is metered without automatic retry or future blocking", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  let upstreamCalls = 0;
  globalThis.fetch = async (_url, init) => {
    upstreamCalls += 1;
    if (upstreamCalls === 1) throw new Error("synthetic upstream failure");
    const requestId = JSON.parse(init.body).request_id;
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "SUCCESS",
      personalized_reading: { core_judgment: "test" },
      preview_meta: { actual_api_cost_usd: 0.01 },
    });
  };
  try {
    const app = await worker();
    const db = createBudgetDb();
    let requestNumber = 0;
    const request = () => new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.12", "oai-authenticated-user-email": "owner@example.com" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: `owner-failure-${++requestNumber}` }),
    });
    const failed = await app.fetch(request(), { ...env, DB: db }, context);
    const succeeded = await app.fetch(request(), { ...env, DB: db }, context);
    const third = await app.fetch(request(), { ...env, DB: db }, context);
    assert.equal(failed.status, 503);
    assert.equal(succeeded.status, 200);
    assert.equal(third.status, 200);
    assert.equal(upstreamCalls, 3);
    assert.equal(db.row.reserved_calls, 3);
    assert.equal(db.row.reserved_micro_usd, 0);
    assert.equal(db.row.actual_micro_usd, 20_000);
    assert.equal(db.row.status, "METERING");
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});

test("public preview submits and polls without a site login while preserving idempotency", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  const requestId = "owner-poll-test";
  let upstreamCalls = 0;
  globalThis.fetch = async (_url, init) => {
    upstreamCalls += 1;
    if (init?.method === "POST") {
      return Response.json({
        contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
        request_id: requestId,
        status: "RUNNING",
      }, { status: 202 });
    }
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "SUCCESS",
      personalized_reading: { core_judgment: "test" },
      preview_meta: { actual_api_cost_usd: 0.02 },
    });
  };
  try {
    const app = await worker();
    const db = createBudgetDb();
    const started = await app.fetch(new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.13" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: requestId }),
    }), { ...env, DB: db }, context);
    const duplicate = await app.fetch(new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.13" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: requestId }),
    }), { ...env, DB: db }, context);
    const poll = () => app.fetch(new Request(`http://localhost/api/v4/meihua?request_id=${requestId}`), { ...env, DB: db }, context);
    const completed = await poll();
    const repeated = await poll();
    assert.equal(started.status, 202);
    assert.equal(duplicate.status, 202);
    assert.equal(completed.status, 200);
    assert.equal(repeated.status, 200);
    assert.equal(upstreamCalls, 3);
    assert.equal(db.row.reserved_calls, 1);
    assert.equal(db.row.actual_micro_usd, 20_000);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});

test("owner preview ignores the retired total cap and never regenerates a finalized request", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousLimit = process.env.ABALO_PREVIEW_MAX_REQUESTS;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.ABALO_PREVIEW_MAX_REQUESTS = "1";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  let upstreamCalls = 0;
  globalThis.fetch = async (_url, init) => {
    upstreamCalls += 1;
    const requestId = JSON.parse(init.body).request_id;
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "SUCCESS",
      personalized_reading: { core_judgment: "test" },
      preview_meta: { actual_api_cost_usd: 0.01 },
    });
  };
  try {
    const app = await worker();
    const db = createBudgetDb();
    const makeRequest = (requestId) => new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.14", "oai-authenticated-user-email": "beta-user@example.com" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: requestId }),
    });
    const first = await app.fetch(makeRequest("beta-cap-first"), { ...env, DB: db }, context);
    const finalizedDuplicate = await app.fetch(makeRequest("beta-cap-first"), { ...env, DB: db }, context);
    const second = await app.fetch(makeRequest("beta-cap-second"), { ...env, DB: db }, context);
    assert.equal(first.status, 200);
    assert.equal((await first.json()).contract_version, "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1");
    assert.equal(finalizedDuplicate.status, 409);
    assert.equal(second.status, 200);
    assert.equal(upstreamCalls, 2);
    assert.equal(db.row.reserved_calls, 2);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousLimit === undefined) delete process.env.ABALO_PREVIEW_MAX_REQUESTS; else process.env.ABALO_PREVIEW_MAX_REQUESTS = previousLimit;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});

test("public preview limits one network to six new requests per hour", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  let upstreamCalls = 0;
  globalThis.fetch = async (_url, init) => {
    upstreamCalls += 1;
    const requestId = JSON.parse(init.body).request_id;
    return Response.json({
      contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
      request_id: requestId,
      status: "SUCCESS",
      personalized_reading: { core_judgment: "test" },
      preview_meta: { actual_api_cost_usd: 0.01 },
    });
  };
  try {
    const app = await worker();
    const db = createBudgetDb();
    const submit = (requestId) => app.fetch(new Request("http://localhost/api/v4/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json", "cf-connecting-ip": "203.0.113.99" },
      body: JSON.stringify({ contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: requestId }),
    }), { ...env, DB: db }, context);
    for (let number = 1; number <= 6; number += 1) {
      assert.equal((await submit(`public-limit-${number}`)).status, 200);
    }
    const blocked = await submit("public-limit-7");
    assert.equal(blocked.status, 429);
    assert.equal(blocked.headers.get("retry-after"), "3600");
    assert.match((await blocked.json()).error, /每小时最多发起 6 次/);
    assert.equal(upstreamCalls, 6);
    assert.equal(db.row.reserved_calls, 6);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED; else process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
  }
});
