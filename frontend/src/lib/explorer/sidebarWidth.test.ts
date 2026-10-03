import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  SIDEBAR_BIG_STEP, SIDEBAR_DEFAULT, SIDEBAR_MAX, SIDEBAR_MIN, SIDEBAR_STEP,
  clampSidebarWidth, parseStoredWidth, widthAfterKey, widthFromPointer,
} from "./sidebarWidth";

describe("sidebar width", () => {
  it("clamps to the min and max", () => {
    assert.equal(clampSidebarWidth(10), SIDEBAR_MIN);
    assert.equal(clampSidebarWidth(9999), SIDEBAR_MAX);
    assert.equal(clampSidebarWidth(300.4), 300);
    assert.equal(clampSidebarWidth(NaN), SIDEBAR_DEFAULT);
  });

  it("default sits between min and max", () => {
    assert.ok(SIDEBAR_MIN < SIDEBAR_DEFAULT && SIDEBAR_DEFAULT < SIDEBAR_MAX);
  });

  it("stored values: missing, junk and out-of-range fall back or clamp", () => {
    assert.equal(parseStoredWidth(null), SIDEBAR_DEFAULT);
    assert.equal(parseStoredWidth(""), SIDEBAR_DEFAULT);
    assert.equal(parseStoredWidth("wide"), SIDEBAR_DEFAULT);
    assert.equal(parseStoredWidth("360"), 360);
    assert.equal(parseStoredWidth("5000"), SIDEBAR_MAX);
    assert.equal(parseStoredWidth("-4"), SIDEBAR_MIN);
  });

  it("arrow keys move by a step, Shift by a big step, and stay inside the range", () => {
    assert.equal(widthAfterKey(300, "ArrowRight"), 300 + SIDEBAR_STEP);
    assert.equal(widthAfterKey(300, "ArrowLeft"), 300 - SIDEBAR_STEP);
    assert.equal(widthAfterKey(300, "ArrowRight", true), 300 + SIDEBAR_BIG_STEP);
    assert.equal(widthAfterKey(SIDEBAR_MAX, "ArrowRight"), SIDEBAR_MAX);
    assert.equal(widthAfterKey(SIDEBAR_MIN, "ArrowLeft"), SIDEBAR_MIN);
  });

  it("Home, End and Enter jump to min, max and default; other keys are ignored", () => {
    assert.equal(widthAfterKey(300, "Home"), SIDEBAR_MIN);
    assert.equal(widthAfterKey(300, "End"), SIDEBAR_MAX);
    assert.equal(widthAfterKey(400, "Enter"), SIDEBAR_DEFAULT);
    assert.equal(widthAfterKey(300, "a"), null);
    assert.equal(widthAfterKey(300, "ArrowUp"), null);
  });

  it("dragging: width is the pointer offset from the split's left edge, clamped", () => {
    assert.equal(widthFromPointer(500, 100), 400);
    assert.equal(widthFromPointer(120, 100), SIDEBAR_MIN);
    assert.equal(widthFromPointer(2000, 100), SIDEBAR_MAX);
  });
});
