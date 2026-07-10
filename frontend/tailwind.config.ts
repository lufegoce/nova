import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nova: {
          bg: "#0b0f14",
          panel: "#121821",
          border: "#232b36",
          accent: "#3b82f6",
        },
      },
    },
  },
  plugins: [],
};

export default config;
