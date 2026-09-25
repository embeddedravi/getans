/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        sans:    ["Inter", "sans-serif"],
        mono:    ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  daisyui: {
    themes: [
      {
        signal: {
          "primary":          "#F2A93B",
          "primary-content":  "#12161C",
          "secondary":        "#5B8DEF",
          "secondary-content":"#F5F7FA",
          "accent":           "#4CAF7D",
          "accent-content":   "#0E1712",
          "neutral":          "#1B212A",
          "neutral-content":  "#C7CDD6",
          "base-100":         "#12161C",
          "base-200":         "#171C24",
          "base-300":         "#1B212A",
          "base-content":     "#E7EAEE",
          "info":             "#5B8DEF",
          "success":          "#4CAF7D",
          "warning":          "#F2A93B",
          "error":            "#E2585B",

          "--rounded-box":    "0.375rem",
          "--rounded-btn":    "0.25rem",
          "--rounded-badge":  "0.25rem",
          "--border-btn":     "1px",
          "--tab-radius":     "0.25rem",
        },
      },
    ],
    darkTheme: "signal",
    base: true,
    styled: true,
    utils: true,
  },
  plugins: [require("daisyui")],
};
