"use client";

import React from "react";
import type { ConfidenceLevel } from "@/types/m3";

interface Props {
  score: number;
  label: ConfidenceLevel;
  language: "ar" | "en";
}

const cfg: Record<ConfidenceLevel, { ring: string; dot: string; ar: string }> = {
  High:   { ring: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300", dot: "bg-emerald-400", ar: "عالية" },
  Medium: { ring: "border-yellow-400/40 bg-yellow-400/10 text-yellow-300",   dot: "bg-yellow-400",  ar: "متوسطة" },
  Low:    { ring: "border-red-400/40 bg-red-400/10 text-red-300",            dot: "bg-red-400",     ar: "منخفضة" },
};

export default function ConfidenceIndicator({ score, label, language }: Props) {
  const { ring, dot, ar } = cfg[label];
  const pct = Math.round(score * 100);
  const display = language === "ar" ? ar : label;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${ring}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot} animate-pulse`} />
      {display}
      <span className="font-mono opacity-70">{pct}%</span>
    </span>
  );
}
