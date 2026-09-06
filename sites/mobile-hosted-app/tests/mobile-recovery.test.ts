import test from "node:test";
import assert from "node:assert/strict";
import { castingViewport } from "../app/lib/casting-viewport";
import { engineReadiness, retryAfterSeconds, uncertainEngineResponse } from "../app/lib/engine-readiness";
import { createServiceWarmup } from "../app/lib/client-service-warmup";
import { publicEngineHealthUrl } from "../portable/service-wakeup";
import { CONCISE_READING_PROFILE, selectReadingProfile } from "../app/lib/reading-profile";

test("speed profile requires explicit server configuration and engine support", () => {
  assert.equal(selectReadingProfile(CONCISE_READING_PROFILE, [CONCISE_READING_PROFILE]), CONCISE_READING_PROFILE);
  for (const config of [undefined, "standard", "bogus"]) {
    assert.equal(selectReadingProfile(config, [CONCISE_READING_PROFILE]), undefined);
  }
  for (const supported of [[], [null], ["other-version"]]) {
    assert.equal(selectReadingProfile(CONCISE_READING_PROFILE, supported), undefined);
  }
});

test("same health probe negotiates capabilities without another request or POST", async () => {
  const original = globalThis.fetch;
  try {
    let calls = 0;
    globalThis.fetch = async (_input, init) => {
      calls++;
      assert.notEqual(init?.method, "POST");
      return Response.json({ status: "ok", service: "abalo-authoritative-engine", direct_reading_profiles: [CONCISE_READING_PROFILE] });
    };
    let selected: string | undefined;
    assert.equal(await engineReadiness(new URL("https://engine.example"), profiles => {
      selected = selectReadingProfile(CONCISE_READING_PROFILE, profiles);
    }), null);
    assert.equal(selected, CONCISE_READING_PROFILE);
    assert.equal(calls, 1);
    globalThis.fetch = async () => Response.json({ status: "ok", service: "abalo-authoritative-engine" });
    assert.equal(await engineReadiness(new URL("https://engine.example"), profiles => {
      selected = selectReadingProfile(CONCISE_READING_PROFILE, profiles);
    }), null);
    assert.equal(selected, undefined);
  } finally { globalThis.fetch = original; }
});

test("only public credential-free Render health URLs can cross the client boundary", () => {
  assert.equal(publicEngineHealthUrl("https://example.onrender.com"), "https://example.onrender.com/healthz");
  for (const raw of [undefined, "http://example.onrender.com", "https://example.onrender.com.evil.test", "https://user:secret@example.onrender.com", "http://localhost:8080", "https://private.example", "https://example.onrender.com?key=secret", "https://example.onrender.com/private", "https://example.onrender.com:9000"]) {
    assert.equal(publicEngineHealthUrl(raw), null);
  }
});

test("concurrent user actions share one credential-free browser wake-up and never POST", async () => {
  const calls: { input: string; init?: RequestInit }[] = [];
  const warm = createServiceWarmup(async (input, init) => {
    calls.push({ input: String(input), init });
    return String(input).startsWith("/") ? Response.json({ health_url: "https://example.onrender.com/healthz" }) : new Response(null);
  });
  await Promise.all([warm(), warm(), warm()]);
  await warm();
  assert.equal(calls.length, 2);
  const health = calls[1];
  assert.equal(health.input, "https://example.onrender.com/healthz");
  assert.equal(health.init?.method, "GET");
  assert.equal(health.init?.mode, "no-cors");
  assert.equal(health.init?.credentials, "omit");
  assert.equal(health.init?.referrerPolicy, "no-referrer");
  assert.equal(health.init?.body, undefined);
  assert.equal(health.init?.headers, undefined);
});

test("untrusted config and failed wake-up cannot trigger private requests or automatic retries", async () => {
  for (const health_url of ["https://user:secret@example.onrender.com/healthz", "http://127.0.0.1/healthz", "https://example.onrender.com/healthz?secret=1"]) {
    let calls = 0;
    const warm = createServiceWarmup(async () => { calls++; return Response.json({ health_url }); });
    await warm();
    assert.equal(calls, 1);
  }
  let failures = 0;
  const warm = createServiceWarmup(async () => { failures++; throw new Error("offline"); });
  await warm(); await warm();
  assert.equal(failures, 1);
});

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
