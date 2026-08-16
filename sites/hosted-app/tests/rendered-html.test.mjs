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
  const source = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  assert.match(html, /<title>观象 · 寂然不动，感而遂通天下之故<\/title>/);
  assert.match(html, /寂然不动，感而遂通天下之故/);
  assert.match(html, /心有所问 静观其象/);
  assert.match(html, /hero-entry-wide-v7\.webp/);
  assert.match(html, /hero-entry-square-v7\.webp/);
  assert.match(html, /hero-entry-mobile-v7\.webp/);
  assert.match(html, /entry-hero-final/);
  assert.match(html, /hero-plum-branch-cinematic-v2\.webp/);
  assert.match(html, /hero-butterfly-perched-v3\.png/);
  assert.match(html, /entry-wind-dissolve/);
  assert.doesNotMatch(html, /entry-(?:ink-drop|ripple|taiji)/);
  assert.match(html, /entry-bird-flock/);
  assert.match(html, /hero-boat-v1\.png/);
  assert.doesNotMatch(html, /entry-waterfall/);
  assert.match(html, /hero-title-hotspot/);
  assert.match(html, />闻琴<\/span>/);
  assert.match(html, /hero-guqin-horizontal-v2\.webp/);
  assert.match(html, /<button[^>]+class="hero-scroll-cue"/);
  assert.doesNotMatch(html, /<a[^>]+class="hero-scroll-cue"/);
  assert.match(html, /在天成象/);
  assert.match(html, /在地成形/);
  assert.match(html, /变化见矣/);
  assert.doesNotMatch(html, /在天成象，|在地成形，|变化见矣。/);
  assert.doesNotMatch(html, /遇事不决，可问春风/);
  assert.match(html, /进入正问/);
  assert.match(html, /<button[^>]+id="method-ready"[^>]+aria-pressed="false"/);
  assert.match(html, /method-cta-label/);
  assert.doesNotMatch(html, /method-cta-mini-seal/);
  assert.doesNotMatch(html, /<a[^>]+class="method-cta"/);
  assert.match(html, /href="#method"/);
  assert.match(html, /炁是流动的/);
  assert.match(html, /也带动象的变化/);
  assert.match(html, /请先放下急于知道答案的心/);
  assert.match(html, /现在缓缓做三次深呼吸/);
  assert.doesNotMatch(html, /一步一步看清心中的疑惑|慢慢做三个呼吸|三个呼吸之后，我们进入「正问」/);
  assert.doesNotMatch(html, /观象不会替你决定，也不会预先写好结果/);
  assert.doesNotMatch(html, /程序依规则完成排盘/);
  assert.doesNotMatch(html, /aria-label="观象四步"/);
  assert.match(html, /\/fuxi-bagua-taiji\.svg/);
  assert.match(html, /question-pine-cloud-base-v2\.webp/);
  assert.match(html, /question-cloudfall-mountain-v5\.png/);
  assert.match(html, /question-pine-tree-v2\.png/);
  assert.match(html, /inquiry-cloudfall-canvas-back/);
  assert.match(html, /inquiry-cloudfall-canvas-front/);
  assert.doesNotMatch(html, /inquiry-pine-ground/);
  assert.doesNotMatch(html, /inquiry-cloud-stream-far/);
  assert.doesNotMatch(html, /inquiry-cloud-sky-drift/);
  assert.match(html, /你想问的问题/);
  assert.doesNotMatch(html, /写下一件<br\/>真实具体的事/);
  assert.match(html, /请把你的问题写在这里/);
  assert.match(html, /不必担心问得是否准确/);
  assert.match(html, /确定性排盘 · 个性化解读/);
  assert.doesNotMatch(html, /约三分钟/);
  assert.doesNotMatch(html, /第二阶段 · 明法/);
  assert.match(html, /观象之法 · 壹/);
  assert.match(html, /让我带你进入观象/);
  assert.doesNotMatch(html, /让我用四个步骤/);
  assert.doesNotMatch(html, /这段关系一直没有进展，我还要继续主动吗/);
  assert.match(html, /<h2[^>]+id="inquiry-title"[^>]*>正问<\/h2>/);
  assert.match(html, /<div[^>]+class="inquiry-future-flow"[^>]+hidden/);
  assert.match(html, /问题已经写好/);
  assert.match(html, /观象之法 · 贰/);
  assert.match(html, /<h2[^>]+id="discernment-title"[^>]*>辨识<\/h2>/);
  assert.match(html, /卜卦之前，<br\/>让我帮你把纷繁的念头<br\/>慢慢理清。/);
  assert.match(source, /对问题的不同理解，会让解卦指向不同对象。让我们确认一下。/);
  assert.doesNotMatch(source, /只问一次/);
  assert.doesNotMatch(source, /回答或跳过都可继续/);
  assert.match(html, /discernment-chrysanthemum-mountains-v2\.png/);
  assert.match(html, /<section[^>]+id="final-question"[^>]+hidden/);
  assert.match(html, /id="final-question-title"[^>]*>定问<\/h3>/);
  assert.match(html, /请在心中再默念一遍最终问题/);
  assert.match(html, />缓缓深呼吸<\/span>/);
  assert.match(html, /进入第四步：成卦/);
  assert.doesNotMatch(html, /最终问卦题目/);
  assert.match(html, /<section[^>]+id="casting"[^>]+class="inquiry-step inquiry-panel number-step casting-number-step viewport-page flow-lock-screen"[^>]+hidden/);
  assert.doesNotMatch(html, /class="inquiry-step inquiry-panel cast-step"/);
  assert.match(html, /<h3[^>]+id="casting-title"[^>]*>成卦<\/h3>/);
  assert.match(html, /casting-peony-bloom-1-v1\.png/);
  assert.match(html, /casting-peony-bloom-2-v1\.png/);
  assert.match(html, /casting-peony-bloom-3-v1\.png/);
  assert.match(html, /casting-peony-petal-v1\.png/);
  assert.doesNotMatch(html, /心中默念最终确认的问题/);
  assert.match(html, /缓缓做三次呼吸/);
  assert.match(html, /每次呼吸结束后，在右侧输入一个1–999的整数/);
  assert.doesNotMatch(html, /casting-peony-wind-v1\.png/);
  assert.match(html, /每一息结束，凭第一直觉写下一个数/);
  assert.match(html, /<button[^>]+class="cast-button casting-submit"[^>]*>[\s\S]*开始成卦[\s\S]*<\/button>/);
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

test("question scene preserves anchored ground while separating mountain, pine and cloud motion", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /function InquiryInkScene/);
  assert.match(appSource, /question-pine-cloud-base-v2\.webp/);
  assert.match(appSource, /question-cloudfall-mountain-v5\.png/);
  assert.match(appSource, /question-pine-tree-v2\.png/);
  assert.match(appSource, /<InquiryCloudfallCanvas layer="back"/);
  assert.match(appSource, /<InquiryCloudfallCanvas layer="front"/);
  assert.doesNotMatch(appSource, /inquiry-pine-ground/);
  assert.doesNotMatch(appSource, /question-cloud-stream-v3-tile\.png/);
  assert.match(cssSource, /inquiry-cloud-breath::before[^}]+question-cloudfall-base-v6\.png/);
  assert.match(cssSource, /inquiry-ink-scene \.inquiry-mountain-occluder[^}]+object-position: center 68%/);
  assert.doesNotMatch(cssSource, /inquiry-mountain-occluder[^}]+translate3d/);
  assert.match(cssSource, /inquiry-cloudfall-canvas-front[^}]+z-index: 3/);
  assert.match(cssSource, /inquiry-pine-tree[^}]+animation: inquiry-pine-breeze 6\.8s/);
  assert.match(cssSource, /@keyframes inquiry-cloud-breathe-near/);
  assert.doesNotMatch(cssSource, /inquiry-pine-ground[^}]+clip-path/);
});

test("discernment mirrors the primary-question hierarchy and shows only the current turn", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /className="discernment scroll-section flow-lock-screen"/);
  assert.match(appSource, /className="eyebrow">观象之法 · 贰/);
  assert.match(appSource, /discernment-chrysanthemum-mountains-v2\.png/);
  assert.match(appSource, /discernment-crane-flight-sprite-v1\.png|discernment-crane-facing/);
  assert.doesNotMatch(appSource, /hair-ribbon|discernment-ribbon/);
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
  assert.match(appSource, /这一问暂时不知道/);
  assert.match(appSource, /我已经说清，可以结束辨识/);
  assert.match(appSource, /className="discernment-chrysanthemum-progress"/);
  assert.match(appSource, /Math\.max\(0, 8 - turns\.length\)/);
  assert.doesNotMatch(appSource, /className="discernment-dialogue-head"/);
  assert.match(appSource, /type DiscernmentCompletionReason = "ENOUGH" \| "MAX_TURNS" \| "USER_EARLY"/);
  assert.match(appSource, /nextTurns\.length >= 8[\s\S]+setReview\(payload\); setReviewReason\("MAX_TURNS"\); setCurrentPrompt\(""\); setMode\("REVIEW"\)/);
  assert.match(appSource, /onCompletionReason\("USER_EARLY"\)/);
  assert.match(appSource, /《周易·系辞下》/);
  assert.match(appSource, /穷则变，变则通，通则久/);
  assert.doesNotMatch(appSource, /你选择了提前结束，或已经达到本次最多八问|不必为了问完而继续回答|AI 改写建议/);
  assert.match(appSource, /FIRST_DISCERNMENT_QUESTION = "先从现在说起：这件事目前进行到哪一步了？"/);
  assert.match(appSource, /前 \{turns\.length\} 个回答都还在/);
  assert.match(appSource, /onClick=\{retryTurn\}>继续这一轮/);
  assert.match(appSource, /className="discernment-mist-scroll"/);
  assert.match(appSource, /discernment-mist-scroll-v1\.png/);
  assert.match(appSource, /不怕念起，只怕觉迟/);
  assert.match(appSource, /这一问已记下，下一问正在浮现/);
  assert.doesNotMatch(appSource, /你刚才的回答已经记下|正在从这句话里分清已知与未知/);
  assert.match(cssSource, /\.discernment \.discernment-turn \{ border-top: 0; border-bottom: 0; \}/);
  assert.match(cssSource, /\.discernment \.discernment-working \{ border-top: 0; \}/);
  assert.match(cssSource, /\.discernment \.discernment-classic \{ border-top: 0; border-bottom: 0; \}/);
  assert.doesNotMatch(appSource, /开始 AI 辨识|重新连接 AI 辨识|正在静心听你所问/);
  assert.match(cssSource, /\.discernment \{[^}]+min-height: 100svh[^}]+overflow: hidden/s);
  assert.match(cssSource, /discernment-heading h2[^}]+clamp\(88px, 8\.3vw, 132px\)/);
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
  assert.match(appSource, /根据刚才的回答/);
  assert.match(appSource, /采用建议/);
  assert.match(appSource, /保留原问/);
  assert.match(appSource, /最终问题已经定下/);
  assert.match(appSource, /我感受到你想尽快进入取数卜卦的环节。/);
  assert.match(appSource, /className="final-question-breathing"><span>请在心中再默念一遍最终问题<\/span><span>缓缓深呼吸<\/span>/);
  assert.doesNotMatch(appSource, /请在心中再默念一遍最终问题[，,]|缓缓深呼吸[。\.]/);
  assert.match(appSource, /进入第四步：成卦/);
  assert.doesNotMatch(appSource, /最终问卦题目|final-question-input|question-compare/);
  assert.match(appSource, /onSuggestion\(\{ question: review\.suggested_question, reason: review\.question_change_reason \}\)/);
  assert.match(appSource, /<FinalQuestion hidden=\{!intakeComplete \|\| flowPage !== 5\}/);
  assert.match(appSource, /id="casting" className="inquiry-step inquiry-panel number-step casting-number-step viewport-page flow-lock-screen" hidden=\{!finalQuestionConfirmed \|\| flowPage !== 6\}/);
  assert.match(appSource, /className="final-question-sky-drift"/);
  assert.match(appSource, /className="final-question-bird"/);
  assert.match(appSource, /<p>收回纷乱的念头<br \/>确认你真正想问的事<\/p>/);
  assert.doesNotMatch(appSource, /第三步：定问<br \/>收回纷乱的念头/);
  assert.match(appSource, /<BaguaMark className="final-question-bagua" \/><span className="method-cta-label">/);
  assert.match(cssSource, /final-question-step[^}]+min-height: 100svh/);
  assert.match(cssSource, /final-question-backdrop[^}]+final-question-sunset-reeds-v2\.png/);
  assert.match(cssSource, /final-question-backdrop[^}]+position: fixed[^}]+inset: 0[^}]+width: 100vw[^}]+height: 100svh/);
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
  assert.match(cssSource, /question-change-proposal \{[^}]+border-top: 0[^}]+border-bottom: 0/s);
  assert.match(cssSource, /question-change-proposal blockquote \{[^}]+padding: 0[^}]+border: 0[^}]+var\(--brush\)/s);
  assert.match(cssSource, /final-question-step > \.final-question-heading \{[^}]+position: absolute[^}]+left: clamp\(116px, 10vw, 184px\)/s);
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
  assert.doesNotMatch(appSource, /心中默念最终确认的问题/);
  assert.match(appSource, /缓缓做三次呼吸/);
  assert.doesNotMatch(appSource, /<span>第四步：成卦<\/span>/);
  assert.match(appSource, /每次呼吸结束后，在右侧输入一个1–999的整数/);
  assert.match(appSource, /placeholder: "上卦"/);
  assert.match(appSource, /placeholder: "下卦"/);
  assert.match(appSource, /placeholder: "动爻"/);
  assert.match(appSource, /aria-describedby="casting-range-note"/);
  assert.doesNotMatch(appSource, /casting-peony-wind-v1\.png/);
  assert.match(appSource, /peony-number-field[\s\S]+casting-range-note[\s\S]+className="cast-button casting-submit"[\s\S]+正在成卦，请稍候[\s\S]+三个数已经取好[\s\S]+<\/header>[\s\S]+casting-number-workspace/);
  assert.match(appSource, /className="cast-button casting-submit"[^>]*><BaguaMark \/>/);
  assert.match(appSource, /async function launchDirectHigh\(numbersInput: number\[\]\)/);
  assert.match(appSource, /正在建立唯一一次排盘与解卦任务/);
  assert.match(appSource, /className="cast-button casting-submit"[\s\S]+casting-submit-error/);
  assert.match(cssSource, /\.casting-heading \{ --casting-copy-size: clamp\(22px, 1\.7vw, 29px\)/);
  assert.match(cssSource, /\.casting-heading \.casting-contemplation \{[^}]+font-size: var\(--casting-copy-size\)/);
  assert.match(cssSource, /\.casting-heading \.peony-number-copy b \{ font-size: var\(--casting-copy-size\); \}/);
  assert.match(cssSource, /\.casting-heading \.peony-number-field \{ margin-top: clamp\(72px, 8vh, 92px\); \}/);
  assert.match(cssSource, /\.casting-heading \.casting-submit \{ margin-top: clamp\(72px, 9vh, 96px\); \}/);
  assert.equal((appSource.match(/className="cast-button/g) ?? []).length, 1);
  assert.doesNotMatch(appSource, /function CastingLoader|className="ack"|正在生成解读|确认使用边界/);
  assert.doesNotMatch(appSource, /className="inquiry-step inquiry-panel cast-step"/);
  assert.match(appSource, /peony-bloom-image[\s\S]+peony-petal-layer[\s\S]+peony-petal-origin[\s\S]+peony-falling-petal/);
  assert.match(appSource, /每一息结束，凭第一直觉写下一个数/);
  assert.match(appSource, /guidance: "输入第一个数"/);
  assert.match(appSource, /guidance: "输入第二个数"/);
  assert.match(appSource, /guidance: "输入第三个数"/);
  assert.match(cssSource, /font-family: "Zhi Mang Xing Local"/);
  assert.match(cssSource, /--kai: "Ma Shan Zheng Local"/);
  assert.match(cssSource, /font-family: var\(--input-brush\) !important/);
  assert.doesNotMatch(appSource, /闭上眼睛，缓缓呼吸三次，在心中再默念一遍确认后的问题/);
  assert.doesNotMatch(appSource, /第一数定上卦，第二数定下卦，第三数定动爻/);
  assert.doesNotMatch(appSource, /三个数字只交给程序/);
  assert.doesNotMatch(appSource, /className="breath-ritual"/);
  assert.match(cssSource, /casting-peony-backdrop[^}]+casting-peony-background-v3\.webp/);
  assert.match(cssSource, /casting-heading h3[^}]+font-family: var\(--brush\)/);
  assert.match(cssSource, /casting-heading \.casting-submit \.bagua-mark[^}]+width: 30px[^}]+height: 30px/);
  assert.match(cssSource, /casting-number-step[^}]+overflow: visible/);
  assert.match(cssSource, /casting-number-step::before[^}]+z-index: -3[^}]+background: #f1ede5/);
  assert.match(cssSource, /casting-peony-scene[^}]+width: 100vw[^}]+aspect-ratio: 16 \/ 9/);
  assert.match(cssSource, /casting-number-step[^}]+--casting-viewport-shift/);
  assert.match(cssSource, /casting-number-step > \.casting-heading \{[^}]+position: absolute[^}]+left: clamp\(116px, 10vw, 184px\)/s);
  assert.match(cssSource, /casting-number-step > \.casting-heading \{[^}]+z-index: 2/);
  assert.match(cssSource, /casting-number-workspace \{[^}]+pointer-events: none/);
  assert.match(cssSource, /inquiry\.has-casting-step[^}]+padding-bottom: 0/);
  assert.match(cssSource, /viewport-page[^}]+min-height: calc\(100svh - 68px\)/);
  assert.match(appSource, /useLayoutEffect\(\(\) => \{[\s\S]+if \(!finalQuestionConfirmed\) return;[\s\S]+window\.scrollTo\(\{ top: 0, left: 0, behavior: "auto" \}\)/);
  assert.doesNotMatch(appSource, /getBoundingClientRect\(\)\.top - headerHeight/);
  assert.doesNotMatch(appSource, /getElementById\("casting"\)\?\.scrollIntoView/);
  assert.match(appSource, /className="version-note" hidden/);
  assert.match(appSource, /className="site-footer" hidden/);
  assert.match(cssSource, /casting-peony-scene[^}]+translateX\(calc\(-50% - var\(--casting-viewport-shift\)\)\)/);
  assert.doesNotMatch(cssSource, /peony-bloom-image[^}]+animation:/);
  assert.match(cssSource, /peony-falling-petal[^}]+peony-petal-fall var\(--petal-duration\) linear/);
  assert.match(cssSource, /peony-number \{[^}]+grid-template-columns:[^}]+align-items: center/);
  assert.match(cssSource, /peony-petal-layer \{[^}]+z-index: 2/);
  assert.match(cssSource, /peony-bloom \{[^}]+z-index: 1/);
  assert.match(cssSource, /casting-heading \.peony-number-field[^}]+grid-template-columns: repeat\(3/);
  assert.match(cssSource, /casting-contemplation span:nth-child\(2\)[^}]+margin-left: 0/);
  assert.match(cssSource, /peony-number-copy[^}]+justify-items: start[^}]+text-align: left/);
  assert.match(cssSource, /casting-heading \.casting-submit::after[^}]+content: none/);
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

test("seventh page opens the page-eight data-model review", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.doesNotMatch(appSource, /const numbersReady = numbers\.every|acknowledged/);
  assert.match(appSource, /className="cast-button casting-submit" disabled=\{loading\}/);
  assert.match(appSource, /const \[readingStarted, setReadingStarted\] = useState\(false\)/);
  assert.match(appSource, /function ResultKoiPond\(\)/);
  assert.match(appSource, /id="result" className=\{`result-shell\$\{readingStarted \? " is-reading-started" : " flow-lock-screen"\}`\}/);
  assert.match(appSource, /page7-koi-cinnabar-v1\.png/);
  assert.match(appSource, /page7-koi-ink-v1\.png/);
  assert.match(appSource, /Math\.random\(\)/);
  assert.match(appSource, /requestAnimationFrame\(draw\)/);
  assert.match(appSource, /tailWeight/);
  assert.match(appSource, /context\.rotate\(localAngle\)/);
  assert.match(appSource, /function BrushHexagram/);
  assert.match(appSource, /className="brush-hexagram"/);
  assert.match(appSource, /page7-yao-brush-v1\.png/);
  assert.match(appSource, /page7-yao-brush-short-v1\.png/);
  assert.match(appSource, /className="result-number">第 \{result\.base_hexagram\.king_wen_number\} 卦/);
  assert.match(appSource, /className="result-canonical"><b>卦辞<\/b><span>/);
  assert.doesNotMatch(appSource, /<aside className="result-aside">/);
  assert.doesNotMatch(appSource, /className="result-question"/);
  assert.match(appSource, /aria-controls="result-reading" aria-expanded=\{readingStarted\}/);
  assert.match(appSource, /aria-expanded=\{readingStarted\} onClick=\{openDetailedReading\}>查看详细解卦<\/button>/);
  assert.match(appSource, /function Page8KunStory/);
  assert.match(appSource, /鲲游五境/);
  assert.match(appSource, /className="method-cta final-question-cta page8-kun-finale-cta"/);
  assert.match(appSource, /<span className="method-cta-label">进入观象寄语<\/span>/);
  assert.doesNotMatch(appSource, /五境阅毕 · 下行进入观象寄语|五境阅毕 · 第九页尚未开启/);
  assert.match(appSource, /function finishWithoutSuggestion\(\)[\s\S]+onStructured\(\{/);
  assert.match(appSource, /function ConditionalIntake\(/);
  assert.match(appSource, /status === "ASK_ONCE"/);
  assert.match(appSource, /status: "FAIL_OPEN"/);
  assert.match(appSource, /function confirmQuestion\(\)[\s\S]+setQuestionConfirmed\(true\);\s+\}/);
  assert.match(appSource, /onNeedsClarification=\{\(\) => advanceFlow\(4, "discernment-title"\)\}/);
  assert.match(appSource, /function continueClearQuestionToCasting\(\)[\s\S]+advanceFlow\(6, "casting-title"\)/);
  assert.match(appSource, /className="final-question-confirmed-text">\{finalQuestion\}<\/blockquote>/);
  assert.match(appSource, /clarificationAnswer=\{conditionalIntake\?\.answer\}/);
  assert.match(appSource, /<span>辨识确认<\/span>/);
  assert.match(appSource, /setError\(message\)/);
  assert.match(appSource, /page8Task\.phase === "FAILED"[^\n]+返回正问，重新确认/);
  assert.match(appSource, /flowPageRef\.current = 3;\s+setResponse\(null\); setFlowPage\(3\)/);
  assert.match(appSource, /setResponse\(\{ \.\.\.payload, user_question: question \}\)/);
  assert.match(appSource, /async function launchDirectHigh\(numbersInput: number\[\]\)/);
  assert.match(appSource, /fetch\("\/api\/direct-reading\/v2"/);
  assert.match(appSource, /await launchDirectHigh\(parsed\)/);
  assert.doesNotMatch(appSource, /const deterministicRequest = fetch\("\/api\/v3\/meihua"/);
  assert.match(appSource, /function DirectHighResultView\(/);
  assert.match(appSource, /<Page8KunStory reading=\{reading\}/);
  assert.match(appSource, /const page8Reading = response\.page8_reading \?\? buildPage8Scaffold\(response\)/);
  assert.match(appSource, /function Page8TaskPanel/);
  assert.match(appSource, /辨识不会参与排盘/);
  assert.match(appSource, /id="result-reading" hidden=\{!readingStarted\}/);
  assert.match(appSource, /window\.matchMedia\("\(prefers-reduced-motion: reduce\)"\)/);
  assert.match(cssSource, /result-overview[^}]+grid-template-columns: minmax\(0, 1fr\) minmax\(0, 1fr\)/);
  assert.match(cssSource, /page7-taiji-bg-v1\.png/);
  assert.match(cssSource, /result-koi-layer[^}]+pointer-events: none/);
  assert.match(cssSource, /result-detail-button:hover, \.result-detail-button:focus-visible/);
});

test("first seven pages are single-screen, forward-only and scroll locked", async () => {
  const appSource = await fs.readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  const cssSource = await fs.readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(appSource, /const \[flowPage, setFlowPage\] = useState\(1\)/);
  assert.match(appSource, /if \(nextPage <= flowPageRef\.current \|\| nextPage > 7\) return/);
  assert.match(appSource, /window\.addEventListener\("wheel", blockScroll, \{ passive: false \}\)/);
  assert.match(appSource, /window\.addEventListener\("touchmove", blockScroll, \{ passive: false \}\)/);
  assert.match(appSource, /data-flow-page=\{flowPage\}/);
  assert.match(appSource, /hidden=\{flowPage !== 1\}/);
  assert.match(appSource, /hidden=\{flowPage !== 2\}/);
  assert.match(appSource, /hidden=\{flowPage !== 3\}/);
  assert.match(appSource, /hidden=\{flowPage !== 4\}/);
  assert.match(appSource, /flowPage !== 5/);
  assert.match(appSource, /flowPage !== 6/);
  assert.match(appSource, /response && flowPage === 7/);
  assert.match(cssSource, /flow-scroll-locked[^}]+overflow: hidden !important/);
  assert.match(cssSource, /flow-lock-screen[^}]+height: 100svh !important[^}]+max-height: 100svh !important/);
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
