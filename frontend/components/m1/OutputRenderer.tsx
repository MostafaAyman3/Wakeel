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
 * DataVisualization — renders the best data component based
 * on data shape. Used by both normal responses and as a
 * secondary view alongside alert cards.
 * ───────────────────────────────────────────────────────────── */

function DataVisualization({
  dataFormat,
  dataArray,
  chartConfig,
  language,
}: {
  dataFormat: string;
  dataArray: Record<string, unknown>[];
  chartConfig: QueryResponse["chart_config"];
  language: "ar" | "en";
}) {
  if (dataArray.length === 0) return null;

  switch (dataFormat) {
    case "metric_card":
      return <MetricCard data={dataArray} language={language} />;
    case "table":
      return <SortableTable data={dataArray} language={language} />;
    case "line_chart":
      return chartConfig ? <LineChart config={chartConfig} language={language} /> : null;
    case "bar_chart":
      return chartConfig ? <BarChart config={chartConfig} language={language} /> : null;
    default:
      return null;
  }
}

/* ─────────────────────────────────────────────────────────────
 * OutputRenderer — smart router that reads response.format
 * and renders the correct visualization component.
 *
 * When format is "alert", both the alert card AND the
 * underlying data (table/chart) are shown so admin users
 * can inspect the anomalous data directly.
 *
 * Always renders narrative text below the primary visualization.
 * ───────────────────────────────────────────────────────────── */

interface OutputRendererProps {
  response: QueryResponse;
  language: "ar" | "en";
}

export default function OutputRenderer({ response, language }: OutputRendererProps) {
  const { format, data, chart_config, narrative, alert, disclaimer, metadata } = response;

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

  // Determine secondary data format for alert responses
  const alertDataFormat = (metadata as Record<string, unknown>)?.alert_data_format as string | undefined;

  // Infer the best data format when alert_data_format isn't set
  const inferDataFormat = (): string | null => {
    if (dataArray.length === 0) return null;
    const cols = Object.keys(dataArray[0]);
    if (dataArray.length > 5) return "table";
    if (chart_config) return chart_config.chart_type === "line" ? "line_chart" : "bar_chart";
    if (dataArray.length <= 5 && cols.length <= 3) return "table";
    return "table";
  };

  const secondaryFormat = alertDataFormat || (format === "alert" ? inferDataFormat() : null);

  return (
    <div className="space-y-3">
      {/* Alert card — shown first when format is alert */}
      {format === "alert" && alert && (
        <AlertCard alert={alert} language={language} />
      )}

      {/* Primary visualization — for non-alert formats */}
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

      {/* Secondary data visualization — shown below alert card */}
      {format === "alert" && secondaryFormat && dataArray.length > 0 && (
        <DataVisualization
          dataFormat={secondaryFormat === "table" || !chart_config ? "table" : secondaryFormat}
          dataArray={dataArray}
          chartConfig={chart_config}
          language={language}
        />
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


