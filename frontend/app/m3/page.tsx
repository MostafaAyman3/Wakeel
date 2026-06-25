"use client";

import { useState } from "react";

import { ChatInterface } from "@/components/chat/ChatInterface";
import HumanReviewPanel from "@/components/m3/HumanReviewPanel";
import { useM3Support } from "@/hooks/useM3Support";

type View = "chat" | "review";

export default function M3Page() {
  const [view, setView] = useState<View>("chat");
  const {
    loading,
    error,
    messages,
    response,
    actionResult,
    sendMessage,
    approve,
    reject,
    escalate,
    reset,
  } = useM3Support();

  const hasReview = response?.review_required && !response.escalation_needed;

  return (
    <div className="flex min-h-screen flex-col">
      {/* Brand bar */}
      <header className="bg-petrol-deep text-paper">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3.5">
          <div className="flex items-baseline gap-2.5">
            <span className="font-display text-lg font-bold tracking-tight">وكيل</span>
            <span className="font-display text-sm font-medium uppercase tracking-[0.2em] text-paper/70">
              Wakeel
            </span>
          </div>
          <div className="flex items-center gap-3">
            {hasReview && (
              <span className="flex items-center gap-1.5 rounded-full bg-amber/20 px-3 py-1 text-[11px] font-semibold text-amber">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber" />
                Review pending
              </span>
            )}
            <div className="flex rounded-full border border-paper/20 bg-paper/10 p-0.5 text-sm">
              <button
                onClick={() => setView("chat")}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                  view === "chat" ? "bg-paper text-petrol-deep" : "text-paper/70 hover:text-paper"
                }`}
              >
                Customer
              </button>
              <button
                onClick={() => setView("review")}
                disabled={!response}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  view === "review" ? "bg-paper text-petrol-deep" : "text-paper/70 hover:text-paper"
                }`}
              >
                Agent
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-5 py-6">
        {error && (
          <div className="mb-4 rounded-card border border-alert/40 bg-alert/[0.07] px-4 py-3 text-sm text-alert">
            {error}
          </div>
        )}

        {view === "chat" && (
          <div className="flex flex-1 flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="font-display text-lg font-semibold text-ink">Support Chat</h1>
                <p className="text-xs text-sage">
                  Ask about your order, invoice, policies, or anything else.
                </p>
              </div>
              {messages.length > 0 && (
                <button
                  onClick={reset}
                  className="text-xs font-medium text-petrol hover:text-petrol-deep"
                >
                  + New chat
                </button>
              )}
            </div>
            <div className="flex-1">
              <ChatInterface
                messages={messages}
                loading={loading}
                onSend={sendMessage}
              />
            </div>
          </div>
        )}

        {view === "review" && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h1 className="font-display text-lg font-semibold text-ink">Agent Review</h1>
              <button
                onClick={() => {
                  reset();
                  setView("chat");
                }}
                className="text-sm font-medium text-petrol hover:text-petrol-deep"
              >
                + New case
              </button>
            </div>

            {!response ? (
              <div className="rounded-card border border-line bg-paper/60 px-6 py-12 text-center text-sm text-sage shadow-desk">
                Send a message in the Customer view to generate a case for review.
              </div>
            ) : (
              <div className="rounded-card border border-line bg-paper/60 p-6 shadow-desk backdrop-blur-sm">
                <HumanReviewPanel
                  response={response}
                  loading={loading}
                  actionResult={actionResult}
                  onApprove={approve}
                  onReject={reject}
                  onEscalate={escalate}
                />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
