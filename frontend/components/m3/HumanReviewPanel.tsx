"use client";

// HumanReviewPanel — the agent's desk. Left: the draft to verify, edit, and
// decide on. Right: the evidence and the confidence signal. Three decisions:
// Approve & Send · Reject & Regenerate · Escalate.

import { useEffect, useState } from "react";

import ConfidenceIndicator from "@/components/m3/ConfidenceIndicator";
import TransparencyPanel from "@/components/m3/TransparencyPanel";
import EscalationView from "@/components/m3/EscalationView";
import type { ReviewActionResponse, SupportResponse } from "@/types/m3";

interface Props {
  response: SupportResponse;
  loading: boolean;
  actionResult: ReviewActionResponse | null;
  onApprove: (draft: string) => void;
  onReject: (feedback: string) => void;
  onEscalate: (reason: string) => void;
}

const ACTION_VERB: Record<string, string> = {
  approved: "Sent to customer",
  rejected: "Regenerating",
  escalated: "Escalated",
};

export default function HumanReviewPanel({
  response,
  loading,
  actionResult,
  onApprove,
  onReject,
  onEscalate,
}: Props) {
  const [draft, setDraft] = useState(response.draft_response);
  const [feedback, setFeedback] = useState("");
  const [showReject, setShowReject] = useState(false);

  useEffect(() => {
    setDraft(response.draft_response);
    setShowReject(false);
    setFeedback("");
  }, [response]);

  const isArabic = /[؀-ۿ]/.test(response.draft_response);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.05fr,0.95fr]">
      {/* ── Left: draft + decision ─────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {response.issue_type && (
            <span className="code rounded-full bg-petrol/10 px-2.5 py-1 text-[11px] font-medium text-petrol-deep">
              {response.issue_type}
            </span>
          )}
          {response.review_required && (
            <span className="rounded-full border border-warn/40 bg-warn/10 px-2.5 py-1 text-[11px] font-medium text-warn">
              Review required
            </span>
          )}
          {response.escalation_needed && (
            <span className="rounded-full border border-alert/40 bg-alert/10 px-2.5 py-1 text-[11px] font-medium text-alert">
              Escalation
            </span>
          )}
        </div>

        <div>
          <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-petrol-deep">
            Draft reply <span className="font-normal normal-case text-sage">— editable</span>
          </label>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={9}
            dir={isArabic ? "rtl" : "ltr"}
            className="w-full rounded-card border border-line bg-paper px-4 py-3 text-[15px] leading-relaxed text-ink focus:border-petrol focus:outline-none"
          />
        </div>

        {/* Reject feedback */}
        {showReject && (
          <div className="rounded-card border border-warn/30 bg-warn/[0.06] p-3">
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.12em] text-warn">
              What should change?
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={2}
              placeholder="e.g. Too formal · mention the refund window"
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm focus:border-petrol focus:outline-none"
            />
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => feedback.trim() && onReject(feedback.trim())}
                disabled={loading || !feedback.trim()}
                className="rounded-lg bg-warn px-3 py-1.5 text-sm font-medium text-paper transition hover:brightness-95 disabled:opacity-40"
              >
                Regenerate
              </button>
              <button
                onClick={() => setShowReject(false)}
                className="rounded-lg px-3 py-1.5 text-sm text-sage hover:text-ink"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Decisions */}
        {!actionResult ? (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onApprove(draft)}
              disabled={loading}
              className="flex-1 rounded-card bg-petrol px-4 py-2.5 font-display text-sm font-semibold text-paper transition hover:bg-petrol-deep disabled:opacity-40"
            >
              Approve &amp; send
            </button>
            <button
              onClick={() => setShowReject((v) => !v)}
              disabled={loading}
              className="rounded-card border border-line bg-paper px-4 py-2.5 text-sm font-medium text-ink transition hover:border-warn hover:text-warn disabled:opacity-40"
            >
              Reject
            </button>
            <button
              onClick={() => onEscalate("Manual escalation by agent")}
              disabled={loading}
              className="rounded-card border border-line bg-paper px-4 py-2.5 text-sm font-medium text-ink transition hover:border-alert hover:text-alert disabled:opacity-40"
            >
              Escalate
            </button>
          </div>
        ) : (
          // Decision stamp
          <div className="flex items-center gap-3 rounded-card border border-ok/40 bg-ok/[0.07] px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-ok text-ok">
              ✓
            </span>
            <div>
              <div className="font-display text-sm font-semibold text-ok">
                {ACTION_VERB[actionResult.action] ?? actionResult.action}
              </div>
              {actionResult.escalation_reason && (
                <div className="text-xs text-sage">{actionResult.escalation_reason}</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: confidence + evidence ───────────────────── */}
      <div className="space-y-4 lg:border-l lg:border-line lg:pl-6">
        <div className="flex items-center justify-between rounded-card border border-line bg-paper p-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-petrol-deep">
              Confidence
            </div>
            <div className="mt-0.5 text-[11px] text-sage">Internal · not sent</div>
          </div>
          <ConfidenceIndicator
            score={response.confidence_score}
            label={response.confidence_label}
          />
        </div>

        {response.escalation_needed && (
          <EscalationView summary={response.escalation_summary} />
        )}

        <TransparencyPanel
          data={response.transparency_data}
          missingFields={response.missing_fields}
        />
      </div>
    </div>
  );
}
