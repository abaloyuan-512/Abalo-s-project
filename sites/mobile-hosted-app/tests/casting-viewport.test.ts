import test from "node:test";
import assert from "node:assert/strict";
import { castingViewport } from "../app/lib/casting-viewport";

test("mobile keyboard does not move the casting canvas or submit action", () => {
  for (const width of [320, 360, 390, 430]) {
    const initial = castingViewport(null, width, 844, false);
    const keyboardOpen = castingViewport(initial, width, 460, true);

    assert.equal(keyboardOpen.height, 844);
    assert.equal(keyboardOpen.keyboardOpen, true);
    assert.equal(castingViewport(keyboardOpen, width, 480, false).height, 844);
    assert.deepEqual(castingViewport(keyboardOpen, width, 844, false), initial);
  }
});

test("real device rotation and ordinary height changes still recalculate the canvas", () => {
  const portrait = castingViewport(null, 390, 844, false);

  assert.deepEqual(castingViewport(portrait, 844, 390, true), {
    width: 844,
    height: 390,
    keyboardOpen: false,
  });
  assert.deepEqual(castingViewport(portrait, 390, 780, false), {
    width: 390,
    height: 780,
    keyboardOpen: false,
  });
});
