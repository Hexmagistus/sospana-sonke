import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { canMountShowpiece, type ShowpieceSignals } from "./showpieceGate.js";

const capable: ShowpieceSignals = {
  reducedMotion: false,
  finePointer: true,
  wide: true,
  saveData: false,
  slowConnection: false,
  cores: 8,
};

describe("hero showpiece gate", () => {
  it("mounts WebGL only on a wide, fine-pointer, capable device", () => {
    assert.equal(canMountShowpiece(capable), true);
    assert.equal(canMountShowpiece({ ...capable, cores: 0 }), true);
  });

  it("keeps the painted globe for phones, motion limits, and slow links", () => {
    assert.equal(canMountShowpiece({ ...capable, wide: false }), false);
    assert.equal(canMountShowpiece({ ...capable, finePointer: false }), false);
    assert.equal(canMountShowpiece({ ...capable, reducedMotion: true }), false);
    assert.equal(canMountShowpiece({ ...capable, saveData: true }), false);
    assert.equal(canMountShowpiece({ ...capable, slowConnection: true }), false);
    assert.equal(canMountShowpiece({ ...capable, cores: 2 }), false);
  });
});

describe("dimensional motion limits", () => {
  const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");

  it("turns tilt and press movement off when the reader asks for less motion", () => {
    const reduced = css
      .split("@media (prefers-reduced-motion: reduce)")
      .find((block) => block.includes(".ss-tilt"));
    assert.ok(reduced);
    assert.match(reduced, /\.ss-press:active/);
    assert.match(reduced, /transform:\s*none !important/);
  });

  it("keeps the labour bars flat, with the length as the only measure", () => {
    const rule = css.slice(css.indexOf(".ss-rate-fill"), css.indexOf(".ss-rate-fill") + 400);
    assert.equal(rule.includes("perspective"), false);
    assert.equal(rule.includes("rotateX"), false);
    assert.match(rule, /height:\s*100%/);
  });
});
