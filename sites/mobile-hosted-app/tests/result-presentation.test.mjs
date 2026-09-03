import assert from "node:assert/strict";
import test from "node:test";

import { resultSectionVisibility } from "../app/result-presentation.mjs";

test("personalized reading is the only primary answer", () => {
  assert.deepEqual(resultSectionVisibility(true), {
    showGenericSignals: false,
    showGenericWhy: false,
    showGenericGuidance: false,
  });
});

test("generic report remains the fallback when personalization is absent", () => {
  assert.deepEqual(resultSectionVisibility(false), {
    showGenericSignals: true,
    showGenericWhy: true,
    showGenericGuidance: true,
  });
});
