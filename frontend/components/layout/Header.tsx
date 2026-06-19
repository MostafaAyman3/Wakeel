"use client";

import React, { forwardRef } from "react";
import { Languages } from "lucide-react";

/* ─────────────────────────────────────────────────────────────
 * Header — logo + language toggle.
 * Compact, no navigation needed for M1 demo.
 * ───────────────────────────────────────────────────────────── */

interface HeaderProps {
  language: "ar" | "en";
  onToggleLanguage: () => void;
}

const Header = forwardRef<HTMLElement, HeaderProps>(
  function Header({ language, onToggleLanguage }, ref) {
    const isAr = language === "ar";

    return (
      <header
        ref={ref}
        className="flex items-center justify-between px-6 py-3 border-b border-slate bg-surface/80 backdrop-blur-sm sticky top-0 z-50"
      >
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gold flex items-center justify-center">
            <span className="text-midnight font-bold text-sm font-cairo">و</span>
          </div>
          <div>
            <h1 className="text-lg font-bold font-cairo leading-none">
              {isAr ? "وكيل" : "Wakeel"}
            </h1>
            <p className="text-xs text-ivory/40 font-inter">
              {isAr ? "المحلل المالي الذكي" : "AI Financial Analyst"}
            </p>
          </div>
        </div>

        {/* Language toggle */}
        <button
          type="button"
          onClick={onToggleLanguage}
          className="btn-ghost flex items-center gap-2 text-sm"
          aria-label="Toggle language"
        >
          <Languages size={16} />
          <span className="font-inter font-medium">
            {isAr ? "EN" : "عربي"}
          </span>
        </button>
      </header>
    );
  },
);

export default Header;
