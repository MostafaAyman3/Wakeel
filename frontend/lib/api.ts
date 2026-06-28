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

import type {
  SupportRequest,
  SupportResponse,
  ReviewActionResponse,
} from "@/types/m3";

const TOKEN_KEY = "wakeel_token";

// Demo credentials — MVP only (matches backend/api/v1/auth.py).
const DEMO_EMAIL = "agent@demo.com";
const DEMO_PASSWORD = "demo1234";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function login(
  email: string = DEMO_EMAIL,
  password: string = DEMO_PASSWORD,
  role: string = "agent",
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, role }),
  });
  if (!res.ok) {
    throw new Error(`Login failed (${res.status})`);
  }
  const data = (await res.json()) as { access_token: string };
  setToken(data.access_token);
  return data.access_token;
}

/** Ensure a token exists, performing a demo login if needed. */
async function ensureAuth(): Promise<string> {
  const existing = getToken();
  if (existing) return existing;
  return login();
}

/** Authenticated request — used for agent-only review actions. */
async function request<T>(path: string, body: unknown): Promise<T> {
  let token = await ensureAuth();

  const doFetch = (authToken: string) =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify(body),
    });

  let res = await doFetch(token);

  if (res.status === 401) {
    clearToken();
    token = await login();
    res = await doFetch(token);
  }

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request to ${path} failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as T;
}

/** Public request — no auth header (customer-facing /support endpoint). */
async function publicRequest<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request to ${path} failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  submitSupport: (payload: SupportRequest) =>
    publicRequest<SupportResponse>("/api/v1/support", payload),

  approve: (payload: {
    case_id: string;
    draft_response: string;
    issue_type?: string | null;
    confidence_score?: number;
  }) => request<ReviewActionResponse>("/api/v1/support/approve", payload),

  reject: (payload: {
    case_id: string;
    draft_response: string;
    feedback: string;
    issue_type?: string | null;
    confidence_score?: number;
  }) => request<ReviewActionResponse>("/api/v1/support/reject", payload),

  escalate: (payload: {
    case_id: string;
    issue_type?: string | null;
    confidence_score?: number;
    reason?: string;
  }) => request<ReviewActionResponse>("/api/v1/support/escalate", payload),
};
