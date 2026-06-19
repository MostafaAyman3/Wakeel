"use client";

import React from "react";
import type { QueryResponse } from "@/types/m1";
import MetricCard from "@/components/m1/MetricCard";
import SortableTable from "@/components/m1/SortableTable";
import LineChart from "@/components/m1/LineChart";
import BarChart from "@/components/m1/BarChart";
import AlertCard from "@/components/m1/AlertCard";
import NarrativeText from "@/components/m1/NarrativeText";

/* ─────────────────────────────────────────────────────────────
 * OutputRenderer — smart router that reads response.format
 * and renders the correct visualization component.
 *
 * Always renders narrative text below the primary visualization.
 * ───────────────────────────────────────────────────────────── */

interface OutputRendererProps {
  response: QueryResponse;
  language: "ar" | "en";
}

export default function OutputRenderer({ response, language }: OutputRendererProps) {
  const { format, data, chart_config, narrative, alert, disclaimer } = response;

  // Error state
  if (format === "error") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-danger text-sm">
          <span>⚠</span>
          <span className="font-semibold">
            {language === "ar" ? "حدث خطأ" : "An error occurred"}
          </span>
        </div>
        {narrative && (
          <p className="text-sm text-ivory/60 leading-relaxed">{narrative}</p>
        )}
      </div>
    );
  }

  const dataArray: Record<string, unknown>[] = Array.isArray(data)
    ? data.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    : typeof data === "object" && data !== null
      ? [data as Record<string, unknown>]
      : [];

  return (
    <div className="space-y-3">
      {/* Primary visualization */}
      {format === "metric_card" && (
        <MetricCard data={dataArray} language={language} />
      )}

      {format === "table" && (
        <SortableTable data={dataArray} language={language} />
      )}

      {format === "line_chart" && chart_config && (
        <LineChart config={chart_config} language={language} />
      )}

      {format === "bar_chart" && chart_config && (
        <BarChart config={chart_config} language={language} />
      )}

      {format === "alert" && alert && (
        <AlertCard alert={alert} language={language} />
      )}

      {/* Narrative text — always shown if present */}
      {narrative && (
        <NarrativeText
          text={narrative}
          format={format}
          language={language}
          disclaimer={disclaimer}
        />
      )}

      {/* Fallback: show data as formatted text for direct_text / formatted_text_list */}
      {(format === "direct_text" || format === "formatted_text_list") &&
        !narrative &&
        dataArray.length > 0 && (
          <div className="text-sm text-ivory/80 leading-relaxed">
            {dataArray.map((row, i) => (
              <p key={i}>
                {Object.entries(row)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" | ")}
              </p>
            ))}
          </div>
        )}
    </div>
  );
}
