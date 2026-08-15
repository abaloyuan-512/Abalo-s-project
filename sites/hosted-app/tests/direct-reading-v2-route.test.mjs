import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

async function worker() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("direct-v2-test", `${process.pid}-${Date.now()}-${Math.random()}`);
  return (await import(workerUrl.href)).default;
}

const baseEnv = { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } };
const context = { waitUntil() {}, passThroughOnException() {} };
const ownerHeaders = {
  "Content-Type": "application/json",
  "oai-authenticated-user-email": "owner@example.com",
};
const here = dirname(fileURLToPath(import.meta.url));

async function startPythonFixture() {
  const executable = process.env.ABALO_TEST_PYTHON || resolve(here, "../../../.venv/Scripts/python.exe");
  const script = resolve(here, "fixtures/direct-reading-python-server.py");
  const child = spawn(executable, [script], { stdio: ["ignore", "pipe", "pipe"] });
  let stdout = "";
  const port = await new Promise((resolvePort, reject) => {
    const timeout = setTimeout(() => reject(new Error("Python fixture did not start")), 10_000);
    child.once("error", reject);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      const line = stdout.split(/\r?\n/, 1)[0]?.trim();
      if (/^\d+$/.test(line)) {
        clearTimeout(timeout);
        resolvePort(Number(line));
      }
    });
  });
  return {
    port,
    async stop() {
      if (child.exitCode === null) child.kill();
      await Promise.race([once(child, "exit"), new Promise((resolveWait) => setTimeout(resolveWait, 3_000))]);
    },
  };
}

function createDirectDb() {
  const jobs = new Map();
  return {
    jobs,
    prepare(sql) {
      let values = [];
      return {
        bind(...next) { values = next; return this; },
        async run() {
          if (sql.includes("CREATE TABLE IF NOT EXISTS direct_reading_preview_jobs")) return { meta: { changes: 0 } };
          if (sql.includes("INSERT OR IGNORE INTO direct_reading_preview_jobs")) {
            const [requestId, digest, promptVersion, createdAt, updatedAt] = values;
            if (jobs.has(requestId)) return { meta: { changes: 0 } };
            jobs.set(requestId, {
              payload_sha256: digest,
              prompt_version: promptVersion,
              state: "RUNNING",
              result_status: null,
              created_at: createdAt,
              updated_at: updatedAt,
            });
            return { meta: { changes: 1 } };
          }
          if (sql.includes("SET state = 'FINALIZED'")) {
            const [status, updatedAt, requestId] = values;
            const job = jobs.get(requestId);
            if (!job || job.state !== "RUNNING") return { meta: { changes: 0 } };
            Object.assign(job, { state: "FINALIZED", result_status: status, updated_at: updatedAt });
            return { meta: { changes: 1 } };
          }
          if (sql.includes("SET state = 'LOST'")) {
            const [status, updatedAt, requestId] = values;
            const job = jobs.get(requestId);
            if (!job || job.state !== "RUNNING") return { meta: { changes: 0 } };
            Object.assign(job, { state: "LOST", result_status: status, updated_at: updatedAt });
            return { meta: { changes: 1 } };
          }
          throw new Error(`Unexpected SQL: ${sql}`);
        },
        async first() {
          if (sql.includes("FROM direct_reading_preview_jobs")) {
            const row = jobs.get(values[0]);
            return row ? { ...row } : null;
          }
          throw new Error(`Unexpected SQL first: ${sql}`);
        },
      };
    },
  };
}

function postRequest(requestId, question = "我现在必须二选一：把主要资源集中到一个新产品并承担更大波动，还是继续平均分散在多个成熟方向？") {
  return new Request("http://localhost/api/direct-reading/v2", {
    method: "POST",
    headers: ownerHeaders,
    body: JSON.stringify({
      contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
      request_id: requestId,
      question_text: question,
      numbers: [38, 71, 24],
    }),
  });
}

test("conditional intake public boundary exposes only one fixed question decision", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "http://127.0.0.1:8765";
  process.env.PYTHON_ENGINE_KEY = "cross-layer-test-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  globalThis.fetch = async (input) => {
    const url = String(input);
    if (url.includes("/api/preview/v2/direct-reading/intake")) {
      return Response.json({
        contract_version: "SITES_CONDITIONAL_INTAKE_PRODUCT_V1",
        intake_id: "intake-3333333333333333",
        status: "ASK_ONCE",
        ambiguity_kind: "JUDGMENT_OBJECT",
        clarification_prompt: "你这次希望判断的具体对象是哪一个？",
        failure_code: null,
        original_question_sha_before: "A".repeat(64),
        original_question_sha_after: "A".repeat(64),
        original_question_preserved: true,
        router_attempts: 1,
        automatic_retries: 0,
        router_cast_count: 0,
        router_high_calls: 0,
        secret_raw_output: "must-not-cross",
      });
    }
    return previousFetch(input);
  };
  try {
    const app = await worker();
    const response = await app.fetch(new Request("http://localhost/api/direct-reading/v2/intake", {
      method: "POST",
      headers: ownerHeaders,
      body: JSON.stringify({
        contract_version: "SITES_CONDITIONAL_INTAKE_PRODUCT_V1",
        intake_id: "intake-3333333333333333",
        original_question: "我和合伙人各自负责一个项目；现在应该暂停这个项目吗？",
      }),
    }), baseEnv, context);
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.status, "ASK_ONCE");
    assert.equal(payload.ambiguity_kind, "JUDGMENT_OBJECT");
    assert.equal(payload.clarification_prompt, "你这次希望判断的具体对象是哪一个？");
    assert.equal(JSON.stringify(payload).includes("must-not-cross"), false);
    assert.equal(JSON.stringify(payload).includes("我和合伙人"), false);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED; else process.env.ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("direct preview is owner-only and disabled by default", async () => {
  const previous = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  try {
    const app = await worker();
    const db = createDirectDb();
    const anonymous = await app.fetch(new Request("http://localhost/api/direct-reading/v2", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }), { ...baseEnv, DB: db }, context);
    const disabled = await app.fetch(postRequest("drv2-1111111111111111"), { ...baseEnv, DB: db }, context);
    assert.equal(anonymous.status, 403);
    assert.equal(disabled.status, 503);
    assert.equal((await disabled.json()).terminal, true);
    assert.equal(db.jobs.size, 0);
  } finally {
    if (previous === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
    else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previous;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL;
    else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("wrong owner and four-to-five-character questions fail before persistence", async () => {
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  try {
    const app = await worker();
    const db = createDirectDb();
    const wrongOwner = await app.fetch(new Request("http://localhost/api/direct-reading/v2", {
      method: "POST",
      headers: { ...ownerHeaders, "oai-authenticated-user-email": "other@example.com" },
      body: "{}",
    }), { ...baseEnv, DB: db }, context);
    assert.equal(wrongOwner.status, 403);
    for (const question of ["四个字吗", "只有五个字"]) {
      const rejected = await app.fetch(postRequest(`drv2-${"5".repeat(16 + question.length)}`, question), { ...baseEnv, DB: db }, context);
      assert.equal(rejected.status, 400);
    }
    assert.equal(db.jobs.size, 0);
  } finally {
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("real Sites route and Python transport expose CAST_READY facts before the final reading", async () => {
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  const fixture = await startPythonFixture();
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = `http://127.0.0.1:${fixture.port}`;
  process.env.PYTHON_ENGINE_KEY = "cross-layer-test-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  const requestId = "drv2-6666666666666666";
  try {
    const app = await worker();
    const db = createDirectDb();
    const submitted = await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context);
    assert.equal(submitted.status, 202);
    const initial = await submitted.json();
    assert.equal(typeof initial.stage, "string");
    assert.equal(initial.chart_facts.base_hexagram.name, "水山蹇");
    assert.equal(JSON.stringify(initial).includes("must-not-cross-public-boundary"), false);

    let terminal = null;
    for (let index = 0; index < 40; index += 1) {
      const polled = await app.fetch(new Request(`http://localhost/api/direct-reading/v2?request_id=${requestId}`, {
        headers: { "oai-authenticated-user-email": "owner@example.com" },
      }), { ...baseEnv, DB: db }, context);
      if (polled.status === 200) {
        terminal = await polled.json();
        break;
      }
      assert.equal(polled.status, 202);
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
    }
    assert.equal(terminal?.status, "SUCCESS");
    assert.match(terminal?.direct_reading?.text ?? "", /^## 判断/);
    assert.equal(terminal?.product_presentation?.reconstructed_equals_source, true);
    assert.equal(terminal?.direct_high?.route, "DIRECT_HIGH");
    assert.equal(db.jobs.get(requestId).state, "FINALIZED");
  } finally {
    await fixture.stop();
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("malformed P8/P9 upstream payload fails closed at the public boundary", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  const fixture = await startPythonFixture();
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = `http://127.0.0.1:${fixture.port}`;
  process.env.PYTHON_ENGINE_KEY = "cross-layer-test-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  globalThis.fetch = async (...args) => {
    const response = await previousFetch(...args);
    const body = await response.clone().json().catch(() => null);
    if (body?.status === "SUCCESS" && body?.product_presentation) {
      if (body.request_id === "drv2-7777777777777777") {
        body.product_presentation.page8.base_hexagram = null;
        body.product_presentation.page9.responsibility = "WRONG_PAGE";
        body.product_presentation.page9.judgment.start_offset = -1;
      } else {
        const falseDigest = "A".repeat(64);
        body.product_presentation.source_reading_sha256 = falseDigest;
        body.product_presentation.reconstructed_reading_sha256 = falseDigest;
        body.product_presentation.page9.judgment.sha256 = falseDigest;
        body.product_presentation.page8.program_strength.program_fact_sha256 = falseDigest;
      }
      return Response.json(body, { status: response.status, headers: response.headers });
    }
    return response;
  };
  const requestId = "drv2-7777777777777777";
  try {
    const app = await worker();
    const db = createDirectDb();
    assert.equal((await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context)).status, 202);
    let terminal = null;
    for (let index = 0; index < 40; index += 1) {
      const polled = await app.fetch(new Request(`http://localhost/api/direct-reading/v2?request_id=${requestId}`, {
        headers: { "oai-authenticated-user-email": "owner@example.com" },
      }), { ...baseEnv, DB: db }, context);
      if (polled.status === 200) {
        terminal = await polled.json();
        break;
      }
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
    }
    assert.equal(terminal?.status, "BLOCKED_OUTPUT");
    assert.equal(terminal?.error_code, "PRODUCT_PRESENTATION_REJECTED");
    assert.equal(terminal?.direct_reading, null);
    assert.equal(terminal?.product_presentation, null);
    assert.equal(terminal?.direct_high, null);

    const digestRequestId = "drv2-8888888888888888";
    assert.equal((await app.fetch(postRequest(digestRequestId), { ...baseEnv, DB: db }, context)).status, 202);
    let digestTerminal = null;
    for (let index = 0; index < 40; index += 1) {
      const polled = await app.fetch(new Request(`http://localhost/api/direct-reading/v2?request_id=${digestRequestId}`, {
        headers: { "oai-authenticated-user-email": "owner@example.com" },
      }), { ...baseEnv, DB: db }, context);
      if (polled.status === 200) {
        digestTerminal = await polled.json();
        break;
      }
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
    }
    assert.equal(digestTerminal?.status, "BLOCKED_OUTPUT");
    assert.equal(digestTerminal?.error_code, "PRODUCT_PRESENTATION_REJECTED");
    assert.equal(digestTerminal?.direct_reading, null);
    assert.equal(digestTerminal?.product_presentation, null);
    assert.equal(digestTerminal?.direct_high, null);
  } finally {
    globalThis.fetch = previousFetch;
    await fixture.stop();
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("final canary helper traverses the same owner route and persistent job layer", async () => {
  const fixture = await startPythonFixture();
  try {
    const helper = resolve(here, "fixtures/run-final-sites-canary.mjs");
    const dist = resolve(here, "../dist/server/index.js");
    const child = spawn(process.execPath, [
      helper,
      dist,
      String(fixture.port),
      "cross-layer-test-engine-key-that-is-long-enough",
      "drv2-9999999999999999",
      "我现在必须二选一：把主要资源集中到一个新产品并承担更大波动，还是继续平均分散在多个成熟方向？",
      "[38,71,24]",
    ], { stdio: ["ignore", "pipe", "pipe"] });
    let output = "";
    let errors = "";
    child.stdout.on("data", (chunk) => { output += chunk.toString("utf8"); });
    child.stderr.on("data", (chunk) => { errors += chunk.toString("utf8"); });
    const [code] = await once(child, "exit");
    assert.equal(code, 0, errors);
    const evidence = JSON.parse(output);
    assert.equal(evidence.submitted_http_status, 202);
    assert.equal(evidence.initial.chart_facts.base_hexagram.name, "水山蹇");
    assert.equal(evidence.terminal.status, "SUCCESS");
    assert.equal(evidence.persisted_state, "FINALIZED");
    assert.equal(evidence.upstream_post_count, 1);
  } finally {
    await fixture.stop();
  }
});

test("twenty concurrent duplicate submissions create one upstream job and persist the digest", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  const requestId = "drv2-2222222222222222";
  let upstreamPosts = 0;
  globalThis.fetch = async (_url, init) => {
    if (init?.method === "POST") upstreamPosts += 1;
    return Response.json({
      contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
      request_id: requestId,
      status: "RUNNING",
      stage: "MODEL_REQUESTED",
      audit: { model: "must-not-leak" },
    }, { status: 202 });
  };
  try {
    const app = await worker();
    const db = createDirectDb();
    const responses = await Promise.all(Array.from({ length: 20 }, () =>
      app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context)));
    assert.equal(upstreamPosts, 1);
    assert.equal(responses.every((response) => response.status === 202), true);
    assert.equal(db.jobs.size, 1);
    const persisted = db.jobs.get(requestId);
    assert.match(persisted.payload_sha256, /^[A-F0-9]{64}$/);
    assert.equal(persisted.prompt_version, "GUANXIANG_DIRECT_READING_PROMPT_V2");
    const bodies = await Promise.all(responses.map((response) => response.json()));
    assert.equal(bodies.some((body) => JSON.stringify(body).includes("must-not-leak")), false);
    const conflict = await app.fetch(postRequest(requestId, "这是另一个不同的问题，应当拒绝冲突。"), { ...baseEnv, DB: db }, context);
    assert.equal(conflict.status, 409);
    assert.equal(upstreamPosts, 1);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("terminal response without product evidence is blocked and never regenerates", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  const requestId = "drv2-3333333333333333";
  let upstreamPosts = 0;
  globalThis.fetch = async (_url, init) => {
    if (init?.method === "POST") upstreamPosts += 1;
    return Response.json({
      contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
      request_id: requestId,
      status: "SUCCESS",
      direct_reading: {
        text: "## 判断\n完整正文",
        content_format: "MARKDOWN",
        version: "test",
        validation_status: "PASSED",
        chart_facts: {
          base_hexagram: { role: "BASE", king_wen_number: 59, name: "风水涣", upper_trigram: "巽", lower_trigram: "坎", model: "nested-secret" },
          mutual_hexagram: { role: "MUTUAL", king_wen_number: 27, name: "山雷颐", upper_trigram: "艮", lower_trigram: "震" },
          changed_hexagram: { role: "CHANGED", king_wen_number: 57, name: "巽为风", upper_trigram: "巽", lower_trigram: "巽" },
          moving_line: { position: 3, name: "六三", canonical_line_text: "渙其躬，无悔。", canonical_data_version: "V1" },
          rule_version: "RULE_V1",
          engine_version: "ENGINE_V1",
          usage: "nested-secret",
        },
      },
      audit: { question_sha256: "secret", model: "secret", usage: { total: 99 }, latency_ms: 100 },
    });
  };
  try {
    const app = await worker();
    const db = createDirectDb();
    const completed = await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context);
    assert.equal(completed.status, 200);
    const body = await completed.json();
    assert.equal(body.status, "BLOCKED_OUTPUT");
    assert.equal(body.error_code, "PRODUCT_PRESENTATION_REJECTED");
    assert.equal(body.direct_reading, null);
    for (const forbidden of ["question_sha256", "model", "usage", "latency_ms", "nested-secret"]) {
      assert.equal(JSON.stringify(body).includes(forbidden), false);
    }
    const repeated = await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context);
    assert.equal(repeated.status, 409);
    assert.equal(upstreamPosts, 1);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});

test("engine restart becomes a stable lost terminal state without a second submission", async () => {
  const previousFetch = globalThis.fetch;
  const previousGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
  const previousUrl = process.env.PYTHON_ENGINE_URL;
  const previousKey = process.env.PYTHON_ENGINE_KEY;
  const previousOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.PYTHON_ENGINE_URL = "https://preview-engine.example";
  process.env.PYTHON_ENGINE_KEY = "test-only-engine-key-that-is-long-enough";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  const requestId = "drv2-4444444444444444";
  let upstreamPosts = 0;
  globalThis.fetch = async (_url, init) => {
    if (init?.method === "POST") {
      upstreamPosts += 1;
      return Response.json({
        contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
        request_id: requestId,
        status: "RUNNING",
        stage: "MODEL_STREAMING",
      }, { status: 202 });
    }
    return Response.json({ status: "not_found" }, { status: 404 });
  };
  try {
    const app = await worker();
    const db = createDirectDb();
    assert.equal((await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context)).status, 202);
    const poll = await app.fetch(new Request(`http://localhost/api/direct-reading/v2?request_id=${requestId}`, {
      headers: { "oai-authenticated-user-email": "owner@example.com" },
    }), { ...baseEnv, DB: db }, context);
    assert.equal(poll.status, 410);
    assert.equal(db.jobs.get(requestId).state, "LOST");
    assert.equal((await app.fetch(postRequest(requestId), { ...baseEnv, DB: db }, context)).status, 409);
    assert.equal(upstreamPosts, 1);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = previousGate;
    if (previousUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = previousUrl;
    if (previousKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = previousKey;
    if (previousOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = previousOwner;
  }
});
