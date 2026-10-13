"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { effectiveTheme } from "./entryFlow";
import { THEME_STORAGE_KEY } from "./themeBootstrap";

/** SOSPANA SONKE // FUTURE OF WORK -- light/dark theme toggle.
 *
 * The actual [data-theme] attribute on <html> is set twice, deliberately:
 *  1. Synchronously, before hydration, by the inline bootstrap script in
 *     layout.tsx (reads localStorage, otherwise the system theme) --
 *     this is what prevents a flash of the wrong theme on load.
 *  2. By this provider's toggleTheme(), for the rest of the session.
 * This component's own state just mirrors whatever the bootstrap script
 * already applied on mount, rather than re-deciding it, so there's never a
 * mismatch between the two.
 */

type Theme = "light" | "dark";

const STORAGE_KEY = THEME_STORAGE_KEY;

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  // `stored` is the visitor's choice; the attribute on <html> is effectiveTheme(): the entry
  // flow (landing, login, register ...) is always bright, see lib/entryFlow.ts.
  const pathname = usePathname();
  const [stored, setStored] = useState<Theme>("light");
  const [ready, setReady] = useState(false);
  const [followSystem, setFollowSystem] = useState(true);

  useEffect(() => {
    let explicit = false;
    try {
      const v = window.localStorage.getItem(STORAGE_KEY);
      if (v === "dark" || v === "light") {
        setStored(v);
        explicit = true;
        setFollowSystem(false);
      } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        setStored("dark");
      }
    } catch {
      /* private mode: keep the default */
    }
    if (!explicit) setFollowSystem(true);
    setReady(true);
  }, []);

  useEffect(() => {
    if (!followSystem) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => setStored(media.matches ? "dark" : "light");
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [followSystem]);

  const theme = effectiveTheme(pathname, stored);
  useEffect(() => {
    // Leave the bootstrap script's attribute alone until we know the saved choice,
    // so a system dark theme does not flash light on the first paint.
    if (!ready) return;
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme, ready]);

  const toggleTheme = useCallback(() => {
    setFollowSystem(false);
    setStored((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* best-effort persistence only */
      }
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}

export { THEME_BOOTSTRAP_SCRIPT } from "./themeBootstrap";
