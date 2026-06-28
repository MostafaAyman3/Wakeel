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
      if (!config.series || config.series.length === 0) return null;

      const firstSeries = config.series[0];
      if (!firstSeries || !firstSeries.data || firstSeries.data.length === 0) return null;

      // Handle both framework-agnostic (old) and ECharts (new) JSON formats
      const isEchartsFormat = !!(config as any).xAxis;
      const categories = isEchartsFormat ? (config as any).xAxis.data : firstSeries.data.map((d: any) => String(d.x));
      const yAxisLabel = config.y_axis?.label || "";

      const colors = [
        ["#B45309", "#F59E0B"], // Amber/Gold
        ["#0369A1", "#38BDF8"], // Light Blue
        ["#BE185D", "#EC4899"], // Pink
        ["#047857", "#10B981"], // Emerald
        ["#5B21B6", "#8B5CF6"]  // Violet
      ];

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
        legend: config.series.length > 1 ? {
          data: config.series.map(s => s.name),
          textStyle: { color: "#94A3B8", fontFamily: isAr ? "Cairo" : "Inter", fontSize: 11 },
          bottom: 0,
          left: "center",
        } : undefined,
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
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
          right: "8%",
          top: config.title ? "18%" : "8%",
          bottom: config.series.length > 1 ? "14%" : "8%",
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
        series: config.series.map((s, idx) => {
          const colorPair = colors[idx % colors.length];
          const values = isEchartsFormat ? s.data : s.data.map((d: any) => d.y);
          
          return {
            name: s.name,
            type: "bar",
            data: values,
            barWidth: config.series.length > 1 ? "30%" : "55%",
            barMaxWidth: 32,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: colorPair[0] },
                { offset: 1, color: colorPair[1] },
              ]),
              borderRadius: [0, 4, 4, 0],
            },
            emphasis: {
              itemStyle: {
                color: colorPair[1],
                shadowBlur: 8,
                shadowColor: "rgba(245, 158, 11, 0.3)",
              },
            },
          };
        }),
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
