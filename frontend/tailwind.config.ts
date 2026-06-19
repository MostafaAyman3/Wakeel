import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        midnight: "#0A0F1C",
        surface: "#111827",
        slate: {
          DEFAULT: "#1E293B",
          light: "#334155",
        },
        gold: {
          DEFAULT: "#F59E0B",
          light: "#FCD34D",
          dim: "#B45309",
        },
        ivory: "#F8FAFC",
        danger: {
          DEFAULT: "#EF4444",
          dim: "#991B1B",
        },
        warning: {
          DEFAULT: "#F59E0B",
          dim: "#92400E",
        },
      },
      fontFamily: {
        cairo: ["Cairo", "sans-serif"],
        inter: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245, 158, 11, 0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(245, 158, 11, 0)" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-border": {
          "0%, 100%": { borderColor: "rgba(239, 68, 68, 0.6)" },
          "50%": { borderColor: "rgba(239, 68, 68, 1)" },
        },
      },
      animation: {
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.4s ease-out",
        "pulse-border": "pulse-border 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
