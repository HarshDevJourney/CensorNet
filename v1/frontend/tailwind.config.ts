import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "rgb(var(--c-paper) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        accent: "rgb(var(--c-accent) / <alpha-value>)",
        ready: "rgb(var(--c-ready) / <alpha-value>)",
        working: "rgb(var(--c-working) / <alpha-value>)",
        failed: "rgb(var(--c-failed) / <alpha-value>)",
        queued: "rgb(var(--c-queued) / <alpha-value>)",
        redis: "rgb(var(--c-redis) / <alpha-value>)",
        pg: "rgb(var(--c-pg) / <alpha-value>)",
      },
      fontFamily: {
        display: ["'Bricolage Grotesque Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["'Instrument Sans Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        fill: {
          "0%": { backgroundColor: "rgb(255 255 255 / 0.15)" },
          "40%": { backgroundColor: "rgb(var(--c-working))" },
          "100%": { backgroundColor: "rgb(var(--c-ready))" },
        },
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.45" } },
      },
      animation: {
        fill: "fill 700ms ease-out forwards",
        "pulse-soft": "pulseSoft 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
