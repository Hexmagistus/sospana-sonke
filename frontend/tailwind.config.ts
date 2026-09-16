import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  // "selector" (not the default "media") so the SS // FUTURE OF WORK theme
  // toggle (lib/theme.tsx, sets [data-theme] on <html>) drives dark: utilities
  // directly, independent of the OS-level prefers-color-scheme setting.
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0f766e", dark: "#115e59", light: "#5eead4" },
        navy: { DEFAULT: "#0b2447", light: "#123a6b" },
        gold: { DEFAULT: "#f5b301", light: "#ffd76a" },
        coral: "#ff6b5b",
        purple: "#7c5cff",
        sky: "#2f9bf6",
        // SOSPANA SONKE // FUTURE OF WORK design tokens -- CSS variables
        // (see globals.css), so these utilities self-adapt to the active
        // theme without needing a dark: variant on every usage.
        ss: {
          bg: "var(--ss-bg)",
          surface: "var(--ss-surface)",
          elevated: "var(--ss-surface-elevated)",
          glass: "var(--ss-glass)",
          border: "var(--ss-border)",
          text: "var(--ss-text)",
          muted: "var(--ss-text-muted)",
          primary: "var(--ss-primary)",
          "primary-glow": "var(--ss-primary-glow)",
          "primary-soft": "var(--ss-primary-soft)",
          "primary-soft-strong": "var(--ss-primary-soft-strong)",
          "primary-border-soft": "var(--ss-primary-border-soft)",
          tech: "var(--ss-tech)",
          "tech-glow": "var(--ss-tech-glow)",
          success: "var(--ss-success)",
          warning: "var(--ss-warning)",
          danger: "var(--ss-danger)",
          "danger-soft": "var(--ss-danger-soft)",
          "danger-soft-border": "var(--ss-danger-soft-border)",
        },
      },
      fontFamily: {
        display: ["var(--font-space)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
