"use client";

/* ─────────────────────────────────────────────────────────────
 * useM1Chat — manages chat state + API calls for M1 agent.
 *
 * Provides:
 *   messages      – conversation history
 *   isLoading     – true while waiting for agent response
 *   language      – current language ("ar" | "en")
 *   error         – latest error message (null if none)
 *   sendMessage   – send a query to the agent
 *   clearHistory  – reset conversation
 *   setLanguage   – switch language
 *
 * Multi-turn context:
 *   A sessionId (UUID) is generated on the first message and reused
 *   for all subsequent messages in the same chat window. It is sent
 *   to the backend so conversation turns are persisted in the
 *   `conversations` table, enabling the agent to resolve follow-up
 *   references like "قارنه" or "نفس السنة".
 * ───────────────────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import type { ChatMessage, QueryResponse } from "@/types/m1";
import { queryM1 } from "@/lib/api";
import { isArabic } from "@/lib/rtl";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function generateSessionId(): string {
  // Use crypto.randomUUID() if available (all modern browsers), else fallback
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function useM1Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [error, setError] = useState<string | null>(null);
  // sessionId is null until the first message — generated lazily so each
  // fresh chat window starts a new conversation.
  const [sessionId, setSessionId] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isLoading) return;

      setError(null);

      // Detect language from query text
      const detectedLang = isArabic(query) ? "ar" : "en";

      // Resolve session: reuse existing or generate a new one now
      const currentSessionId = sessionId ?? generateSessionId();
      if (!sessionId) {
        setSessionId(currentSessionId);
      }

      // Add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: query.trim(),
        timestamp: new Date(),
        language: detectedLang,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const response: QueryResponse = await queryM1(
          query.trim(),
          detectedLang,
          currentSessionId,
        );

        // Backend echoes session_id back — sync in case it was auto-generated server-side
        if (response.session_id && response.session_id !== currentSessionId) {
          setSessionId(response.session_id);
        }

        // Add agent response
        const agentMsg: ChatMessage = {
          id: generateId(),
          role: "agent",
          content: response.narrative || "",
          response,
          timestamp: new Date(),
          language: detectedLang,
        };

        setMessages((prev) => [...prev, agentMsg]);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to get response";
        setError(message);

        // Add error as agent message
        const errorMsg: ChatMessage = {
          id: generateId(),
          role: "agent",
          content: message,
          response: {
            format: "error",
            data: null,
            chart_config: null,
            narrative: message,
            alert: null,
            disclaimer: null,
          },
          timestamp: new Date(),
          language: detectedLang,
        };

        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, sessionId],
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
    setSessionId(null); // Reset session — next message starts a new conversation
  }, []);

  return {
    messages,
    isLoading,
    language,
    error,
    sendMessage,
    clearHistory,
    setLanguage,
  };
}
