import type { Config } from "tailwindcss";

// Wakeel Dispatch Desk — design tokens.
// A calm operations console for human-supervised AI support.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15211F",
        petrol: {
          DEFAULT: "#0F5257",
          deep: "#0A3B3F",
          soft: "#1A6B6F",
        },
        sand: "#ECEFEC",
        paper: "#FFFFFF",
        line: "#E1E5E0",
        sage: "#6E827C",
        amber: "#D88A2B",
        ok: "#2C7A57",
        warn: "#C2862A",
        alert: "#B14430",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        desk: "0 1px 2px rgba(21,33,31,0.04), 0 8px 28px -16px rgba(15,82,87,0.18)",
        lift: "0 12px 40px -20px rgba(15,82,87,0.35)",
      },
      borderRadius: {
        card: "14px",
      },
      keyframes: {
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        segIn: {
          "0%": { transform: "scaleY(0.2)", opacity: "0.3" },
          "100%": { transform: "scaleY(1)", opacity: "1" },
        },
      },
      animation: {
        riseIn: "riseIn 0.35s cubic-bezier(0.2,0.7,0.2,1) both",
        segIn: "segIn 0.4s cubic-bezier(0.2,0.7,0.2,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
