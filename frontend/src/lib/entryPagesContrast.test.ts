import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { contrastRatio } from "./themeContrast.js";

/**
 * The homepage (src/app/page.tsx and src/components/home2) is light only. Every text colour it
 * uses must reach WCAG AA (4.5:1) on the cream page, white cards and the pale tints it sits on.
 */
const CREAM = "#FBF6EC";
const WHITE = "#ffffff";
const TEXT = ["#1F2328", "#3A3F47", "#4A4F57", "#0B6575", "#1E6B40", "#6B3FA0", "#9A3722", "#7A5200", "#B8432A", "#9A5A00"];
const TINTS = ["#EEF6F7", "#EDF6F0", "#FDF3DC", "#FBF0EC", "#F3EEFA", "#FFF8EC"];

describe("homepage palette (light)", () => {
  it("every text colour reaches AA on cream and white", () => {
    for (const fg of TEXT) for (const bg of [CREAM, WHITE]) {
      const r = contrastRatio(fg, bg);
      assert.ok(r >= 4.5, `${fg} on ${bg} is ${r.toFixed(2)}:1`);
    }
  });
  it("tag and stat text reaches AA on its pale tint", () => {
    for (const fg of ["#1F2328", "#0B6575", "#1E6B40", "#7A5200", "#9A3722", "#4A4F57"]) for (const bg of TINTS) {
      const r = contrastRatio(fg, bg);
      assert.ok(r >= 4.5, `${fg} on ${bg} is ${r.toFixed(2)}:1`);
    }
  });
  it("white text sits only on dark fills (coral, teal buttons; selected province)", () => {
    for (const bg of ["#B8432A", "#9A3722", "#0B6575"]) assert.ok(contrastRatio(WHITE, bg) >= 4.5, bg);
  });
});
