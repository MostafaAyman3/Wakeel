"use client";

// useM3Support — manages the M3 customer-support flow:
//   submit a query -> receive draft + transparency data -> agent review
//   actions (approve / reject+regenerate / escalate).

import { useCallback, useState } from "react";

import { api } from "@/lib/api";
import type {
  CustomerIdentifier,
  ReviewActionResponse,
  SupportRequest,
  SupportResponse,
} from "@/types/m3";

export interface UseM3Support {
  loading: boolean;
  error: string | null;
  response: SupportResponse | null;
  caseId: string | null;
  actionResult: ReviewActionResponse | null;
  submit: (
    query: string,
    identifier?: CustomerIdentifier | null,
    rejectionContext?: Record<string, unknown> | null,
  ) => Promise<void>;
  approve: (draftOverride?: string) => Promise<void>;
  reject: (feedback: string) => Promise<void>;
  escalate: (reason?: string) => Promise<void>;
  reset: () => void;
}

export function useM3Support(): UseM3Support {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SupportResponse | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<ReviewActionResponse | null>(
    null,
  );
  // Remember the last submission so Reject & Regenerate can replay it.
  const [lastRequest, setLastRequest] = useState<{
    query: string;
    identifier: CustomerIdentifier | null;
  } | null>(null);

  const submit = useCallback(
    async (
      query: string,
      identifier?: CustomerIdentifier | null,
      rejectionContext?: Record<string, unknown> | null,
    ) => {
      setLoading(true);
      setError(null);
      setActionResult(null);
      try {
        const payload: SupportRequest = {
          query,
          identifier: identifier ?? null,
          rejection_context: rejectionContext ?? null,
        };
        const res = await api.submitSupport(payload);
        setResponse(res);
        setLastRequest({ query, identifier: identifier ?? null });
        // Derive a case id for review actions (identifier value, else a stamp).
        setCaseId(identifier?.value || `case-${Date.now()}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Request failed");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const approve = useCallback(
    async (draftOverride?: string) => {
      if (!response || !caseId) return;
      setLoading(true);
      setError(null);
      try {
        const result = await api.approve({
          case_id: caseId,
          draft_response: draftOverride ?? response.draft_response,
          issue_type: response.issue_type,
          confidence_score: response.confidence_score,
        });
        setActionResult(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Approve failed");
      } finally {
        setLoading(false);
      }
    },
    [response, caseId],
  );

  const reject = useCallback(
    async (feedback: string) => {
      if (!response || !caseId) return;
      setLoading(true);
      setError(null);
      try {
        const result = await api.reject({
          case_id: caseId,
          draft_response: response.draft_response,
          feedback,
          issue_type: response.issue_type,
          confidence_score: response.confidence_score,
        });
        setActionResult(result);
        // Reject & Regenerate: replay the original query/identifier, this time
        // passing the rejection context so the agent improves the response.
        if (lastRequest) {
          await submit(
            lastRequest.query,
            lastRequest.identifier,
            (result.rejection_context as Record<string, unknown>) ?? {
              feedback,
            },
          );
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Reject failed");
      } finally {
        setLoading(false);
      }
    },
    [response, caseId, submit, lastRequest],
  );

  const escalate = useCallback(
    async (reason?: string) => {
      if (!response || !caseId) return;
      setLoading(true);
      setError(null);
      try {
        const result = await api.escalate({
          case_id: caseId,
          issue_type: response.issue_type,
          confidence_score: response.confidence_score,
          reason: reason ?? "Manual escalation by agent",
        });
        setActionResult(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Escalate failed");
      } finally {
        setLoading(false);
      }
    },
    [response, caseId],
  );

  const reset = useCallback(() => {
    setResponse(null);
    setCaseId(null);
    setActionResult(null);
    setError(null);
  }, []);

  return {
    loading,
    error,
    response,
    caseId,
    actionResult,
    submit,
    approve,
    reject,
    escalate,
    reset,
  };
}
