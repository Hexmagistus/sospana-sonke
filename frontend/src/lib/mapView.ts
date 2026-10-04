/** Camera maths for the directory map. Pure functions, no DOM.

The map is the pre-rendered world (960 x 500 units, see data/world-map.json).
A country is a path made of M, L and Z commands, so its box can be read
straight from the path text. */

export const WORLD_W = 960;
export const WORLD_H = 500;

export type View = { x: number; y: number; w: number; h: number };

export const WORLD_VIEW: View = { x: 0, y: 0, w: WORLD_W, h: WORLD_H };

type Box = { minX: number; minY: number; maxX: number; maxY: number };

function boxOf(sub: string): Box | null {
  const nums = sub.match(/-?\d+(?:\.\d+)?/g);
  if (!nums || nums.length < 4) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i + 1 < nums.length; i += 2) {
    const x = Number(nums[i]);
    const y = Number(nums[i + 1]);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return { minX, minY, maxX, maxY };
}

const area = (b: Box) => (b.maxX - b.minX) * (b.maxY - b.minY);

/**
 * Box to frame for a country. The biggest piece anchors it, and only pieces
 * near that one are added. That keeps far-away territories (Alaska, French
 * Guiana, the Chukotka tip of Russia) from shrinking the view to a speck.
 */
export function countryBox(d: string): Box | null {
  const pieces = d.split("M").map(boxOf).filter((b): b is Box => b !== null);
  if (pieces.length === 0) return null;
  const main = pieces.reduce((a, b) => (area(b) > area(a) ? b : a));
  const reach = Math.max(main.maxX - main.minX, main.maxY - main.minY, 40) * 1.5;
  const cx = (main.minX + main.maxX) / 2;
  const cy = (main.minY + main.maxY) / 2;
  const merged = { ...main };
  for (const p of pieces) {
    if (p === main) continue;
    const px = (p.minX + p.maxX) / 2;
    const py = (p.minY + p.maxY) / 2;
    if (Math.abs(px - cx) <= reach && Math.abs(py - cy) <= reach) {
      merged.minX = Math.min(merged.minX, p.minX);
      merged.minY = Math.min(merged.minY, p.minY);
      merged.maxX = Math.max(merged.maxX, p.maxX);
      merged.maxY = Math.max(merged.maxY, p.maxY);
    }
  }
  return merged;
}

/** Smallest view width, so a tiny country is not zoomed into a blur. */
export const MIN_VIEW_W = 130;

/**
 * Camera for a country: its box plus padding, widened to the map's aspect
 * ratio, never smaller than MIN_VIEW_W and always inside the world.
 */
export function viewForCountry(d: string, centre: { x: number; y: number }): View {
  const box = countryBox(d);
  const aspect = WORLD_W / WORLD_H;
  let w = MIN_VIEW_W;
  let cx = centre.x;
  let cy = centre.y;
  if (box) {
    cx = (box.minX + box.maxX) / 2;
    cy = (box.minY + box.maxY) / 2;
    const bw = (box.maxX - box.minX) * 1.9;
    const bh = (box.maxY - box.minY) * 1.9 * aspect;
    w = Math.max(MIN_VIEW_W, bw, bh);
  }
  w = Math.min(w, WORLD_W);
  const h = w / aspect;
  const x = Math.min(Math.max(cx - w / 2, 0), WORLD_W - w);
  const y = Math.min(Math.max(cy - h / 2, 0), WORLD_H - h);
  return { x, y, w, h };
}

export function easeInOutCubic(t: number): number {
  const c = Math.min(Math.max(t, 0), 1);
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}

/** Point between two views. t is 0..1 and is eased by the caller. */
export function mixViews(a: View, b: View, t: number): View {
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    w: a.w + (b.w - a.w) * t,
    h: a.h + (b.h - a.h) * t,
  };
}

export const viewBoxString = (v: View) => `${v.x.toFixed(2)} ${v.y.toFixed(2)} ${v.w.toFixed(2)} ${v.h.toFixed(2)}`;

/* ---- Interactive pan / zoom (drag, wheel, pinch, buttons, keyboard) ---- */

/** Closest the user can zoom in: a view this wide is ~24x the world. */
export const MAX_ZOOM_VIEW_W = 40;
const ASPECT = WORLD_W / WORLD_H;

/** Keep a view inside the world and within the allowed zoom range, with the map's aspect ratio. */
export function clampView(v: View): View {
  const w = Math.min(WORLD_W, Math.max(MAX_ZOOM_VIEW_W, v.w));
  const h = w / ASPECT;
  const x = Math.min(Math.max(v.x, 0), WORLD_W - w);
  const y = Math.min(Math.max(v.y, 0), WORLD_H - h);
  return { x, y, w, h };
}

/**
 * Zoom by `factor` (> 1 zooms in) keeping the point under (fx, fy) fixed. fx and fy are
 * fractions 0..1 of the view, so the cursor / pinch centre stays where the user put it.
 */
export function zoomView(v: View, factor: number, fx = 0.5, fy = 0.5): View {
  const w = Math.min(WORLD_W, Math.max(MAX_ZOOM_VIEW_W, v.w / factor));
  const h = w / ASPECT;
  const px = v.x + v.w * fx;
  const py = v.y + v.h * fy;
  return clampView({ x: px - w * fx, y: py - h * fy, w, h });
}

/** Move the view by (dx, dy) map units. */
export function panView(v: View, dx: number, dy: number): View {
  return clampView({ ...v, x: v.x + dx, y: v.y + dy });
}

/** How far zoomed in a view is (1 = whole world). */
export const zoomLevel = (v: View) => WORLD_W / v.w;

export type MapKeyAction =
  | { kind: "pan"; dx: number; dy: number }
  | { kind: "zoom"; factor: number }
  | { kind: "reset" };

/** Keyboard map: arrows pan by 15% of the view, + / - zoom, 0 or Home resets. */
export function keyAction(key: string): MapKeyAction | null {
  switch (key) {
    case "ArrowLeft": return { kind: "pan", dx: -0.15, dy: 0 };
    case "ArrowRight": return { kind: "pan", dx: 0.15, dy: 0 };
    case "ArrowUp": return { kind: "pan", dx: 0, dy: -0.15 };
    case "ArrowDown": return { kind: "pan", dx: 0, dy: 0.15 };
    case "+": case "=": return { kind: "zoom", factor: 1.5 };
    case "-": case "_": return { kind: "zoom", factor: 1 / 1.5 };
    case "0": case "Home": return { kind: "reset" };
    default: return null;
  }
}

/** Wheel zoom factor for a wheel event's deltaY (negative scrolls up = zoom in). */
export const wheelFactor = (deltaY: number) => Math.exp(-Math.max(-120, Math.min(120, deltaY)) * 0.0022);
