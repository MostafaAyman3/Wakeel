"use client";

import React, { forwardRef } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { formatNumber } from "@/lib/rtl";

/* ─────────────────────────────────────────────────────────────
 * MetricCard — displays single KPI with large number + context.
 *
 * Supports: single scalar, comparison pair, or triple (T3).
 * forwardRef + standard HTML attributes for shadcn swap.
 * ───────────────────────────────────────────────────────────── */

interface MetricCardProps {
  data: Record<string, unknown>[];
  language: "ar" | "en";
}

/* Columns that are context, not KPIs — dates, identifiers, internal fields.
 * A date rendered as a big gold number ("INVOICE DATE: 2024") is noise. */
const NON_METRIC_KEY = /(^|_)(id|uuid)$|date|period|_at$|month|year|quarter|week|day/i;

const MetricCard = forwardRef<HTMLDivElement, MetricCardProps>(
  function MetricCard({ data, language }, ref) {
    if (!data || data.length === 0) return null;

    const row = data[0];
    const allEntries = Object.entries(row).filter(([k]) => !k.startsWith("_"));
    const metricEntries = allEntries.filter(([k]) => !NON_METRIC_KEY.test(k));
    // If filtering removed everything, show the original row rather than nothing
    const entries = metricEntries.length > 0 ? metricEntries : allEntries;

    // Single value
    if (entries.length === 1) {
      const [label, value] = entries[0];
      return (
        <div ref={ref} className="card-base" id="metric-card">
          <p className="text-xs text-ivory/40 uppercase tracking-wider font-inter mb-1">
            {formatLabel(label, language)}
          </p>
          <p className="text-3xl font-bold font-cairo text-gold">
            {formatNumber(value as number, language)}
          </p>
        </div>
      );
    }

    // Multiple metrics (T3 executive summary style)
    return (
      <div ref={ref} className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(entries.length, 3)}, 1fr)` }} id="metric-card">
        {entries.map(([label, value]) => (
          <div key={label} className="card-base text-center">
            <p className="text-xs text-ivory/40 uppercase tracking-wider font-inter mb-1">
              {formatLabel(label, language)}
            </p>
            <p className="text-2xl font-bold font-cairo text-gold">
              {formatNumber(value as number, language)}
            </p>
          </div>
        ))}
      </div>
    );
  },
);

function formatLabel(key: string, language: string): string {
  // Clean up snake_case into readable labels
  const cleaned = key.replace(/_/g, " ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export default MetricCard;
