"use client";

import React, { forwardRef, useState, useMemo } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { formatNumber } from "@/lib/rtl";

/* ─────────────────────────────────────────────────────────────
 * SortableTable — sortable data table with dark theme.
 *
 * Features:
 *   - Click column header to sort ASC/DESC
 *   - Numbers aligned LTR even in RTL mode
 *   - Alternating row colors
 *   - "Show more" for > 20 rows
 *   - forwardRef for shadcn swap
 * ───────────────────────────────────────────────────────────── */

interface SortableTableProps {
  data: Record<string, unknown>[];
  language: "ar" | "en";
  maxRows?: number;
}

type SortDir = "asc" | "desc" | null;

const SortableTable = forwardRef<HTMLDivElement, SortableTableProps>(
  function SortableTable({ data, language, maxRows = 20 }, ref) {
    const [sortCol, setSortCol] = useState<string | null>(null);
    const [sortDir, setSortDir] = useState<SortDir>(null);
    const [showAll, setShowAll] = useState(false);

    if (!data || data.length === 0) return null;

    const columns = Object.keys(data[0]);

    const sorted = useMemo(() => {
      if (!sortCol || !sortDir) return data;
      return [...data].sort((a, b) => {
        const va = a[sortCol];
        const vb = b[sortCol];
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === "number" && typeof vb === "number") {
          return sortDir === "asc" ? va - vb : vb - va;
        }
        const sa = String(va);
        const sb = String(vb);
        return sortDir === "asc" ? sa.localeCompare(sb) : sb.localeCompare(sa);
      });
    }, [data, sortCol, sortDir]);

    const displayed = showAll ? sorted : sorted.slice(0, maxRows);
    const hasMore = sorted.length > maxRows;

    const handleSort = (col: string) => {
      if (sortCol === col) {
        setSortDir((d) => (d === "asc" ? "desc" : d === "desc" ? null : "asc"));
        if (sortDir === "desc") setSortCol(null);
      } else {
        setSortCol(col);
        setSortDir("asc");
      }
    };

    const isNumeric = (col: string) => {
      const sample = data.find((r) => r[col] != null);
      return sample ? typeof sample[col] === "number" : false;
    };

    return (
      <div ref={ref} className="overflow-x-auto rounded-lg border border-slate" id="sortable-table">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface border-b border-slate">
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2.5 text-xs font-semibold text-ivory/60 uppercase tracking-wider
                             cursor-pointer hover:text-gold transition-colors select-none font-inter"
                  style={{ textAlign: isNumeric(col) ? "right" : "start" }}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.replace(/_/g, " ")}
                    {sortCol === col && sortDir === "asc" && <ChevronUp size={12} />}
                    {sortCol === col && sortDir === "desc" && <ChevronDown size={12} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayed.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-slate/50 hover:bg-gold/5 transition-colors ${
                  i % 2 === 0 ? "bg-midnight" : "bg-surface/50"
                }`}
              >
                {columns.map((col) => {
                  const val = row[col];
                  const numeric = typeof val === "number";
                  return (
                    <td
                      key={col}
                      className={`px-3 py-2 ${numeric ? "text-right font-mono text-gold/80" : ""}`}
                      dir={numeric ? "ltr" : undefined}
                    >
                      {numeric ? formatNumber(val, language) : String(val ?? "—")}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {hasMore && !showAll && (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="w-full py-2 text-xs text-gold hover:text-gold-light
                       bg-surface border-t border-slate transition-colors"
          >
            {language === "ar"
              ? `عرض الكل (${sorted.length} صف)`
              : `Show all (${sorted.length} rows)`}
          </button>
        )}
      </div>
    );
  },
);

export default SortableTable;
