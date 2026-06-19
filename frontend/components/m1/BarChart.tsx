"use client";

import React, { forwardRef, useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { BarChart as EBarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { ChartConfig } from "@/types/m1";

echarts.use([EBarChart, GridComponent, TooltipComponent, TitleComponent, CanvasRenderer]);

/* ─────────────────────────────────────────────────────────────
 * BarChart — ECharts bar chart for categorical comparisons.
 *
 * Horizontal bars for Arabic labels (better RTL readability).
 * Gold/amber bars on dark background.
 * ───────────────────────────────────────────────────────────── */

interface BarChartProps {
  config: ChartConfig;
  language: "ar" | "en";
}

const BarChart = forwardRef<HTMLDivElement, BarChartProps>(
  function BarChart({ config, language }, ref) {
    const isAr = language === "ar";

    const option = useMemo(() => {
      const series = config.series[0];
      if (!series) return {};

      const categories = series.data.map((d) => String(d.x));
      const values = series.data.map((d) => d.y);

      // Use horizontal bars for better label readability
      return {
        backgroundColor: "transparent",
        title: config.title
          ? {
              text: config.title,
              textStyle: { color: "#F8FAFC", fontSize: 14, fontFamily: "Cairo" },
              left: isAr ? "right" : "left",
            }
          : undefined,
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          backgroundColor: "#1E293B",
          borderColor: "#334155",
          textStyle: { color: "#F8FAFC", fontSize: 12 },
          formatter: (params: any) => {
            const p = Array.isArray(params) ? params[0] : params;
            const val = typeof p.value === "number" ? p.value.toLocaleString() : p.value;
            return `<strong>${p.name}</strong><br/>${config.y_axis.label}: ${val}`;
          },
        },
        grid: {
          left: "25%",
          right: "8%",
          top: config.title ? "18%" : "8%",
          bottom: "8%",
        },
        xAxis: {
          type: "value",
          axisLabel: {
            color: "#94A3B8",
            fontSize: 11,
            fontFamily: "JetBrains Mono",
            formatter: (v: number) => v.toLocaleString(),
          },
          splitLine: { lineStyle: { color: "#1E293B" } },
          axisLine: { show: false },
        },
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: {
            color: "#F8FAFC",
            fontSize: 12,
            fontFamily: "Cairo",
            width: 120,
            overflow: "truncate",
          },
          axisLine: { lineStyle: { color: "#334155" } },
        },
        series: [
          {
            name: series.name,
            type: "bar",
            data: values,
            barWidth: "60%",
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: "#B45309" },
                { offset: 1, color: "#F59E0B" },
              ]),
              borderRadius: [0, 4, 4, 0],
            },
            emphasis: {
              itemStyle: { color: "#FCD34D" },
            },
          },
        ],
      };
    }, [config, isAr]);

    const chartHeight = Math.max(200, config.series[0]?.data.length * 40 || 200);

    return (
      <div ref={ref} id="bar-chart">
        <ReactEChartsCore
          echarts={echarts}
          option={option}
          style={{ height: `${chartHeight}px`, width: "100%" }}
          notMerge
          lazyUpdate
        />
      </div>
    );
  },
);

export default BarChart;
