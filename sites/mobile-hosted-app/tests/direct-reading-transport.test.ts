import test from "node:test";
import assert from "node:assert/strict";
import { directReadingProgress, queryDirectReading, submitDirectReading } from "../app/lib/direct-reading-transport";

function clock() {
  let time = 0;
  const delays: number[] = [];
  return { now: () => time, wait: async (ms: number) => { delays.push(ms); time += ms; }, delays,
    advance: (ms: number) => { time += ms; } };
}

test("cold start rejected before dispatch eventually accepts the SAME payload exactly once", async () => {
  const timing = clock();
  const bodies: unknown[] = [];
  let modelJobs = 0;
  const body = JSON.stringify({ request_id: "drv2-123", numbers: [3, 77, 46] });
  const response = await submitDirectReading(body, { ...timing, request: async (_url, init) => {
    bodies.push(init?.body);
    timing.advance(25_000);
    if (bodies.length < 3) return Response.json({ error_code: "ENGINE_WAKING", not_submitted: true },
      { status: 503, headers: { "Retry-After": "3" } });
    modelJobs++;
    return Response.json({ status: "RUNNING", stage: "CAST_READY" }, { status: 202 });
  } });
  assert.equal(response.status, 202);
  assert.deepEqual(bodies, [body, body, body]);
  assert.equal(modelJobs, 1);
  assert.deepEqual(timing.delays, [3000, 3000]);
});

test("ambiguous submits, provider errors, quota and rate limits never replay a POST", async () => {
  const replies = [
    () => { throw new Error("connection lost after dispatch"); },
    () => new Response("gateway html", { status: 502 }),
    () => Response.json({ submission_uncertain: true }, { status: 503 }),
    () => Response.json({ error_code: "ENGINE_RATE_LIMITED" }, { status: 503 }),
    () => Response.json({ not_submitted: true }, { status: 429 }),
    () => Response.json({ error_code: "ENGINE_WAKING" }, { status: 503 }),
    () => Response.json({ status: "UNAVAILABLE", error_code: "PROVIDER_TIMEOUT" }),
  ];
  for (const reply of replies) {
    let calls = 0;
    const timing = clock();
    await submitDirectReading("same", { ...timing, request: async () => { calls++; return reply(); } }).catch(() => undefined);
    assert.equal(calls, 1);
    assert.deepEqual(timing.delays, []);
  }
});

test("persistent cold start is bounded and Retry-After is not shortened", async () => {
  const timing = clock();
  let calls = 0;
  const response = await submitDirectReading("same", { ...timing, request: async () => {
    calls++; timing.advance(25_000);
    return Response.json({ not_submitted: true, error_code: "ENGINE_WAKING" },
      { status: 503, headers: { "Retry-After": "60" } });
  } });
  assert.equal(response.status, 503);
  assert.equal(calls, 2);
  assert.deepEqual(timing.delays, [60000]);
});

test("explicit health-probe rate limit waits before retrying an unsubmitted task", async () => {
  const timing = clock();
  let calls = 0;
  const response = await submitDirectReading("same", { ...timing, request: async () => {
    calls++;
    return calls === 1 ? Response.json({ not_submitted: true, error_code: "ENGINE_RATE_LIMITED" },
      { status: 503, headers: { "Retry-After": "30" } }) : Response.json({ status: "RUNNING" }, { status: 202 });
  } });
  assert.equal(response.status, 202);
  assert.deepEqual(timing.delays, [30000]);
  assert.equal(calls, 2);
});

test("temporary offline, HTML gateway and 503 recover through GET of original ID only", async () => {
  const timing = clock();
  let calls = 0;
  const result = await queryDirectReading("drv2-original", { ...timing, request: async (url, init) => {
    assert.equal(String(url), "/api/direct-reading/v2?request_id=drv2-original");
    assert.equal(init?.body, undefined);
    assert.notEqual(init?.method, "POST");
    calls++;
    if (calls === 1) throw new Error("offline");
    if (calls === 2) return new Response("<html>gateway</html>");
    if (calls === 3) return Response.json({ error: "busy" }, { status: 503, headers: { "Retry-After": "10" } });
    return Response.json({ status: "SUCCESS" });
  } });
  assert.equal((await result.json() as { status: string }).status, "SUCCESS");
  assert.deepEqual(timing.delays, [3000, 6000, 10000]);
});

test("persistent GET failure offers recovery after bounded attempts, never generates", async () => {
  const timing = clock();
  let calls = 0;
  await assert.rejects(queryDirectReading("same", { ...timing, request: async () => {
    calls++; throw new Error("offline");
  } }), /offline/);
  assert.equal(calls, 4);
  assert.deepEqual(timing.delays, [3000, 6000, 12000]);
});

test("terminal failures and long Retry-After are returned without retries", async () => {
  for (const reply of [Response.json({ terminal: true }, { status: 503 }),
    Response.json({ error: "gone" }, { status: 410 }),
    Response.json({ error: "limited" }, { status: 429, headers: { "Retry-After": "3600" } })]) {
    let calls = 0;
    const timing = clock();
    await queryDirectReading("same", { ...timing, request: async () => { calls++; return reply; } });
    assert.equal(calls, 1);
    assert.deepEqual(timing.delays, []);
  }
});

test("changing active task stops further network calls", async () => {
  let active = true;
  let calls = 0;
  await assert.rejects(queryDirectReading("old", { active: () => active,
    wait: async () => { active = false; }, request: async () => { calls++; throw new Error("offline"); },
  }), /Task changed/);
  assert.equal(calls, 1);
});

test("backend stages communicate truthful progress without internal model terms", () => {
  assert.match(directReadingProgress("MODEL_STREAMING"), /撰写/);
  assert.match(directReadingProgress("VALIDATING"), /核对/);
  assert.match(directReadingProgress(undefined), /生成/);
});
