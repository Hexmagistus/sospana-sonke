/**
 * The pre-login "entry flow": landing, login, register, forgot and reset password.
 * These pages are designed on a warm light canvas (cream, white cards, navy and gold
 * accents, photos with their own scrims). They always render in the bright theme, even if
 * a signed-in visitor once chose dark mode: there is no brightness toggle before login, and
 * the page would otherwise paint light text on those light surfaces. The stored choice is
 * left alone and applies again everywhere else (explorer, dashboard, CV pages ...).
 */
export const ENTRY_FLOW_PATHS = ["/", "/login", "/register", "/forgot-password", "/reset-password"] as const;

export function isEntryFlowPath(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  const p = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return (ENTRY_FLOW_PATHS as readonly string[]).includes(p);
}

/** Theme actually applied to <html> for a path, given the stored choice. */
export function effectiveTheme(pathname: string | null | undefined, stored: "light" | "dark"): "light" | "dark" {
  return isEntryFlowPath(pathname) ? "light" : stored;
}
