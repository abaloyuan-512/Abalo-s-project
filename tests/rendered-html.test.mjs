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
  assert.match(html, /你真正想问的问题/);
  assert.match(html, /问题原文只用于理解与呈现，不参与排盘/);
  assert.match(html, /确定性排盘 · 私有体验/);
  assert.doesNotMatch(html, /当前为视觉验收版|PRIVATE PREVIEW/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
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
