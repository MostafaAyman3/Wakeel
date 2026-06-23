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
      const series = config.series[0];
      if (!series || !series.data || series.data.length === 0) return null;

      const xData = series.data.map((d) => String(d.x));
      const yData = series.data.map((d) => d.y);

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
        tooltip: {
          trigger: "axis",
          backgroundColor: "#1E293B",
          borderColor: "#334155",
          borderWidth: 1,
          textStyle: { color: "#F8FAFC", fontSize: 12, fontFamily: isAr ? "Cairo" : "Inter" },
          formatter: (params: any) => {
            const p = Array.isArray(params) ? params[0] : params;
            const val = typeof p.value === "number" ? formatValue(p.value) : p.value;
            return `<strong style="color:#F59E0B">${p.name}</strong><br/>${config.y_axis.label}: ${val}`;
          },
          extraCssText: "border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);",
        },
        grid: {
          left: "4%",
          right: "4%",
          top: config.title ? "20%" : "10%",
          bottom: "18%",
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
          name: config.x_axis.label,
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
        series: [
          {
            name: series.name,
            type: "line",
            data: yData,
            smooth: 0.3,
            lineStyle: { color: "#F59E0B", width: 2.5 },
            itemStyle: { color: "#F59E0B", borderWidth: 2, borderColor: "#0A0F1C" },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(245, 158, 11, 0.3)" },
                { offset: 0.7, color: "rgba(245, 158, 11, 0.05)" },
                { offset: 1, color: "rgba(245, 158, 11, 0)" },
              ]),
            },
            symbol: "circle",
            symbolSize: yData.length > 12 ? 4 : 7,
            emphasis: {
              itemStyle: {
                color: "#FCD34D",
                borderColor: "#F59E0B",
                borderWidth: 2,
                shadowBlur: 8,
                shadowColor: "rgba(245, 158, 11, 0.4)",
              },
            },
          },
        ],
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
