import type { Config } from "tailwindcss";

// Wakeel — unified dark "financial-analyst" identity (aligned with M1).
// Dark midnight surfaces, gold accent, ivory text, Cairo/Inter/JetBrains Mono.
//
// The semantic tokens (paper/ink/line/sage/petrol…) used across the M3 UI are
// remapped to dark-theme values so existing markup flips to the dark look,
// while the explicit M1 names (midnight/surface/slate/gold/ivory) are available
// for the shared shell (Sidebar/Header) and chat bubbles.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ── M1 (MH74) palette ──────────────────────────────
        midnight: "#0A0F1C",
        surface: "#111827",
        slate: { DEFAULT: "#1E293B", light: "#334155" },
        gold: { DEFAULT: "#F59E0B", light: "#FCD34D", dim: "#B45309" },
        ivory: "#F8FAFC",
        danger: { DEFAULT: "#EF4444", dim: "#991B1B" },
        warning: { DEFAULT: "#F59E0B", dim: "#92400E" },

        // ── Semantic aliases remapped onto the dark palette ─
        ink: "#F8FAFC",        // primary text (was near-black → now ivory)
        sand: "#0A0F1C",       // app background → midnight
        paper: "#111827",      // cards → surface
        line: "#1E293B",       // borders → slate
        sage: "#94A3B8",       // muted text
        petrol: { DEFAULT: "#F59E0B", deep: "#B45309", soft: "#FCD34D" },
        amber: "#F59E0B",
        ok: "#34D399",
        warn: "#F59E0B",
        alert: "#EF4444",
      },
      fontFamily: {
        cairo: ["Cairo", "sans-serif"],
        inter: ["Inter", "system-ui", "sans-serif"],
        display: ["Cairo", "Inter", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        desk: "0 1px 2px rgba(0,0,0,0.3), 0 12px 32px -18px rgba(0,0,0,0.6)",
        lift: "0 16px 48px -22px rgba(0,0,0,0.7)",
      },
      borderRadius: { card: "14px" },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245,158,11,0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(245,158,11,0)" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        segIn: {
          "0%": { transform: "scaleY(0.2)", opacity: "0.3" },
          "100%": { transform: "scaleY(1)", opacity: "1" },
        },
      },
      animation: {
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.4s ease-out",
        riseIn: "fade-in 0.35s ease-out both",
        segIn: "segIn 0.4s cubic-bezier(0.2,0.7,0.2,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
