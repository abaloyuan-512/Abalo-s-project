import assert from "node:assert/strict";
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
  assert.match(html, /在天成象，/);
  assert.match(html, /在地成形，变化见矣/);
  assert.match(html, /遇事不决，可问春风/);
  assert.match(html, /href="#method"/);
  assert.match(html, /所谓观象的意思，就是观察身边的现象/);
  assert.match(html, /三数起卦的排盘规则/);
  assert.match(html, /\/trigrams\/qian\.png/);
  assert.match(html, /你真正想问的问题/);
  assert.match(html, /问题原文只用于理解与呈现，不参与排盘/);
  assert.match(html, /约三分钟 · 确定性排盘/);
  assert.match(html, /用三分钟，把一件拿不准的事/);
  assert.match(html, /三个数字.*决定卦象/);
  assert.match(html, /写清所问/);
  assert.match(html, /说明现实处境/);
  assert.match(html, /静心取数/);
  assert.match(html, /观事簿/);
  assert.doesNotMatch(html, /何为观象|冻结规则|当前不收费|当前为视觉验收版|PRIVATE PREVIEW/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("renders public method, privacy and usage pages", async () => {
  const app = await worker();
  for (const [path, expected] of [["/about", /MEIHUA_RULE_SPEC_V1/], ["/privacy", /只有当你主动点击/], ["/guide", /一次观象大约需要三分钟/]]) {
    const response = await app.fetch(new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }), env, context);
    assert.equal(response.status, 200);
    assert.match(await response.text(), expected);
  }
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
