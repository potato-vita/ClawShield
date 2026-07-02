/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        trace: {
          red: "#C91F37",
          blush: "#FFF6F5",
          canvas: "#F7F7F6",
          metal: "#CBD5E1",
          blue: "#2563EB",
        },
      },
      boxShadow: {
        panel: "0 12px 32px rgba(15, 23, 42, 0.07)",
      },
    },
  },
  plugins: [],
};
