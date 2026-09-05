import test from "node:test";
import assert from "node:assert/strict";
import { castingViewport } from "../app/lib/casting-viewport";
import { engineReadiness, retryAfterSeconds, uncertainEngineResponse } from "../app/lib/engine-readiness";

test("keyboard opening and focusout animation preserve the casting canvas at common widths", () => {
  for (const width of [320, 360, 390, 430]) {
    const initial = castingViewport(null, width, 844, false);
    const keyboard = castingViewport(initial, width, 460, true);
    assert.equal(keyboard.height, 844);
    assert.equal(keyboard.keyboardOpen, true);
    assert.equal(castingViewport(keyboard, width, 480, false).height, 844);
    assert.deepEqual(castingViewport(keyboard, width, 844, false), initial);
    assert.equal(castingViewport(keyboard, 844, width, true).height, width);
    assert.equal(castingViewport(initial, width, 780, false).height, 780);
  }
});

test("Retry-After dates and malformed headers are bounded", async () => {
  assert.equal(retryAfterSeconds(new Response(null, { headers: { "retry-after": "60" } })), 60);
  assert.equal(retryAfterSeconds(new Response(null, { headers: { "retry-after": "junk" } })), 30);
  assert.equal(retryAfterSeconds(new Response(null, { headers: { "retry-after": "999999" } })), 3600);
  assert.equal(retryAfterSeconds(new Response(null, { headers: { "retry-after": "Sat, 05 Sep 2026 14:01:00 GMT" } }), Date.parse("2026-09-05T14:00:00Z")), 60);
  const result = uncertainEngineResponse(new Response("private gateway body", { status: 429 }));
  const body = await result.json() as Record<string, unknown>;
  assert.equal(body.submission_uncertain, true);
  assert.equal(body.retryable, false);
  assert.doesNotMatch(JSON.stringify(body), /private gateway body/);
});

test("wake-up only reads health; 429/HTML/timeout never submit or replay a model job", async () => {
  const original = globalThis.fetch;
  const enabled = process.env.GUANXIANG_ENGINE_PREFLIGHT;
  process.env.GUANXIANG_ENGINE_PREFLIGHT = "true";
  try {
    for (const reply of [new Response("Too many requests", { status: 429 }), new Response("<html>Loading</html>"), null]) {
      let calls = 0;
      globalThis.fetch = async (input, init) => {
        calls++;
        assert.equal(String(input), "https://engine.example/healthz");
        assert.notEqual(init?.method, "POST");
        if (!reply) throw new Error("timeout");
        return reply;
      };
      const response = await engineReadiness(new URL("https://engine.example/api/preview/v2/direct-reading/jobs"));
      assert.equal(response?.status, 503);
      assert.equal((await response!.json() as Record<string, unknown>).not_submitted, true);
      assert.equal(calls, 1);
    }
    globalThis.fetch = async () => Response.json({ status: "ok", service: "abalo-authoritative-engine" });
    assert.equal(await engineReadiness(new URL("https://engine.example")), null);
  } finally {
    globalThis.fetch = original;
    if (enabled === undefined) delete process.env.GUANXIANG_ENGINE_PREFLIGHT;
    else process.env.GUANXIANG_ENGINE_PREFLIGHT = enabled;
  }
});
