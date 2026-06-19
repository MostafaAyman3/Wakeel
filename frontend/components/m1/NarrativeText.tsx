"use client";

import React, { forwardRef } from "react";
import { Info } from "lucide-react";
import type { OutputFormat } from "@/types/m1";

/* ─────────────────────────────────────────────────────────────
 * NarrativeText — rich text display for narratives.
 *
 * Handles: direct_text, narrative, formatted_text_list.
 * Shows disclaimer as footnote for tax responses.
 * forwardRef for shadcn swap.
 * ───────────────────────────────────────────────────────────── */

interface NarrativeTextProps {
  text: string;
  format: OutputFormat;
  language: "ar" | "en";
  disclaimer?: string | null;
}

const NarrativeText = forwardRef<HTMLDivElement, NarrativeTextProps>(
  function NarrativeText({ text, format, language, disclaimer }, ref) {
    if (!text) return null;

    // Split text into paragraphs
    const paragraphs = text
      .split(/\n+/)
      .map((p) => p.trim())
      .filter(Boolean);

    return (
      <div ref={ref} className="space-y-2" id="narrative-text">
        {/* Label for context */}
        {format !== "narrative" && format !== "direct_text" && (
          <p className="text-xs text-ivory/30 font-inter uppercase tracking-wider">
            {language === "ar" ? "التحليل" : "Analysis"}
          </p>
        )}

        {/* Narrative content */}
        <div
          className="text-sm text-ivory/80 leading-relaxed font-cairo space-y-2"
          dir={language === "ar" ? "rtl" : "ltr"}
        >
          {paragraphs.map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>

        {/* Disclaimer (tax responses) */}
        {disclaimer && (
          <div className="flex items-start gap-2 mt-3 pt-3 border-t border-slate/50">
            <Info size={14} className="text-ivory/30 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-ivory/30 leading-relaxed font-inter">
              {disclaimer}
            </p>
          </div>
        )}
      </div>
    );
  },
);

export default NarrativeText;
