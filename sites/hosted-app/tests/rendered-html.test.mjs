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
  assert.match(html, /三数起卦规则/);
  assert.match(html, /\/fuxi-bagua-taiji\.svg/);
  assert.match(html, /你真正想问的问题/);
  assert.match(html, /请用清晰具体的文字说出你想弄明白的事/);
  assert.match(html, /确定性排盘 · 个性化解读/);
  assert.match(html, /用三分钟，把一件拿不准的事/);
  assert.match(html, /卦从数起，意随事明/);
  assert.match(html, /这段关系一直没有进展，我还要继续主动吗/);
  assert.match(html, /写清所问/);
  assert.match(html, /说明现实处境/);
  assert.match(html, /分清事实与未知/);
  assert.match(html, /已经确认的现实事实/);
  assert.match(html, /目前不能假设的未知项/);
  assert.match(html, /静心取数/);
  assert.match(html, /一般，可分阶段调整/);
  assert.match(html, /高不可逆，不能试错后撤回/);
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
    const first = await app.fetch(request(), { ...env, DB: db }, context);
    const second = await app.fetch(request(), { ...env, DB: db }, context);
    const third = await app.fetch(request(), { ...env, DB: db }, context);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    assert.equal(third.status, 200);
    assert.equal(upstreamCalls, 3);
    assert.equal(db.row.reserved_calls, 3);
    assert.equal(db.row.reserved_micro_usd, 0);
    assert.equal(db.row.actual_micro_usd, 80_000);
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
