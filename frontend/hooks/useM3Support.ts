"use client";

import { useCallback, useRef, useState } from "react";

import { api } from "@/lib/api";
import type {
  CustomerIdentifier,
  ReviewActionResponse,
  SupportRequest,
  SupportResponse,
} from "@/types/m3";
import type { ChatMessage } from "@/types/m1";

// Conversation session id.
//
// Must be a UUID — the backend conversation store parses it with uuid.UUID and
// silently drops memory for any non-UUID value. Persisted in localStorage so the
// same conversation (and its memory) survives a page reload (Feature 005 FR-010);
// "New chat" issues a fresh id.
const SESSION_STORAGE_KEY = "wakeel.m3.session_id";

function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // RFC4122-ish fallback for environments without crypto.randomUUID.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Read the persisted session id, creating and storing one if absent. Returns a
// fresh (non-persisted) id during SSR where localStorage is unavailable.
function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return generateUuid();
  try {
    const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const fresh = generateUuid();
    window.localStorage.setItem(SESSION_STORAGE_KEY, fresh);
    return fresh;
  } catch {
    return generateUuid();
  }
}

// Generate a new session id and persist it ("New chat" → fresh memory).
function resetSessionId(): string {
  const fresh = generateUuid();
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(SESSION_STORAGE_KEY, fresh);
    } catch {
      /* ignore storage failures — memory simply won't persist across reloads */
    }
  }
  return fresh;
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
  const sessionIdRef = useRef<string>(getOrCreateSessionId());
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
          role: "agent",
          content: res.final_response || res.draft_response,
          route: res.route,
          rag_sources: res.rag_sources,
          review_required: res.review_required,
          escalation_needed: res.escalation_needed,
          timestamp: new Date(),
          language: "en",
        } as any);
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
      addMessage({ role: "user", content: text, timestamp: new Date(), language: "en" } as any);
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
    sessionIdRef.current = resetSessionId();
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
