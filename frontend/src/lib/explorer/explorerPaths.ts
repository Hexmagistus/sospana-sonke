/** Pages that use the split country explorer. On desktop these drop the top bar:
the logo and menu button sit in the explorer, and the links open in a side drawer. */
const EXPLORER_PATHS = ["/companies", "/universities", "/hospitals"] as const;

export function isExplorerPath(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  const p = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return (EXPLORER_PATHS as readonly string[]).includes(p);
}

/** Event the explorer's menu button sends and the nav listens for. */
export const OPEN_MENU_EVENT = "ss:open-menu";
