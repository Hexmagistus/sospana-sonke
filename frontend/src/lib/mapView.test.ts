import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  MAX_ZOOM_VIEW_W, WORLD_H, WORLD_VIEW, WORLD_W, clampView, keyAction, panView, wheelFactor, zoomLevel, zoomView,
} from "./mapView.js";

describe("map pan and zoom maths", () => {
  it("zooming in keeps the point under the cursor fixed", () => {
    const v = zoomView(WORLD_VIEW, 2, 0.25, 0.5);
    const before = WORLD_VIEW.x + WORLD_VIEW.w * 0.25;
    const after = v.x + v.w * 0.25;
    assert.ok(Math.abs(before - after) < 1e-6);
    assert.equal(v.w, WORLD_W / 2);
    assert.equal(zoomLevel(v), 2);
  });

  it("zoom is limited: never wider than the world, never closer than the max zoom", () => {
    assert.deepEqual(zoomView(WORLD_VIEW, 0.2), WORLD_VIEW);
    let v = WORLD_VIEW;
    for (let i = 0; i < 30; i++) v = zoomView(v, 1.5, 0.5, 0.5);
    assert.equal(v.w, MAX_ZOOM_VIEW_W);
  });

  it("panning cannot leave the world", () => {
    const zoomed = zoomView(WORLD_VIEW, 4);
    const left = panView(zoomed, -5000, -5000);
    assert.equal(left.x, 0);
    assert.equal(left.y, 0);
    const right = panView(zoomed, 5000, 5000);
    assert.equal(right.x + right.w, WORLD_W);
    assert.ok(Math.abs(right.y + right.h - WORLD_H) < 1e-6);
  });

  it("panning the whole world does nothing (it already fits)", () => {
    assert.deepEqual(panView(WORLD_VIEW, 100, 100), WORLD_VIEW);
  });

  it("clampView keeps the map's aspect ratio", () => {
    const v = clampView({ x: -10, y: -10, w: 300, h: 10 });
    assert.ok(Math.abs(v.w / v.h - WORLD_W / WORLD_H) < 1e-9);
    assert.equal(v.x, 0);
  });

  it("keyboard: arrows pan, + / - zoom, 0 resets, other keys are ignored", () => {
    assert.deepEqual(keyAction("ArrowLeft"), { kind: "pan", dx: -0.15, dy: 0 });
    assert.deepEqual(keyAction("ArrowDown"), { kind: "pan", dx: 0, dy: 0.15 });
    const plus = keyAction("+");
    const minus = keyAction("-");
    assert.ok(plus?.kind === "zoom" && plus.factor > 1);
    assert.ok(minus?.kind === "zoom" && minus.factor < 1);
    assert.equal(keyAction("=")?.kind, "zoom");
    assert.equal(keyAction("0")?.kind, "reset");
    assert.equal(keyAction("a"), null);
    assert.equal(keyAction("Tab"), null);
  });

  it("wheel up zooms in, wheel down zooms out, and one big flick is capped", () => {
    assert.ok(wheelFactor(-100) > 1);
    assert.ok(wheelFactor(100) < 1);
    assert.equal(wheelFactor(-100000), wheelFactor(-120));
  });
});
