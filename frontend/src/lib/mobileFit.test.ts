import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { join } from "node:path";

/**
 * Source-level guards for the phone-fit work. These do NOT lay anything out, so they cannot prove a
 * page fits; the real check is `scripts/mobile-fit.mjs` (Playwright, run by hand against a running
 * site). They only stop the specific rules that keep phones from scrolling sideways being deleted by accident.
 * Run from the frontend/ folder, like the other tests here.
 */
const read = (p: string) => readFileSync(join(process.cwd(), "src", p), "utf8");

describe("phone fit guards", () => {
  it("wraps long unbroken text on phones", () => {
    const css = read("app/globals.css");
    assert.match(css, /@media \(max-width: 767px\)\s*\{\s*main,\s*main \*[^}]*overflow-wrap: anywhere/);
  });

  it("keeps touch targets at least 40px on coarse pointers", () => {
    const css = read("app/globals.css");
    assert.match(css, /@media \(max-width: 767px\) and \(pointer: coarse\)/);
    assert.match(css, /min-height: 40px/);
  });

  it("keeps the signed-in top bar compact below 380px (theme toggle is icon-only)", () => {
    const nav = read("components/Nav.tsx");
    assert.match(nav, /min-\[380px\]:w-\[4\.5rem\]/);
    assert.match(nav, /px-3 py-2\.5 min-\[360px\]:px-4/);
  });

  it("lets the landing hero column shrink instead of clipping", () => {
    assert.match(read("app/page.tsx"), /grid-cols-\[minmax\(0,1fr\)\]/);
  });

  it("declares a device-width viewport", () => {
    assert.match(read("app/layout.tsx"), /width: "device-width"|width=device-width/);
  });
});
