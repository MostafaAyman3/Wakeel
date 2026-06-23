"use client";

import React, { forwardRef, useMemo, useRef } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import type { ChartConfig } from "@/types/m1";

/* ─────────────────────────────────────────────────────────────
 * BarChart — ECharts bar chart for categorical comparisons.
 *
 * Horizontal bars for Arabic labels (better RTL readability).
 * Gold/amber bars on dark background.
 *
 * SSR-safe: This component is loaded via next/dynamic with
 * ssr: false from OutputRenderer, so echarts.graphic is
 * always available here.
 * ───────────────────────────────────────────────────────────── */

interface BarChartProps {
  config: ChartConfig;
  language: "ar" | "en";
}

const BarChart = forwardRef<HTMLDivElement, BarChartProps>(
  function BarChart({ config, language }, ref) {
    const isAr = language === "ar";
    const chartRef = useRef<any>(null);

    const formatValue = (v: number): string => {
      if (typeof v !== "number" || isNaN(v)) return String(v);
      return v.toLocaleString(isAr ? "ar-EG" : "en-US");
    };

    const option = useMemo(() => {
      const series = config.series[0];
      if (!series || !series.data || series.data.length === 0) return null;

      const categories = series.data.map((d) => String(d.x));
      const values = series.data.map((d) => d.y);

      // Use horizontal bars for better label readability
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
          axisPointer: { type: "shadow" },
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
          right: "8%",
          top: config.title ? "18%" : "8%",
          bottom: "8%",
          containLabel: true,
        },
        xAxis: {
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
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: {
            color: "#F8FAFC",
            fontSize: 11,
            fontFamily: isAr ? "Cairo" : "Inter",
            width: 140,
            overflow: "truncate",
          },
          axisLine: { lineStyle: { color: "#334155" } },
          axisTick: { show: false },
        },
        series: [
          {
            name: series.name,
            type: "bar",
            data: values,
            barWidth: "55%",
            barMaxWidth: 32,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: "#B45309" },
                { offset: 1, color: "#F59E0B" },
              ]),
              borderRadius: [0, 4, 4, 0],
            },
            emphasis: {
              itemStyle: {
                color: "#FCD34D",
                shadowBlur: 8,
                shadowColor: "rgba(245, 158, 11, 0.3)",
              },
            },
          },
        ],
        animation: true,
        animationDuration: 600,
        animationEasing: "cubicOut",
      };
    }, [config, isAr]);

    const dataCount = config.series[0]?.data?.length ?? 0;
    const chartHeight = Math.max(200, Math.min(400, dataCount * 42));

    if (!option) {
      return (
        <div ref={ref} className="text-sm text-ivory/40 text-center py-8">
          {isAr ? "لا توجد بيانات لعرض الرسم" : "No data available for chart"}
        </div>
      );
    }

    return (
      <div ref={ref} id="bar-chart" className="w-full">
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

export default BarChart;
