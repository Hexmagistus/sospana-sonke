/** The caption that must always sit directly under the sun/moon icon. */
export const BRIGHTNESS_LABEL = "Adjust brightness";

export type ThemeName = "light" | "dark";

export function brightnessHint(theme: ThemeName): string {
  return theme === "dark"
    ? `${BRIGHTNESS_LABEL}. Switch to light mode`
    : `${BRIGHTNESS_LABEL}. Switch to dark mode`;
}

/**
 * Presentational sun/moon button with the "Adjust brightness" caption under the icon. It is
 * visible at every width (no `hidden`), 0.7rem (about 12px) or larger, and wraps onto two
 * lines so it fits a 320px phone. The caption uses text-ss-primary, which the theme contrast
 * test covers in both light and dark. Nav wires it to the real theme state.
 */
export default function ThemeToggleButton({
  theme,
  onToggle,
  className = "",
}: {
  theme: ThemeName;
  onToggle: () => void;
  className?: string;
}) {
  const hint = brightnessHint(theme);
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={hint}
      title={hint}
      data-testid="theme-toggle"
      className={`flex min-h-11 w-[3.6rem] min-[400px]:w-[4.5rem] shrink-0 flex-col items-center justify-center gap-0.5 rounded-md px-0.5 py-0.5 text-ss-primary transition hover:bg-ss-primary-soft hover:text-ss-text ${className}`}
    >
      <span className="flex h-6 w-6 items-center justify-center" aria-hidden="true">
        {theme === "dark" ? (
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="4.5" />
            <path strokeLinecap="round" d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.5 14.5A8.5 8.5 0 019.5 3.5a8.5 8.5 0 1011 11z" />
          </svg>
        )}
      </span>
      <span
        data-testid="theme-toggle-label"
        className="block w-full whitespace-normal break-normal text-center text-[0.7rem] font-semibold leading-[1.05] tracking-tight text-ss-primary"
      >
        {BRIGHTNESS_LABEL}
      </span>
    </button>
  );
}
