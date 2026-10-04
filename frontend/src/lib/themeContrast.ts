/**
 * WCAG 2.x contrast helpers used by themeContrast.test.ts.
 *
 * Pure functions plus a tiny reader for the design tokens in app/globals.css, so the
 * test checks the values that actually ship (and fails if someone later lightens a
 * text colour or darkens a surface below the accessible minimum).
 */

export type RGB = { r: number; g: number; b: number; a: number };

export function parseColor(input: string): RGB {
  const s = input.trim().toLowerCase();
  let m = /^#([0-9a-f]{3})$/.exec(s);
  if (m) {
    const [r, g, b] = m[1].split("").map((c) => parseInt(c + c, 16));
    return { r, g, b, a: 1 };
  }
  m = /^#([0-9a-f]{6})$/.exec(s);
  if (m) {
    return { r: parseInt(m[1].slice(0, 2), 16), g: parseInt(m[1].slice(2, 4), 16), b: parseInt(m[1].slice(4, 6), 16), a: 1 };
  }
  m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/.exec(s);
  if (m) return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
  throw new Error(`Unsupported colour: ${input}`);
}

/** Paint `fg` (which may be translucent) over an opaque `bg`. */
export function composite(fg: RGB, bg: RGB): RGB {
  const a = fg.a;
  return { r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a), a: 1 };
}

function channel(v: number): number {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function luminance(c: RGB): number {
  return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
}

/** WCAG contrast ratio between two colours; a translucent `bg` is first painted over `under`. */
export function contrastRatio(fg: string, bg: string, under = "#ffffff"): number {
  const base = parseColor(under);
  const b = composite(parseColor(bg), base);
  const f = composite(parseColor(fg), b);
  const l1 = luminance(f);
  const l2 = luminance(b);
  const [hi, lo] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * Collect `--token: value` declarations from every rule in `css` whose selector (trimmed,
 * whitespace-collapsed) equals `selector`. Later declarations win, like the cascade.
 */
export function readTokens(css: string, selector: string): Record<string, string> {
  const out: Record<string, string> = {};
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const rule = /([^{}]+)\{([^{}]*)\}/g;
  let m: RegExpExecArray | null;
  while ((m = rule.exec(stripped))) {
    const sels = m[1].split(";").pop()!.split(",").map((x) => x.trim().replace(/\s+/g, " "));
    if (!sels.includes(selector)) continue;
    for (const d of m[2].matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/gi)) out[d[1]] = d[2].trim();
  }
  return out;
}
