"use client";

import { useCallback, useRef, useState } from "react";

import { api } from "@/lib/api";
import type {
  CustomerIdentifier,
  ReviewActionResponse,
  SupportRequest,
  SupportResponse,
} from "@/types/m3";
import type { ChatMessage } from "@/components/chat/MessageBubble";

// Stable session id for the lifetime of the page.
function makeSessionId(): string {
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export interface UseM3Support {
  loading: boolean;
  error: string | null;
  messages: ChatMessage[];
  response: SupportResponse | null;
  caseId: string | null;
  actionResult: ReviewActionResponse | null;
  sendMessage: (text: string) => Promise<void>;
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [response, setResponse] = useState<SupportResponse | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<ReviewActionResponse | null>(null);
  const sessionIdRef = useRef<string>(makeSessionId());
  const lastRequestRef = useRef<{ query: string; identifier: CustomerIdentifier | null } | null>(null);

  const addMessage = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { ...msg, id: `${Date.now()}-${Math.random()}` }]);
  }, []);

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
          session_id: sessionIdRef.current,
        };
        const res = await api.submitSupport(payload);
        setResponse(res);
        lastRequestRef.current = { query, identifier: identifier ?? null };
        setCaseId(identifier?.value || `case-${Date.now()}`);

        addMessage({
          role: "assistant",
          content: res.final_response || res.draft_response,
          route: res.route,
          rag_sources: res.rag_sources,
          review_required: res.review_required,
          escalation_needed: res.escalation_needed,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Request failed");
      } finally {
        setLoading(false);
      }
    },
    [addMessage],
  );

  /** Chat-mode: add the user bubble, then call submit. */
  const sendMessage = useCallback(
    async (text: string) => {
      addMessage({ role: "user", content: text });
      await submit(text);
    },
    [addMessage, submit],
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
        if (lastRequestRef.current) {
          await submit(
            lastRequestRef.current.query,
            lastRequestRef.current.identifier,
            (result.rejection_context as Record<string, unknown>) ?? { feedback },
          );
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Reject failed");
      } finally {
        setLoading(false);
      }
    },
    [response, caseId, submit],
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
    setMessages([]);
    setResponse(null);
    setCaseId(null);
    setActionResult(null);
    setError(null);
    sessionIdRef.current = makeSessionId();
  }, []);

  return {
    loading,
    error,
    messages,
    response,
    caseId,
    actionResult,
    sendMessage,
    submit,
    approve,
    reject,
    escalate,
    reset,
  };
}
