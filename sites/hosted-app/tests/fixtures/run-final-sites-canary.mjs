import { pathToFileURL } from "node:url";


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
          const row = jobs.get(values[0]);
          return row ? { ...row } : null;
        },
      };
    },
  };
}


async function main() {
  const [distPath, portText, engineKey, requestId, question, numbersJson] = process.argv.slice(2);
  const port = Number(portText);
  if (!distPath || !Number.isInteger(port) || !engineKey || !requestId || !question) throw new Error("invalid arguments");
  process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true";
  process.env.ABALO_PREVIEW_OWNER_EMAIL = "owner@example.com";
  process.env.PYTHON_ENGINE_URL = `http://127.0.0.1:${port}`;
  process.env.PYTHON_ENGINE_KEY = engineKey;
  const nativeFetch = globalThis.fetch;
  let upstreamPostCount = 0;
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
    if (url.hostname === "127.0.0.1" && url.port === String(port) && init?.method === "POST") {
      upstreamPostCount += 1;
    }
    return nativeFetch(input, init);
  };
  const moduleUrl = pathToFileURL(distPath);
  moduleUrl.searchParams.set("final-canary", `${Date.now()}`);
  const app = (await import(moduleUrl.href)).default;
  const db = createDirectDb();
  const env = { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) }, DB: db };
  const context = { waitUntil() {}, passThroughOnException() {} };
  const owner = { "oai-authenticated-user-email": "owner@example.com" };
  const submitted = await app.fetch(new Request("http://localhost/api/direct-reading/v2", {
    method: "POST",
    headers: { ...owner, "Content-Type": "application/json" },
    body: JSON.stringify({
      contract_version: "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1",
      request_id: requestId,
      question_text: question,
      numbers: JSON.parse(numbersJson),
    }),
  }), env, context);
  const initial = await submitted.json();
  let terminalStatus = submitted.status;
  let terminal = initial;
  const stages = [initial.stage].filter(Boolean);
  const deadline = Date.now() + 210_000;
  while (terminalStatus === 202 && Date.now() < deadline) {
    await new Promise((resolveWait) => setTimeout(resolveWait, 250));
    const polled = await app.fetch(new Request(`http://localhost/api/direct-reading/v2?request_id=${encodeURIComponent(requestId)}`, { headers: owner }), env, context);
    terminalStatus = polled.status;
    terminal = await polled.json();
    if (terminal.stage && stages.at(-1) !== terminal.stage) stages.push(terminal.stage);
  }
  process.stdout.write(JSON.stringify({
    submitted_http_status: submitted.status,
    initial,
    terminal_http_status: terminalStatus,
    terminal,
    stages,
    persisted_state: db.jobs.get(requestId)?.state ?? null,
    upstream_post_count: upstreamPostCount,
  }));
}


await main();
