"use client";

import React, { forwardRef, useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart as ELineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { ChartConfig } from "@/types/m1";

// Register ECharts components
echarts.use([ELineChart, GridComponent, TooltipComponent, TitleComponent, CanvasRenderer]);

/* ─────────────────────────────────────────────────────────────
 * LineChart — ECharts line chart for time series data.
 *
 * Reads chart_config from Sprint 5 OutputSelectorNode.
 * Gold line on dark background with formatted tooltips.
 * ───────────────────────────────────────────────────────────── */

interface LineChartProps {
  config: ChartConfig;
  language: "ar" | "en";
}

const LineChart = forwardRef<HTMLDivElement, LineChartProps>(
  function LineChart({ config, language }, ref) {
    const option = useMemo(() => {
      const series = config.series[0];
      if (!series) return {};

      const xData = series.data.map((d) => String(d.x));
      const yData = series.data.map((d) => d.y);

      return {
        backgroundColor: "transparent",
        title: config.title
          ? {
              text: config.title,
              textStyle: { color: "#F8FAFC", fontSize: 14, fontFamily: "Cairo" },
              left: language === "ar" ? "right" : "left",
            }
          : undefined,
        tooltip: {
          trigger: "axis",
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
          left: "12%",
          right: "8%",
          top: config.title ? "18%" : "8%",
          bottom: "15%",
        },
        xAxis: {
          type: "category",
          data: xData,
          axisLabel: {
            color: "#94A3B8",
            fontSize: 11,
            fontFamily: "Inter",
            rotate: xData.length > 8 ? 30 : 0,
          },
          axisLine: { lineStyle: { color: "#334155" } },
          name: config.x_axis.label,
          nameTextStyle: { color: "#94A3B8", fontSize: 11 },
          nameLocation: "center",
          nameGap: 35,
        },
        yAxis: {
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
        series: [
          {
            name: series.name,
            type: "line",
            data: yData,
            smooth: true,
            lineStyle: { color: "#F59E0B", width: 2.5 },
            itemStyle: { color: "#F59E0B" },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(245, 158, 11, 0.25)" },
                { offset: 1, color: "rgba(245, 158, 11, 0)" },
              ]),
            },
            symbol: "circle",
            symbolSize: 6,
          },
        ],
      };
    }, [config, language]);

    return (
      <div ref={ref} id="line-chart">
        <ReactEChartsCore
          echarts={echarts}
          option={option}
          style={{ height: "280px", width: "100%" }}
          notMerge
          lazyUpdate
        />
      </div>
    );
  },
);

export default LineChart;
