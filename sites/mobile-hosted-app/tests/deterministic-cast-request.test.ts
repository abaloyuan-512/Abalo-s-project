import assert from "node:assert/strict";
import test from "node:test";

import { requestDeterministicCast } from "../app/deterministic-cast-request";

test("deterministic cast retries only transient 503 responses and then returns success", async () => {
  const statuses = [503, 503, 200];
  const sleeps: number[] = [];
  const retries: number[] = [];
  let calls = 0;

  const result = await requestDeterministicCast<{ status: string }>({
    fetchResult: async () => {
      const status = statuses[calls++];
      return Response.json({ status: status === 200 ? "SUCCESS" : "WAKING" }, { status });
    },
    sleep: async (milliseconds) => { sleeps.push(milliseconds); },
    onRetry: (attempt) => { retries.push(attempt); },
  });

  assert.equal(calls, 3);
  assert.equal(result.request.status, 200);
  assert.equal(result.payload.status, "SUCCESS");
  assert.deepEqual(sleeps, [1_500, 1_500]);
  assert.deepEqual(retries, [1, 2]);
});

test("deterministic cast does not retry a non-transient failure", async () => {
  let calls = 0;
  const result = await requestDeterministicCast<{ error: string }>({
    fetchResult: async () => {
      calls += 1;
      return Response.json({ error: "invalid request" }, { status: 400 });
    },
    sleep: async () => undefined,
  });

  assert.equal(calls, 1);
  assert.equal(result.request.status, 400);
  assert.equal(result.payload.error, "invalid request");
});
