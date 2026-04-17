/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0a0a2e",
        ink: "#10103d",
      },
      boxShadow: {
        neon: "0 0 25px rgba(133, 64, 255, 0.55)",
      },
    },
  },
  plugins: [],
};
