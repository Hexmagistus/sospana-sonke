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
        // gold.dark is the AA-safe gold for TEXT on light surfaces (5.9:1 on white);
        // plain gold is for fills, borders and text on navy/dark.
        gold: { DEFAULT: "#f5b301", light: "#ffd76a", dark: "#8a5a00" },
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
      // Gold text must stay readable on light surfaces, so text-ss-primary resolves
      // to --ss-primary-text (dark gold in light mode, bright gold in dark mode).
      // bg-/border-/ring-ss-primary keep the bright brand gold.
      textColor: {
        "ss-primary": "var(--ss-primary-text)",
      },
      fontFamily: {
        // Headings / display moments.
        display: ["var(--font-display)", "var(--font-text)", "ui-sans-serif", "system-ui", "sans-serif"],
        // UI + body. Overrides Tailwind's default sans so the whole app follows.
        sans: [
          "var(--font-text)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI",
          "Roboto", "Noto Sans", "Helvetica Neue", "Arial", "sans-serif",
        ],
      },
      // Fluid type scale (tokens live in globals.css). Existing text-sm / text-xl...
      // utilities are unchanged so no layout shifts; new work can use text-step-*.
      fontSize: {
        "step--1": ["var(--ss-step--1)", { lineHeight: "1.5" }],
        "step-0": ["var(--ss-step-0)", { lineHeight: "1.6" }],
        "step-1": ["var(--ss-step-1)", { lineHeight: "1.4" }],
        "step-2": ["var(--ss-step-2)", { lineHeight: "1.3" }],
        "step-3": ["var(--ss-step-3)", { lineHeight: "1.2" }],
        "step-4": ["var(--ss-step-4)", { lineHeight: "1.12" }],
        "step-5": ["var(--ss-step-5)", { lineHeight: "1.05" }],
      },
      transitionTimingFunction: { ss: "var(--ss-ease)" },
      transitionDuration: { "ss-fast": "var(--ss-dur-fast)", ss: "var(--ss-dur)", "ss-slow": "var(--ss-dur-slow)" },
    },
  },
  plugins: [],
};
export default config;
