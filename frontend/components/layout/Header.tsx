"use client";

import React, { forwardRef } from "react";
import { Languages } from "lucide-react";
import ModuleSwitcher from "./ModuleSwitcher";

/* ─────────────────────────────────────────────────────────────
 * Header — logo + module switcher + language toggle.
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
        {/* Left: Logo */}
        <div className="flex items-center gap-3 md:w-1/3">
          <div className="w-8 h-8 rounded-lg bg-gold flex items-center justify-center shadow-[0_0_10px_rgba(245,158,11,0.2)]">
            <span className="text-midnight font-bold text-sm font-cairo">و</span>
          </div>
          <div>
            <h1 className="text-lg font-bold font-cairo leading-none">
              {isAr ? "وكيل" : "Wakeel"}
            </h1>
            <p className="text-xs text-ivory/40 font-inter">
              {isAr ? "نظام الإدارة الذكي" : "Smart ERP System"}
            </p>
          </div>
        </div>

        {/* Center: Module Switcher */}
        <div className="flex justify-center flex-1">
          <ModuleSwitcher language={language} />
        </div>

        {/* Right: Language toggle */}
        <div className="flex justify-end md:w-1/3">
          <button
            type="button"
            onClick={onToggleLanguage}
            className="btn-ghost flex items-center gap-2 text-sm hover:text-gold transition-colors"
            aria-label="Toggle language"
          >
            <Languages size={16} />
            <span className="font-inter font-medium">
              {isAr ? "EN" : "عربي"}
            </span>
          </button>
        </div>
      </header>
    );
  },
);

export default Header;
