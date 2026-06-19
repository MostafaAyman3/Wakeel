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
 * ───────────────────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import type { ChatMessage, QueryResponse } from "@/types/m1";
import { queryM1 } from "@/lib/api";
import { isArabic } from "@/lib/rtl";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useM1Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isLoading) return;

      setError(null);

      // Detect language from query text
      const detectedLang = isArabic(query) ? "ar" : "en";

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
        const response: QueryResponse = await queryM1(query.trim(), detectedLang);

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
    [isLoading],
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
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
