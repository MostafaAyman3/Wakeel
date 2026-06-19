"use client";

import React, { forwardRef } from "react";

/* ─────────────────────────────────────────────────────────────
 * LanguageToggle — AR ↔ EN switch with animated indicator.
 * ───────────────────────────────────────────────────────────── */

interface LanguageToggleProps {
  language: "ar" | "en";
  onChange: (lang: "ar" | "en") => void;
}

const LanguageToggle = forwardRef<HTMLDivElement, LanguageToggleProps>(
  function LanguageToggle({ language, onChange }, ref) {
    return (
      <div
        ref={ref}
        className="inline-flex items-center rounded-lg bg-midnight border border-slate p-0.5"
        role="radiogroup"
        aria-label="Language selection"
      >
        <button
          type="button"
          role="radio"
          aria-checked={language === "ar"}
          onClick={() => onChange("ar")}
          className={`px-3 py-1.5 text-sm rounded-md transition-all duration-200 ${
            language === "ar"
              ? "bg-gold text-midnight font-semibold"
              : "text-ivory/50 hover:text-ivory"
          }`}
        >
          عربي
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={language === "en"}
          onClick={() => onChange("en")}
          className={`px-3 py-1.5 text-sm rounded-md font-inter transition-all duration-200 ${
            language === "en"
              ? "bg-gold text-midnight font-semibold"
              : "text-ivory/50 hover:text-ivory"
          }`}
        >
          EN
        </button>
      </div>
    );
  },
);

export default LanguageToggle;
