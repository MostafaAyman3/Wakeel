import type { M3Response, RejectionContext } from "@/types/m3";
import { getAuthToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

async function authHeaders() {
  const token = await getAuthToken();
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function submitSupport(
  query: string,
  identifier?: string,
  rejectionContext?: RejectionContext,
): Promise<M3Response> {
  const res = await fetch(`${API_BASE}/api/v1/support`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({
      query,
      identifier,
      rejection_context: rejectionContext ?? null,
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Server error (${res.status}): ${text}`);
  }

  return res.json();
}

export async function approveSupport(
  caseId: string,
  finalResponse: string,
): Promise<void> {
  await fetch(`${API_BASE}/api/v1/support/approve`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ case_id: caseId, final_response: finalResponse }),
  });
}

export async function rejectSupport(
  caseId: string,
  reason: string,
  feedback: string,
  previousDraft: string,
): Promise<void> {
  await fetch(`${API_BASE}/api/v1/support/reject`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({
      case_id: caseId,
      reason,
      feedback,
      previous_draft: previousDraft,
    }),
  });
}

export async function escalateSupport(caseId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/support/escalate`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ case_id: caseId }),
  });
}
