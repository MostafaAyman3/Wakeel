"use client";

import { useState, useCallback } from "react";
import type { M3Response, IdentifierType, RejectionContext } from "@/types/m3";
import { submitSupport, approveSupport, escalateSupport } from "@/lib/m3api";
import { isArabic } from "@/lib/rtl";

export type M3View = "input" | "review" | "escalation" | "done";

interface LastRequest {
  identifierType: IdentifierType;
  identifierValue: string;
  issueDescription: string;
}

export function useM3Support() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<M3Response | null>(null);
  const [editedDraft, setEditedDraft] = useState("");
  const [view, setView] = useState<M3View>("input");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<LastRequest | null>(null);

  const submitRequest = useCallback(
    async (
      identifierType: IdentifierType,
      identifierValue: string,
      issueDescription: string,
      rejectionContext?: RejectionContext,
    ) => {
      setIsLoading(true);
      setError(null);

      const detectedLang = isArabic(issueDescription) ? "ar" : "en";
      setLanguage(detectedLang);
      setLastRequest({ identifierType, identifierValue, issueDescription });

      try {
        const identifier = `${identifierType}:${identifierValue}`;
        const result = await submitSupport(
          issueDescription,
          identifier,
          rejectionContext,
        );
        setResponse(result);
        setEditedDraft(result.draft_response);
        setCaseId((prev) => prev ?? `CASE-${Date.now()}`);
        setView(result.escalation_needed ? "escalation" : "review");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const approve = useCallback(async () => {
    setIsLoading(true);
    try {
      if (caseId) await approveSupport(caseId, editedDraft);
    } finally {
      setIsLoading(false);
      setView("done");
    }
  }, [caseId, editedDraft]);

  const reject = useCallback(
    async (reason: string, feedback: string) => {
      if (!lastRequest || !response) return;
      await submitRequest(
        lastRequest.identifierType,
        lastRequest.identifierValue,
        lastRequest.issueDescription,
        { reason, feedback, previous_draft: response.draft_response },
      );
    },
    [lastRequest, response, submitRequest],
  );

  const escalate = useCallback(async () => {
    setIsLoading(true);
    try {
      if (caseId) await escalateSupport(caseId);
    } finally {
      setIsLoading(false);
      setView("escalation");
    }
  }, [caseId]);

  const reset = useCallback(() => {
    setResponse(null);
    setEditedDraft("");
    setError(null);
    setView("input");
    setCaseId(null);
    setLastRequest(null);
  }, []);

  return {
    language,
    setLanguage,
    isLoading,
    error,
    response,
    editedDraft,
    setEditedDraft,
    view,
    submitRequest,
    approve,
    reject,
    escalate,
    reset,
  };
}
