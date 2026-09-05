import assert from "node:assert/strict";
import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { createServer } from "node:net";
import test from "node:test";
import { SqliteDatabase } from "../portable/sqlite";
import { sanitizeRequest } from "../portable/request-boundary";
import { instrumentEngineFetch } from "../portable/upstream-diagnostics";
import { setRuntimeDb } from "../db";
import { reservePublicRequestRateLimit } from "../db/public-request-rate-limit";

test("engine diagnostics preserve responses and never log private content", async () => {
  const events: Record<string, string | number | boolean>[] = [];
  const privateText = "secret-user-content";
  const transport = instrumentEngineFetch(async () => new Response(privateText, {
    status: 200, headers: { "Content-Type": "text/html", "cf-mitigated": "challenge" },
  }), "https://engine.example", event => events.push(event));
  const response = await transport("https://engine.example/api/preview/v2/direct-reading/jobs", {
    method: "POST", headers: { "X-Abalo-Engine-Key": privateText }, body: privateText,
  });
  assert.equal(await response.text(), privateText);
  assert.deepEqual(events, [{ event: "engine_transport", operation: "submit", status: 200,
    format: "html", challenge: true, renderOrigin: false, retryAfterPresent: false }]);
  assert.ok(!JSON.stringify(events).includes(privateText));
  await transport("https://other.example/");
  assert.equal(events.length, 1);
});

test("SQLite persists data and preserves duplicate column order for Drizzle", async () => {
  const filename = resolve(mkdtempSync(resolve(tmpdir(), "gx-sqlite-")), "test.sqlite");
  let db = new SqliteDatabase(filename);
  await db.prepare("CREATE TABLE records (id TEXT PRIMARY KEY, note TEXT)").run();
  await db.prepare("INSERT INTO records VALUES (?, ?)").bind("one", "中文验证").run();
  assert.deepEqual(await db.prepare("SELECT id, note, id FROM records").raw(), [["one", "中文验证", "one"]]);
  db.close();
  db = new SqliteDatabase(filename);
  assert.equal(await db.prepare("SELECT note FROM records").first("note"), "中文验证");
  db.close();
});

test("SQLite batch rolls back every write on a later constraint failure", async () => {
  const db = new SqliteDatabase(":memory:");
  await db.prepare("CREATE TABLE records (id TEXT PRIMARY KEY)").run();
  await assert.rejects(db.batch([
    db.prepare("INSERT INTO records VALUES (?)").bind("same"),
    db.prepare("INSERT INTO records VALUES (?)").bind("same"),
  ]));
  assert.equal(await db.prepare("SELECT count(*) AS n FROM records").first("n"), 0);
  db.close();
});

test("real SQLite admits only six concurrent reservations and preserves idempotency", async () => {
  const db = new SqliteDatabase(":memory:");
  setRuntimeDb(db as unknown as D1Database);
  try {
    const result = await Promise.all(Array.from({ length: 20 }, (_, n) =>
      reservePublicRequestRateLimit("a".repeat(64), `portable-${n}`)));
    assert.equal(result.filter(r => r.allowed).length, 6);
    assert.deepEqual(await reservePublicRequestRateLimit("a".repeat(64), "portable-0"),
      { allowed: true, isNewRequest: false });
    assert.equal((await reservePublicRequestRateLimit("b".repeat(64), "portable-0")).allowed, false);
  } finally { setRuntimeDb(undefined); db.close(); }
});

test("public clients cannot forge the owner or their rate-limit identity", () => {
  const request = { headers: {
    "oai-authenticated-user-email": "owner@example.com",
    "cf-connecting-ip": "8.8.8.8",
    "x-forwarded-for": "1.1.1.1",
    "x-forwarded-host": "evil.example",
  } as Record<string, string>, socket: { remoteAddress: "::ffff:192.0.2.10" } };
  sanitizeRequest(request, new Set(), new URL("https://example.com"));
  assert.equal(request.headers["oai-authenticated-user-email"], undefined);
  assert.equal(request.headers["cf-connecting-ip"], "192.0.2.10");
  assert.equal(request.headers.host, "example.com");
  assert.equal(request.headers["x-forwarded-for"], undefined);
});

test("trusted reverse proxy uses the last appended valid address, not forged leftmost entries", () => {
  const request = { headers: { "x-forwarded-for": "8.8.8.8, 192.0.2.20" } as Record<string, string>,
    socket: { remoteAddress: "127.0.0.1" } };
  sanitizeRequest(request, new Set(["127.0.0.1"]), new URL("https://example.com"));
  assert.equal(request.headers["cf-connecting-ip"], "192.0.2.20");
});

async function stop(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null) return;
  const exited = once(child, "exit");
  child.kill();
  await exited;
}

async function freePort(): Promise<number> {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  await new Promise<void>(done => server.close(() => done()));
  return port;
}

async function waitForOutput(child: ChildProcess, pattern: RegExp): Promise<string> {
  return new Promise((done, reject) => {
    let output = "";
    const timer = setTimeout(() => reject(new Error(`Process startup timeout: ${output}`)), 20_000);
    child.once("error", error => { clearTimeout(timer); reject(error); });
    child.once("exit", code => { clearTimeout(timer); reject(new Error(`Exited ${code}: ${output}`)); });
    child.stdout!.on("data", data => { output += data.toString(); if (pattern.test(output)) { clearTimeout(timer); done(output); } });
    child.stderr!.on("data", data => { output += data.toString(); });
  });
}

test("portable HTTP serves frozen UI/assets, isolates journals, rejects forged auth and completes real Python transport", { timeout: 70_000 }, async () => {
  const port = await freePort();
  const origin = `http://localhost:${port}`;
  const filename = resolve(mkdtempSync(resolve(tmpdir(), "gx-http-")), "test.sqlite");
  const python = spawn(process.env.ABALO_TEST_PYTHON || resolve(process.platform === "win32"
    ? "../../.venv/Scripts/python.exe" : "../../.venv/bin/python"),
    ["tests/fixtures/direct-reading-python-server.py"], { stdio: ["ignore", "pipe", "pipe"] });
  let app: ChildProcess | undefined;
  try {
    const pythonOutput = await waitForOutput(python, /^\d+\r?\n/);
    const enginePort = Number(pythonOutput.split(/\r?\n/)[0]);
    const startApp = () => spawn(process.execPath, ["--experimental-strip-types", "portable/server.ts"], {
      stdio: ["ignore", "pipe", "pipe"], env: {
        ...process.env, PORT: String(port), HOST: "127.0.0.1", NODE_ENV: "production",
        GUANXIANG_PUBLIC_ORIGIN: origin, GUANXIANG_SQLITE_PATH: filename,
        ABALO_PUBLIC_BETA_ENABLED: "true", ABALO_DIRECT_READING_V2_PREVIEW_ENABLED: "true",
        ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED: "true",
        ABALO_PREVIEW_OWNER_EMAIL: "owner@example.com",
        PYTHON_ENGINE_URL: `http://127.0.0.1:${enginePort}`,
        PYTHON_ENGINE_KEY: "cross-layer-test-engine-key-that-is-long-enough",
      },
    });
    app = startApp();
    await waitForOutput(app, /Guanxiang portable ready/);
    const health = await fetch(`${origin}/healthz`);
    assert.equal(health.status, 200);
    const home = await fetch(origin);
    assert.equal(home.status, 200);
    const html = await home.text();
    assert.match(html, /观象/);
    assert.match(html, /p1-motion-pre-reveal-base-v2.png/);
    assert.match(html, new RegExp(`${origin}/manifest-v2.webmanifest`));
    assert.doesNotMatch(html, /https:\/\/guanxiang-mobile\.abaloyuan\.chatgpt\.site/);
    // SSR alone is insufficient: verify every emitted hydration/style module.
    for (const name of readdirSync("dist-portable/client/assets")) {
      if (!/\.(js|css)$/.test(name)) continue;
      const assetResponse = await fetch(`${origin}/assets/${name}`);
      assert.equal(assetResponse.status, 200, name);
      assert.match(assetResponse.headers.get("content-type") || "", name.endsWith(".css") ? /text\/css/ : /javascript/);
      assert.ok((await assetResponse.arrayBuffer()).byteLength > 0);
    }
    const range = await fetch(`${origin}/p1-mobile-motion-selected-v1.mp4`, { headers: { Range: "bytes=0-99" } });
    assert.equal(range.status, 206);
    assert.equal((await range.arrayBuffer()).byteLength, 100);
    assert.match(range.headers.get("content-range") || "", /^bytes 0-99\//);
    assert.equal((await fetch(`${origin}/p1-mobile-motion-selected-v1.mp4`, { headers: { Range: "bytes=999999999999-" } })).status, 416);
    assert.equal((await fetch(`${origin}/.vite/manifest.json`)).status, 404);
    assert.equal((await fetch(`${origin}/assets/missing.js.map`)).status, 404);
    assert.equal((await fetch(`${origin}/.env`)).status, 404);
    for (const asset of ["/manifest-v2.webmanifest", "/sw.js", "/icon-192.png", "/p1-mobile-motion-selected-v1.mp4"]) {
      const response = await fetch(`${origin}${asset}`);
      assert.equal(response.status, 200, asset);
      await response.arrayBuffer();
    }
    const token = "portable-device-" + "a".repeat(32);
    const headers = { "Content-Type": "application/json", "x-guanxiang-key": token };
    const record = { id: crypto.randomUUID(), question: "这是迁移测试用的问题", numbers: [38, 71, 24],
      structured_intake: {}, result: {}, action_text: "仅用于数据库测试" };
    assert.equal((await fetch(`${origin}/api/journal`, { method: "POST", headers, body: JSON.stringify(record) })).status, 201);
    const own = await (await fetch(`${origin}/api/journal`, { headers })).json() as { records: unknown[] };
    assert.equal(own.records.length, 1);
    const other = await (await fetch(`${origin}/api/journal`, { headers: { "x-guanxiang-key": "b".repeat(40) } })).json() as { records: unknown[] };
    assert.equal(other.records.length, 0);
    assert.equal((await fetch(`${origin}/api/journal`)).status, 401);
    assert.equal((await fetch(`${origin}/api/feedback`, { method: "POST", headers,
      body: JSON.stringify({ kind: "其他", content: "独立部署迁移测试反馈" }) })).status, 201);

    // The Python fixture uses the real deterministic engine and HTTP transport.
    // Model output is a frozen fixture, NOT a live model quality test.
    const id = "drv2-" + "1".repeat(32);
    const body = JSON.stringify({ contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
      request_id: id, question_text: "我现在应该集中资源推进这个测试项目吗？", numbers: [38, 71, 24] });
    const post = await fetch(`${origin}/api/direct-reading/v2`, { method: "POST", headers, body });
    assert.equal(post.status, 202, await post.clone().text());
    let payload: Record<string, unknown> = {};
    for (let n = 0; n < 40; n++) {
      const result = await fetch(`${origin}/api/direct-reading/v2?request_id=${id}`);
      payload = await result.json();
      if (payload.status !== "RUNNING") break;
      await new Promise(done => setTimeout(done, 150));
    }
    assert.equal(payload.status, "SUCCESS", JSON.stringify(payload));
    assert.ok(payload.product_presentation);
    assert.ok(payload.page9_finale);
    assert.doesNotMatch(JSON.stringify(payload), /must-not-cross-public-boundary/);
    for (let n = 2; n <= 6; n++) {
      const response = await fetch(`${origin}/api/direct-reading/v2`, { method: "POST", headers,
        body: body.replace(id, "drv2-" + String(n).repeat(32)) });
      assert.notEqual(response.status, 429);
      await response.text();
    }
    const forbidden = await fetch(`${origin}/api/direct-reading/v2`, { method: "POST",
      headers: { ...headers, "oai-authenticated-user-email": "owner@example.com", "cf-connecting-ip": "203.0.113.25", "x-forwarded-for": "203.0.113.26" },
      body: body.replace(id, "drv2-" + "7".repeat(32)) });
    assert.equal(forbidden.status, 429);
    assert.equal(forbidden.headers.get("retry-after"), "3600");
    await stop(app); app = undefined;
    const db = new SqliteDatabase(filename);
    assert.equal(await db.prepare("SELECT count(*) AS n FROM observations").first("n"), 1);
    assert.equal(await db.prepare("SELECT count(*) AS n FROM public_request_rate_limits").first("n"), 6);
    assert.equal(await db.prepare("SELECT state FROM direct_reading_preview_jobs WHERE request_id = ?").bind(id).first("state"), "FINALIZED");
    db.close();
    app = startApp();
    await waitForOutput(app, /Guanxiang portable ready/);
    const restored = await (await fetch(`${origin}/api/journal`, { headers })).json() as { records: unknown[] };
    assert.equal(restored.records.length, 1);
    const restoredJob = await (await fetch(`${origin}/api/direct-reading/v2?request_id=${id}`)).json() as { status: unknown };
    assert.equal(restoredJob.status, "SUCCESS");
    const stillLimited = await fetch(`${origin}/api/direct-reading/v2`, {
      method: "POST", headers, body: body.replace(id, "drv2-" + "8".repeat(32)),
    });
    assert.equal(stillLimited.status, 429);
  } finally { if (app) await stop(app); await stop(python); }
});
