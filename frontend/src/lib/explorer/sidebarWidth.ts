/** Width of the country sidebar in the split view (desktop only), in px. */
export const SIDEBAR_MIN = 240;
export const SIDEBAR_MAX = 480;
export const SIDEBAR_DEFAULT = 304; // 19rem
export const SIDEBAR_STEP = 16;
export const SIDEBAR_BIG_STEP = 48;
export const SIDEBAR_STORAGE_KEY = "ss-explorer-sidebar-width";

export function clampSidebarWidth(px: number, min = SIDEBAR_MIN, max = SIDEBAR_MAX): number {
  if (!Number.isFinite(px)) return SIDEBAR_DEFAULT;
  return Math.round(Math.min(max, Math.max(min, px)));
}

/** A stored value that is missing, not a number or out of range falls back to the default. */
export function parseStoredWidth(raw: string | null | undefined): number {
  if (raw == null || raw.trim() === "") return SIDEBAR_DEFAULT;
  const n = Number(raw);
  if (!Number.isFinite(n)) return SIDEBAR_DEFAULT;
  return clampSidebarWidth(n);
}

/** New width for a key press on the separator, or null when the key is not one it handles. */
export function widthAfterKey(current: number, key: string, shift = false): number | null {
  const step = shift ? SIDEBAR_BIG_STEP : SIDEBAR_STEP;
  switch (key) {
    case "ArrowLeft": return clampSidebarWidth(current - step);
    case "ArrowRight": return clampSidebarWidth(current + step);
    case "Home": return SIDEBAR_MIN;
    case "End": return SIDEBAR_MAX;
    case "Enter": return SIDEBAR_DEFAULT;
    default: return null;
  }
}

/** Width while dragging: pointer x relative to the left edge of the split view. */
export function widthFromPointer(clientX: number, containerLeft: number): number {
  return clampSidebarWidth(clientX - containerLeft);
}

export function readStoredWidth(): number {
  try { return parseStoredWidth(localStorage.getItem(SIDEBAR_STORAGE_KEY)); } catch { return SIDEBAR_DEFAULT; }
}

export function storeWidth(px: number): void {
  try {
    if (px === SIDEBAR_DEFAULT) localStorage.removeItem(SIDEBAR_STORAGE_KEY);
    else localStorage.setItem(SIDEBAR_STORAGE_KEY, String(px));
  } catch { /* private mode */ }
}
