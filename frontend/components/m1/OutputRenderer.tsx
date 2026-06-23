"use client";

import React from "react";
import dynamic from "next/dynamic";
import type { QueryResponse } from "@/types/m1";
import MetricCard from "@/components/m1/MetricCard";
import SortableTable from "@/components/m1/SortableTable";
import AlertCard from "@/components/m1/AlertCard";
import NarrativeText from "@/components/m1/NarrativeText";

/* ─────────────────────────────────────────────────────────────
 * Dynamic chart imports — ssr: false prevents Next.js from
 * rendering ECharts on the server where browser APIs
 * (Canvas, echarts.graphic.LinearGradient) are unavailable.
 * ───────────────────────────────────────────────────────────── */

const ChartSkeleton = () => (
  <div className="animate-pulse rounded-lg bg-surface border border-slate p-4">
    <div className="h-4 w-1/3 bg-slate rounded mb-4" />
    <div className="flex items-end gap-2 h-[200px]">
      {[60, 80, 45, 90, 70, 55, 85].map((h, i) => (
        <div
          key={i}
          className="flex-1 bg-gold/10 rounded-t"
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
    <div className="h-3 w-full bg-slate/50 rounded mt-3" />
  </div>
);

const LineChart = dynamic(() => import("@/components/m1/LineChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

const BarChart = dynamic(() => import("@/components/m1/BarChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

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

