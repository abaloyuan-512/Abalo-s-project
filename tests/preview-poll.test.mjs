import assert from "node:assert/strict";
import test from "node:test";

import { pollPreviewTask, PreviewPollError } from "../app/preview/preview-poll.ts";

function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() { return payload; },
  };
}

test("PREVIEW_FAILED is terminal after one poll", async () => {
  let calls = 0;
  await assert.rejects(
    pollPreviewTask("beta-failed", {
      fetchResult: async () => {
        calls += 1;
        return response(200, { status: "PREVIEW_FAILED", error: "未通过安全或质量检查。" });
      },
      sleep: async () => {},
    }),
    (error) => error instanceof PreviewPollError && error.terminal && error.requestId === "beta-failed",
  );
  assert.equal(calls, 1);
});

test("a restored request also stops on PREVIEW_FAILED", async () => {
  let calls = 0;
  await assert.rejects(
    pollPreviewTask("beta-restored", {
      fetchResult: async () => {
        calls += 1;
        return response(200, { status: "PREVIEW_FAILED", error: "本次生成失败。" });
      },
      sleep: async () => {},
    }),
    /本次生成失败/,
  );
  assert.equal(calls, 1);
});

test("only explicit running responses continue polling", async () => {
  const responses = [
    response(202, { status: "RUNNING" }),
    response(200, { status: "RUNNING" }),
    response(200, { status: "SUCCESS", personalized_reading: { core_judgment: "可以继续" } }),
  ];
  let calls = 0;
  const result = await pollPreviewTask("beta-success", {
    fetchResult: async () => responses[calls++],
    sleep: async () => {},
  });
  assert.equal(calls, 3);
  assert.equal(result.status, "SUCCESS");
});

test("network errors stop loading but preserve the task for refresh recovery", async () => {
  await assert.rejects(
    pollPreviewTask("beta-network", {
      fetchResult: async () => { throw new TypeError("Failed to fetch"); },
      sleep: async () => {},
    }),
    (error) => error instanceof PreviewPollError && !error.terminal,
  );
});
