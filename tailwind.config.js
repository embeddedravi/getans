/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./tmpl/**"], // This is where your HTML templates / JSX files are located
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["sans-serif"],
        mono: ["monospace"],
        serif: ["serif"],
      },
    },
  },
  plugins: [],
  
};
