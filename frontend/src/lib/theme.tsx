"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/** SOSPANA SONKE // FUTURE OF WORK -- light/dark theme toggle.
 *
 * The actual [data-theme] attribute on <html> is set twice, deliberately:
 *  1. Synchronously, before hydration, by the inline bootstrap script in
 *     layout.tsx (reads localStorage, falls back to prefers-color-scheme) --
 *     this is what prevents a flash of the wrong theme on load.
 *  2. By this provider's toggleTheme(), for the rest of the session.
 * This component's own state just mirrors whatever the bootstrap script
 * already applied on mount, rather than re-deciding it, so there's never a
 * mismatch between the two.
 */

type Theme = "light" | "dark";

const STORAGE_KEY = "ss-theme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    if (current === "dark" || current === "light") setTheme(current);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
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

/** Inline script text for a next/script beforeInteractive tag in layout.tsx.
 * Kept here (not hand-duplicated in JSX) so the storage key and fallback
 * logic can never drift out of sync with the provider above. */
export const THEME_BOOTSTRAP_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem('${STORAGE_KEY}');
    var theme = stored === 'dark' || stored === 'light'
      ? stored
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {}
})();
`;
