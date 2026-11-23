import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#f6f1e7",
        paper: "#100e0c",
        amber: "#f0b429",
        coral: "#ff5d3a",
        line: "rgba(246, 241, 231, 0.14)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        lift: "0 18px 50px rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
