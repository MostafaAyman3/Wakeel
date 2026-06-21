/* ─────────────────────────────────────────────────────────────
 * API client for M1 Intelligence Agent.
 *
 * Sends queries to POST /api/v1/query with Bearer token.
 * Uses Next.js rewrite proxy (defined in next.config.mjs)
 * so the browser talks to the same origin — no CORS issues.
 * ───────────────────────────────────────────────────────────── */

import type { QueryResponse } from "@/types/m1";
import { getAuthToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

/**
 * Send a natural-language query to the M1 agent.
 *
 * @param query      User question (Arabic or English)
 * @param language   "ar" | "en" | "auto"
 * @param sessionId  Optional UUID to link to an ongoing conversation
 * @returns QueryResponse from the backend
 */
export async function queryM1(
  query: string,
  language: string = "auto",
  sessionId?: string,
): Promise<QueryResponse> {
  const token = await getAuthToken();

  try {
    const res = await fetch(`${API_BASE}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, language, session_id: sessionId ?? null }),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unknown error");
      return {
        format: "error",
        data: null,
        chart_config: null,
        narrative: `Server error (${res.status}): ${errorText}`,
        alert: null,
        disclaimer: null,
      };
    }

    const data: QueryResponse = await res.json();
    return data;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Network request failed";
    return {
      format: "error",
      data: null,
      chart_config: null,
      narrative: `Connection error: ${message}`,
      alert: null,
      disclaimer: null,
    };
  }
}
