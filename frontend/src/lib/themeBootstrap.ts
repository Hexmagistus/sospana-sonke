export const THEME_STORAGE_KEY = "ss-theme";

/** Inline script text for a next/script beforeInteractive tag in layout.tsx.
 * Kept here (not hand-duplicated in JSX) so the storage key and fallback
 * logic can never drift out of sync with the provider above. */
// Always bright: the site is light-only (owner request). Saved choices and the
// OS dark preference are ignored; the stale key is cleared.
export const THEME_BOOTSTRAP_SCRIPT = `
(function () {
  try { localStorage.removeItem('${THEME_STORAGE_KEY}'); } catch (e) {}
  document.documentElement.setAttribute('data-theme', 'light');
})();
`;
