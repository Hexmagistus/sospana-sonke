// Deterministic monogram badge for companies without a stored icon.
//
// Pure functions (no React, no network) so the same company always gets the same
// badge on every device and the logic can be unit-tested. Palette = the Sospana
// Sonke brand: navy and gold. Every pair below is >= 4.5:1 (WCAG AA) for the
// initials; the test file checks that with the real WCAG formula.

export interface MonogramColours {
  bg: string;
  fg: string;
  ring: string;
}

export const MONOGRAM_PALETTE: readonly MonogramColours[] = [
  { bg: "#07284C", fg: "#FCC033", ring: "#FCC033" }, // navy / gold
  { bg: "#FCC033", fg: "#07284C", ring: "#07284C" }, // gold / navy
  { bg: "#19376d", fg: "#ffd666", ring: "#FCC033" }, // royal navy / light gold
  { bg: "#ffd666", fg: "#07284C", ring: "#19376d" }, // light gold / navy
  { bg: "#07284C", fg: "#ffffff", ring: "#ffd666" }, // navy / white
  { bg: "#12355b", fg: "#FCC033", ring: "#ffd666" }, // deep blue / gold
  { bg: "#f8e3a1", fg: "#07284C", ring: "#07284C" }, // pale gold / navy
  { bg: "#27498a", fg: "#ffffff", ring: "#FCC033" }, // steel navy / white
];

const SKIP_WORDS = new Set([
  "the", "of", "and", "for", "ltd", "limited", "pty", "proprietary", "soc", "inc",
  "plc", "rf", "co", "sa", "t/a",
]);

/** FNV-1a: tiny, stable across engines, good enough to spread colours. */
export function hashString(value: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < value.length; i++) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/**
 * Up to two initials from the name's meaningful words, in the name's own script.
 * Keeps diacritics (Ékhaya -> É), skips filler such as "Pty Ltd".
 */
export function monogramInitials(name: string): string {
  const words = (name || "")
    .replace(/\(.*?\)/g, " ")
    .split(/[\s\-–—/&,.]+/)
    .map((w) => w.replace(/[^\p{L}\p{N}]/gu, ""))
    .filter(Boolean);
  const meaningful = words.filter((w) => !SKIP_WORDS.has(w.toLowerCase()));
  const pool = meaningful.length ? meaningful : words;
  const letters = pool
    .slice(0, 2)
    .map((w) => Array.from(w)[0]?.toLocaleUpperCase("en") ?? "");
  return letters.join("") || "?";
}

/** Same key (id, else name) -> same colours, always. */
export function monogramColours(key: string): MonogramColours {
  return MONOGRAM_PALETTE[hashString(key || "?") % MONOGRAM_PALETTE.length];
}

// ---- WCAG helpers (used by tests to prove the palette stays AA) ----
function channel(v: number): number {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}
export function luminance(hex: string): number {
  const n = parseInt(hex.replace("#", ""), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
