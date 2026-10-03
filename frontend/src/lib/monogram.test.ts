import assert from "node:assert/strict";
import { test } from "node:test";
import {
  MONOGRAM_PALETTE,
  contrastRatio,
  hashString,
  monogramColours,
  monogramInitials,
} from "./monogram";

test("initials skip filler words and keep two letters", () => {
  assert.equal(monogramInitials("Standard Bank Group Ltd"), "SB");
  assert.equal(monogramInitials("The Bidvest Group Limited"), "BG");
  assert.equal(monogramInitials("Eskom"), "E");
  assert.equal(monogramInitials("Transnet SOC Ltd"), "T");
  assert.equal(monogramInitials("Anglo American (AMS)"), "AA");
});

test("initials keep African-language and accented letters", () => {
  assert.equal(monogramInitials("Ékhaya Sonke"), "ÉS");
  assert.equal(monogramInitials("Ìbàdàn Ọlọ́run"), "ÌỌ");
  assert.equal(monogramInitials("ǂKhomani Trust"), "ǂT");
});

test("empty or symbol-only names never produce a blank badge", () => {
  assert.equal(monogramInitials(""), "?");
  assert.equal(monogramInitials("!!! ???"), "?");
  assert.equal(monogramInitials("Pty Ltd"), "PL");
});

test("colours are deterministic per key and spread across the palette", () => {
  assert.deepEqual(monogramColours("abc-123"), monogramColours("abc-123"));
  assert.equal(hashString("Sasol"), hashString("Sasol"));
  const used = new Set<string>();
  for (let i = 0; i < 400; i++) used.add(monogramColours(`company-${i}`).bg + monogramColours(`company-${i}`).fg);
  assert.ok(used.size >= MONOGRAM_PALETTE.length - 1, `only ${used.size} combos used`);
});

test("every palette pair meets WCAG AA (4.5:1) for the initials", () => {
  for (const p of MONOGRAM_PALETTE) {
    const ratio = contrastRatio(p.bg, p.fg);
    assert.ok(ratio >= 4.5, `${p.bg} on ${p.fg} is ${ratio.toFixed(2)}`);
  }
});
