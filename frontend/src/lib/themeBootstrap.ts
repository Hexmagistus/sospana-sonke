import { ENTRY_FLOW_PATHS } from "./entryFlow";

export const THEME_STORAGE_KEY = "ss-theme";

/** Inline script text for a next/script beforeInteractive tag in layout.tsx.
 * Kept here (not hand-duplicated in JSX) so the storage key and fallback
 * logic can never drift out of sync with the provider above. */
export const THEME_BOOTSTRAP_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem('${THEME_STORAGE_KEY}');
    // An explicit toggle wins. With no saved choice, follow the system theme.
    var theme = stored === 'dark' || stored === 'light'
      ? stored
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    // The pre-login pages are always bright (see lib/entryFlow.ts).
    var p = location.pathname.replace(/\\/+$/, '') || '/';
    if (${JSON.stringify(ENTRY_FLOW_PATHS)}.indexOf(p) !== -1) theme = 'light';
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {}
})();
`;
