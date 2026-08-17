import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0f766e", dark: "#115e59", light: "#5eead4" },
        navy: { DEFAULT: "#0b2447", light: "#123a6b" },
        gold: { DEFAULT: "#f5b301", light: "#ffd76a" },
        coral: "#ff6b5b",
        purple: "#7c5cff",
        sky: "#2f9bf6",
      },
    },
  },
  plugins: [],
};
export default config;
