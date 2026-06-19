/* ─────────────────────────────────────────────────────────────
 * M1 Intelligence Agent — TypeScript types
 * Matches backend QueryResponse schema from m1_query.py
 * ───────────────────────────────────────────────────────────── */

export type OutputFormat =
  | "direct_text"
  | "metric_card"
  | "formatted_text_list"
  | "table"
  | "bar_chart"
  | "line_chart"
  | "narrative"
  | "alert"
  | "error";

export interface ChartConfig {
  chart_type: "bar" | "line";
  x_axis: { field: string; label: string };
  y_axis: { field: string; label: string };
  title: string;
  series: Array<{
    name: string;
    data: Array<{ x: string | number; y: number }>;
  }>;
}

export interface AlertPayload {
  severity: "warning" | "critical";
  title: string;
  description: string;
  recommendation: string;
}

export interface QueryResponse {
  format: OutputFormat;
  data: Record<string, unknown>[] | Record<string, unknown> | string | null;
  chart_config: ChartConfig | null;
  narrative: string | null;
  alert: AlertPayload | null;
  disclaimer: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  response?: QueryResponse;
  timestamp: Date;
  language: "ar" | "en";
}

export type AgentStepStatus = "running" | "complete" | "error";
