import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { contrastRatio, readTokens } from "./themeContrast.js";

/**
 * The platform is bright by default. These tests read the real tokens from
 * src/app/globals.css (and the navy/gold accents from tailwind.config.ts) and fail if a
 * pair drops below WCAG AA (4.5:1), or below AAA (7:1) for body text.
 * Run from the frontend/ directory (as CI does).
 */
const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");
const tw = readFileSync(resolve(process.cwd(), "tailwind.config.ts"), "utf8");

const light = readTokens(css, ":root");
const dark = readTokens(css, ':root[data-theme="dark"]');
const mapLight = readTokens(css, ".ss-map");
const mapDark = readTokens(css, ':root[data-theme="dark"] .ss-map');

function twColor(name: "navy" | "gold"): string {
  const m = new RegExp(`${name}:\\s*\\{\\s*DEFAULT:\\s*"(#[0-9a-fA-F]{6})"`).exec(tw);
  assert.ok(m, `tailwind.config.ts should define ${name}.DEFAULT`);
  return m[1];
}
const NAVY = twColor("navy");
const GOLD = twColor("gold");
const WHITE = "#ffffff";

type Pair = { name: string; fg: string; bg: string; under?: string; min: number };

function check(pairs: Pair[]) {
  for (const p of pairs) {
    const ratio = contrastRatio(p.fg, p.bg, p.under);
    assert.ok(ratio >= p.min, `${p.name}: ${p.fg} on ${p.bg} is ${ratio.toFixed(2)}:1, needs >= ${p.min}:1`);
  }
}

function tokensOf(t: Record<string, string>, name: string): string {
  const v = t[name];
  assert.ok(v, `missing token ${name}`);
  return v;
}

describe("light theme (the default)", () => {
  const t = (n: string) => tokensOf(light, n);
  const bg = t("--ss-bg");
  const surface = t("--ss-surface");

  it("is actually bright: page and surface backgrounds are near-white", () => {
    assert.ok(contrastRatio(bg, "#000000") > 15, "page background must be very light");
    assert.ok(contrastRatio(surface, "#000000") > 15, "surface must be very light");
    assert.ok(contrastRatio(t("--ss-glass"), "#000000", bg) > 15, "glass panels must be very light");
    assert.ok(contrastRatio(t("--ss-panel"), "#000000", bg) > 15, "map-overlay panels must be very light");
  });

  it("body text reaches AAA (7:1) on every light surface", () => {
    const surfaces: [string, string, string?][] = [
      ["page", bg],
      ["surface", surface],
      ["elevated", t("--ss-surface-elevated")],
      ["glass over page", t("--ss-glass"), bg],
      ["panel over page", t("--ss-panel"), bg],
      ["gold wash over surface", t("--ss-primary-soft"), surface],
      ["strong gold wash over surface", t("--ss-primary-soft-strong"), surface],
    ];
    check(
      surfaces.flatMap(([n, s, under]) => [
        { name: `--ss-text on ${n}`, fg: t("--ss-text"), bg: s, under, min: 7 },
        { name: `--ss-text-muted on ${n}`, fg: t("--ss-text-muted"), bg: s, under, min: 7 },
      ]),
    );
  });

  it("accent text colours reach AA (4.5:1) on page and surface", () => {
    const accents = ["--ss-primary-text", "--ss-success", "--ss-danger", "--ss-warning", "--ss-tech"];
    check(
      accents.flatMap((a) => [
        { name: `${a} on surface`, fg: t(a), bg: surface, min: 4.5 },
        { name: `${a} on page`, fg: t(a), bg: bg, min: 4.5 },
      ]),
    );
  });

  it("gold-as-text is dark gold (AAA on white), never the bright fill gold", () => {
    check([{ name: "--ss-primary-text on surface", fg: t("--ss-primary-text"), bg: surface, min: 7 }]);
    assert.ok(contrastRatio(GOLD, surface) < 4.5, "bright gold is a fill/border colour only, not text on white");
  });

  it("navy headings/links and gold buttons are legible", () => {
    check([
      { name: "navy on surface (headings, links)", fg: NAVY, bg: surface, min: 7 },
      { name: "navy on page", fg: NAVY, bg: bg, min: 7 },
      { name: "navy text on gold button", fg: NAVY, bg: GOLD, min: 7 },
      { name: "white on navy button", fg: WHITE, bg: NAVY, min: 7 },
      { name: "text on gold button", fg: t("--ss-text"), bg: GOLD, min: 7 },
      { name: "white on red-700 badge", fg: WHITE, bg: "#b91c1c", min: 4.5 },
      { name: "white on teal chat bubble", fg: WHITE, bg: "#0b5e58", min: 7 },
    ]);
  });

  it("borders are visible against surfaces (non-text 3:1 not required, but at least faint)", () => {
    assert.ok(contrastRatio(t("--ss-border"), surface, surface) >= 1.3);
  });
});

describe("dark theme (optional)", () => {
  const t = (n: string) => tokensOf(dark, n);
  const bg = t("--ss-bg");
  const surface = t("--ss-surface");

  it("body text reaches AAA and accents reach AA", () => {
    const surfaces: [string, string, string?][] = [
      ["page", bg],
      ["surface", surface],
      ["elevated", t("--ss-surface-elevated")],
      ["panel over page", t("--ss-panel"), bg],
    ];
    check([
      ...surfaces.flatMap(([n, s, under]) => [
        { name: `dark --ss-text on ${n}`, fg: t("--ss-text"), bg: s, under, min: 7 },
        { name: `dark --ss-text-muted on ${n}`, fg: t("--ss-text-muted"), bg: s, under, min: 7 },
      ]),
      ...["--ss-primary-text", "--ss-success", "--ss-danger", "--ss-warning", "--ss-tech"].flatMap((a) => [
        { name: `dark ${a} on surface`, fg: t(a), bg: surface, min: 4.5 },
        { name: `dark ${a} on page`, fg: t(a), bg: bg, min: 4.5 },
      ]),
      { name: "navy text on gold button (dark mode)", fg: NAVY, bg: GOLD, min: 7 },
    ]);
  });
});

describe("explorer map", () => {
  it("light map: land is light and the selected-country outline is clearly visible", () => {
    const land = tokensOf(mapLight, "--map-land");
    const ocean = tokensOf(mapLight, "--map-ocean");
    check([
      { name: "ocean vs black (light)", fg: "#000000", bg: ocean, min: 15 },
      { name: "land vs black (light)", fg: "#000000", bg: land, min: 15 },
      { name: "selected outline on land", fg: tokensOf(mapLight, "--map-select-stroke"), bg: land, min: 7 },
      { name: "selected outline on gold fill", fg: tokensOf(mapLight, "--map-select-stroke"), bg: GOLD, min: 7 },
      { name: "selected outline on ocean", fg: tokensOf(mapLight, "--map-select-stroke"), bg: ocean, min: 7 },
      { name: "country borders on land (non-text 3:1)", fg: tokensOf(mapLight, "--map-land-stroke"), bg: land, min: 3 },
      { name: "pin on land", fg: tokensOf(mapLight, "--map-pin"), bg: land, min: 7 },
      { name: "hover label text", fg: tokensOf(light, "--ss-text"), bg: tokensOf(mapLight, "--map-label-bg"), under: land, min: 7 },
    ]);
  });

  it("dark map option keeps its outline visible", () => {
    const land = tokensOf(mapDark, "--map-land");
    check([{ name: "dark selected outline on land", fg: tokensOf(mapDark, "--map-select-stroke"), bg: land, min: 7 }]);
  });
});

describe("contrastRatio helper", () => {
  it("matches the WCAG reference values", () => {
    assert.equal(Math.round(contrastRatio("#000000", "#ffffff")), 21);
    assert.equal(contrastRatio("#ffffff", "#ffffff"), 1);
    assert.ok(Math.abs(contrastRatio("#777777", "#ffffff") - 4.48) < 0.02);
  });

  it("composites translucent backgrounds over what is underneath", () => {
    assert.ok(contrastRatio("#0b1220", "rgba(255,255,255,0.5)", "#000000") < 8);
    assert.ok(contrastRatio("#0b1220", "rgba(255,255,255,0.95)", "#ffffff") > 17);
  });
});
