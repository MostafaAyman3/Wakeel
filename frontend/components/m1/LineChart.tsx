"use client";

import React, { forwardRef, useMemo, useRef, useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import type { ChartConfig } from "@/types/m1";

/* ─────────────────────────────────────────────────────────────
 * LineChart — ECharts line chart for time series data.
 *
 * Reads chart_config from Sprint 5 OutputSelectorNode.
 * Gold line on dark background with formatted tooltips.
 *
 * SSR-safe: This component is loaded via next/dynamic with
 * ssr: false from OutputRenderer, so echarts.graphic is
 * always available here.
 * ───────────────────────────────────────────────────────────── */

interface LineChartProps {
  config: ChartConfig;
  language: "ar" | "en";
}

const LineChart = forwardRef<HTMLDivElement, LineChartProps>(
  function LineChart({ config, language }, ref) {
    const isAr = language === "ar";
    const chartRef = useRef<any>(null);

    // Format numbers based on language — locale-aware
    const formatValue = (v: number): string => {
      if (typeof v !== "number" || isNaN(v)) return String(v);
      return v.toLocaleString(isAr ? "ar-EG" : "en-US");
    };

    const option = useMemo(() => {
      if (!config.series || config.series.length === 0) return null;

      const firstSeries = config.series[0];
      if (!firstSeries || !firstSeries.data || firstSeries.data.length === 0) return null;

      // Handle both framework-agnostic (old) and ECharts (new) JSON formats
      const isEchartsFormat = !!(config as any).xAxis;
      const xData = isEchartsFormat ? (config as any).xAxis.data : firstSeries.data.map((d: any) => String(d.x));
      const xAxisLabel = config.x_axis?.label || "";
      const yAxisLabel = config.y_axis?.label || "";

      const colors = ["#F59E0B", "#38BDF8", "#EC4899", "#10B981", "#8B5CF6"];

      return {
        backgroundColor: "transparent",
        title: config.title
          ? {
              text: config.title,
              textStyle: {
                color: "#F8FAFC",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: isAr ? "Cairo" : "Inter",
              },
              left: isAr ? "right" : "left",
              top: 0,
            }
          : undefined,
        legend: config.series.length > 1 ? {
          data: config.series.map(s => s.name),
          textStyle: { color: "#94A3B8", fontFamily: isAr ? "Cairo" : "Inter", fontSize: 11 },
          bottom: 0,
          left: "center",
        } : undefined,
        tooltip: {
          trigger: "axis",
          backgroundColor: "#1E293B",
          borderColor: "#334155",
          borderWidth: 1,
          textStyle: { color: "#F8FAFC", fontSize: 12, fontFamily: isAr ? "Cairo" : "Inter" },
          formatter: (params: any) => {
            const list = Array.isArray(params) ? params : [params];
            if (list.length === 0) return "";
            
            let html = `<strong style="color:#F8FAFC">${list[0].name}</strong><br/>`;
            list.forEach((p: any) => {
              const val = typeof p.value === "number" ? formatValue(p.value) : (p.value ?? "—");
              html += `${p.marker} ${p.seriesName}: <strong style="color:#F8FAFC">${val}</strong><br/>`;
            });
            return html;
          },
          extraCssText: "border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);",
        },
        grid: {
          left: "4%",
          right: "4%",
          top: config.title ? "20%" : "10%",
          bottom: config.series.length > 1 ? "24%" : "18%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: xData,
          axisLabel: {
            color: "#94A3B8",
            fontSize: 10,
            fontFamily: isAr ? "Cairo" : "Inter",
            rotate: xData.length > 6 ? 25 : 0,
            hideOverlap: true,
          },
          axisLine: { lineStyle: { color: "#334155" } },
          axisTick: { show: false },
          name: xAxisLabel,
          nameTextStyle: { color: "#64748B", fontSize: 10, fontFamily: isAr ? "Cairo" : "Inter" },
          nameLocation: "center",
          nameGap: xData.length > 6 ? 45 : 30,
        },
        yAxis: {
          type: "value",
          axisLabel: {
            color: "#94A3B8",
            fontSize: 10,
            fontFamily: "JetBrains Mono",
            formatter: (v: number) => {
              if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
              if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
              return formatValue(v);
            },
          },
          splitLine: { lineStyle: { color: "#1E293B", type: "dashed" as const } },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        series: config.series.map((s, idx) => {
          const color = colors[idx % colors.length];
          let yData = isEchartsFormat ? s.data : s.data.map((d: any) => d.y);
          
          // Sanitize: remove commas and parse to float if string (LLM sometimes formats numbers)
          yData = yData.map((v: any) => {
            if (typeof v === "string") {
              const parsed = parseFloat(v.replace(/,/g, ""));
              return isNaN(parsed) ? v : parsed;
            }
            return v;
          });
          
          return {
            name: s.name,
            type: "line",
            data: yData,
            smooth: 0.3,
            lineStyle: { color, width: 2.5 },
            itemStyle: { color, borderWidth: 2, borderColor: "#0A0F1C" },
            areaStyle: config.series.length === 1 ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(245, 158, 11, 0.3)" },
                { offset: 0.7, color: "rgba(245, 158, 11, 0.05)" },
                { offset: 1, color: "rgba(0,0,0,0)" },
              ]),
            } : undefined,
            symbol: "circle",
            symbolSize: yData.length > 12 ? 4 : 7,
            emphasis: {
              itemStyle: {
                color: "#FCD34D",
                borderColor: color,
                borderWidth: 2,
                shadowBlur: 8,
                shadowColor: "rgba(245, 158, 11, 0.4)",
              },
            },
          };
        }),
        animation: true,
        animationDuration: 800,
        animationEasing: "cubicOut",
      };
    }, [config, isAr]);

    // Dynamic height — more data points = taller chart
    const dataCount = config.series[0]?.data?.length ?? 0;
    const chartHeight = Math.max(220, Math.min(320, 200 + dataCount * 10));

    if (!option) {
      return (
        <div ref={ref} className="text-sm text-ivory/40 text-center py-8">
          {isAr ? "لا توجد بيانات لعرض الرسم" : "No data available for chart"}
        </div>
      );
    }

    return (
      <div ref={ref} id="line-chart" className="w-full">
        <ReactECharts
          ref={chartRef}
          option={option}
          style={{ height: `${chartHeight}px`, width: "100%" }}
          notMerge
          lazyUpdate
          opts={{ renderer: "canvas" }}
        />
      </div>
    );
  },
);

export default LineChart;
