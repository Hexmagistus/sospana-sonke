import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { contrastRatio } from "./themeContrast.js";

/**
 * The landing page ("Get started") paints with its own palette `C` and a few literal colours
 * instead of the theme tokens. These tests read that palette from the source and check every
 * text/background pair the page really uses, so a bright brand colour can never again end up as
 * text on cream/white (that is what made the page unreadable), and so white text only ever sits
 * on dark fills or dark scrims. Run from frontend/ (as CI does).
 */
const src = readFileSync(resolve(process.cwd(), "src/app/page.tsx"), "utf8");
const palette = /const C = \{([\s\S]*?)\n\};/.exec(src);
assert.ok(palette, "landing page should define its colour palette C");
const C: Record<string, string> = {};
for (const m of palette[1].matchAll(/(\w+):\s*"(#[0-9a-fA-F]{6})"/g)) C[m[1]] = m[2];

const WHITE = "#ffffff";
const CREAM = C.cream;
const need = (k: string) => {
  assert.ok(C[k], `palette key ${k}`);
  return C[k];
};

function check(label: string, pairs: [string, string, number, string?][]) {
  for (const [fg, bg, min, under] of pairs) {
    const r = contrastRatio(fg, bg, under);
    assert.ok(r >= min, `${label}: ${fg} on ${bg} is ${r.toFixed(2)}:1, needs >= ${min}:1`);
  }
}

describe("landing page palette (light canvas)", () => {
  it("headings and body use navy / dark text on cream and white at AAA", () => {
    check("navy", [[need("navy"), CREAM, 7], [need("navy"), WHITE, 7], ["#0b1220", CREAM, 7], ["#0b1220", WHITE, 7]]);
  });

  it("every dark twin used as TEXT reaches AA on white, cream and its own pale chip tint", () => {
    for (const k of ["goldText", "tealText", "greenText", "skyText", "plumText", "sunText", "redText"]) {
      const c = need(k);
      check(k, [[c, WHITE, 4.5], [c, CREAM, 4.5]]);
    }
    // value chips are the colour at ~9% alpha over the page: text darkOf(colour) on that tint
    const chip: [string, string][] = [
      [C.redText, C.red], [C.sunText, C.sun], [C.goldText, C.gold], [C.greenText, C.green],
      [C.tealText, C.teal], [C.skyText, C.sky], [C.plumText, C.plum],
    ];
    for (const [text, fill] of chip) {
      const n = parseInt(fill.slice(1), 16);
      const tint = `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},0.0941)`;
      check(`chip ${fill}`, [[text, tint, 4.5, WHITE]]);
    }
  });

  it("white text only on dark fills: buttons, step badges, Live badge, photo captions", () => {
    check("white fills", [
      [WHITE, need("navy"), 7],
      [WHITE, need("redText"), 4.5],
      [WHITE, need("sunText"), 4.5],
      [WHITE, need("greenText"), 4.5],
      [WHITE, need("skyText"), 4.5],
      // photo captions sit on an 85% navy panel, worst case over a white photo
      [WHITE, "rgba(7,21,40,0.85)", 7, WHITE],
    ]);
  });

  it("the closing call to action uses near-black text on its light gold gradient", () => {
    for (const stop of ["#ffe08a", "#f5b301", "#ffc24d"]) check("cta", [["#1a0f00", stop, 7]]);
    assert.ok(src.includes("linear-gradient(120deg,#ffe08a,#f5b301 55%,#ffc24d)"), "CTA gradient should stay the light gold one");
    assert.ok(!/linear-gradient\(120deg,\$\{C\.red\}/.test(src), "do not put the red/orange gradient back behind dark text");
  });

  it("no bright brand colour is used as text colour on the page", () => {
    const bad = /color:\s*C\.(mint|teal|sky|plum|sun|red|green|amber|gold)\b/.exec(src);
    assert.equal(bad, null, `bright colour as text: ${bad?.[0]}`);
    assert.ok(!/text-gray-[1-5]00/.test(src), "light grays are too faint on cream");
  });
});
