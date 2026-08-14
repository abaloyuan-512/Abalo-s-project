import fs from "node:fs";
import { pathToFileURL } from "node:url";

const inputPath = process.argv[2];
const distPath = process.argv[3];
if (!inputPath || !distPath) throw new Error("V002_PROBE_ARGUMENTS");
const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const jobs = new Map();
const db = {
  prepare(sql) {
    let values = [];
    return {
      bind(...next) { values = next; return this; },
      async run() {
        if (sql.includes("CREATE TABLE IF NOT EXISTS direct_reading_preview_jobs")) return { meta: { changes: 0 } };
        if (sql.includes("INSERT OR IGNORE INTO direct_reading_preview_jobs")) {
          const [requestId, digest, promptVersion, createdAt, updatedAt] = values;
          if (jobs.has(requestId)) return { meta: { changes: 0 } };
          jobs.set(requestId, { payload_sha256: digest, prompt_version: promptVersion, state: "RUNNING", result_status: null, created_at: createdAt, updated_at: updatedAt });
          return { meta: { changes: 1 } };
        }
        if (sql.includes("SET state = 'FINALIZED'")) {
          const [status, updatedAt, requestId] = values;
          const job = jobs.get(requestId);
          if (!job || job.state !== "RUNNING") return { meta: { changes: 0 } };
          Object.assign(job, { state: "FINALIZED", result_status: status, updated_at: updatedAt });
          return { meta: { changes: 1 } };
        }
        throw new Error("V002_UNEXPECTED_SQL");
      },
      async first() {
        const row = jobs.get(values[0]);
        return row ? { ...row } : null;
      },
    };
  },
};

const originalFetch = globalThis.fetch;
const originalGate = process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED;
const originalOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL;
const originalUrl = process.env.PYTHON_ENGINE_URL;
const originalKey = process.env.PYTHON_ENGINE_KEY;
process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
process.env.PYTHON_ENGINE_URL = "https://fixture.invalid";
process.env.PYTHON_ENGINE_KEY = "fixture-only-not-a-real-key";
let upstreamCalls = 0;
globalThis.fetch = async () => {
  upstreamCalls += 1;
  return Response.json(input.upstream, { status: 200 });
};
try {
  const url = pathToFileURL(distPath);
  url.searchParams.set("v002", `${process.pid}-${Date.now()}`);
  const app = (await import(url.href)).default;
  const response = await app.fetch(new Request("http://localhost/api/direct-reading/v2", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "oai-authenticated-user-email": "owner@example.com",
    },
    body: JSON.stringify(input.request),
  }), { ASSETS: { fetch: async () => new Response("not found", { status: 404 }) }, DB: db }, { waitUntil() {}, passThroughOnException() {} });
  const body = await response.json();
  process.stdout.write(JSON.stringify({
    http_status: response.status,
    status: body.status,
    error_code: body.error_code,
    direct_reading_null: body.direct_reading === null,
    presentation_null: body.product_presentation === null,
    direct_high_null: body.direct_high === null,
    upstream_calls: upstreamCalls,
  }));
} finally {
  globalThis.fetch = originalFetch;
  if (originalGate === undefined) delete process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED; else process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = originalGate;
  if (originalOwner === undefined) delete process.env.ABALO_PREVIEW_OWNER_EMAIL; else process.env.ABALO_PREVIEW_OWNER_EMAIL = originalOwner;
  if (originalUrl === undefined) delete process.env.PYTHON_ENGINE_URL; else process.env.PYTHON_ENGINE_URL = originalUrl;
  if (originalKey === undefined) delete process.env.PYTHON_ENGINE_KEY; else process.env.PYTHON_ENGINE_KEY = originalKey;
}
