"use client";

// Wakeel — Customer Support Desk (M3 demo MVP).
// The case flows through a real pipeline: Intake → Draft → Review → Decision.
// One screen tells the whole human-in-the-loop story.

import { useState } from "react";

import CustomerInputForm from "@/components/m3/CustomerInputForm";
import HumanReviewPanel from "@/components/m3/HumanReviewPanel";
import { useM3Support } from "@/hooks/useM3Support";

type Stage = "intake" | "review";

const STEPS = [
  { key: "intake", n: "01", label: "Intake" },
  { key: "draft", n: "02", label: "AI draft" },
  { key: "review", n: "03", label: "Review" },
  { key: "decision", n: "04", label: "Decision" },
] as const;

export default function M3Page() {
  const [stage, setStage] = useState<Stage>("intake");
  const {
    loading,
    error,
    response,
    actionResult,
    submit,
    approve,
    reject,
    escalate,
    reset,
  } = useM3Support();

  // Current step index for the pipeline indicator.
  const stepIndex = actionResult
    ? 3
    : response
    ? 2
    : loading
    ? 1
    : 0;

  async function handleCustomerSubmit(
    query: string,
    identifier: Parameters<typeof submit>[1],
  ) {
    await submit(query, identifier);
    setStage("review");
  }

  return (
    <div className="min-h-screen">
      {/* Brand bar */}
      <header className="bg-petrol-deep text-paper">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3.5">
          <div className="flex items-baseline gap-2.5">
            <span className="font-display text-lg font-bold tracking-tight">
              وكيل
            </span>
            <span className="font-display text-sm font-medium uppercase tracking-[0.2em] text-paper/70">
              Wakeel
            </span>
          </div>
          <div className="flex items-center gap-2 text-paper/80">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber" />
            <span className="code text-[11px] uppercase tracking-wider">
              support desk · live
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-7">
        {/* Pipeline stepper — the case really moves through these stages. */}
        <ol className="mb-7 flex items-center gap-2">
          {STEPS.map((s, i) => {
            const active = i === stepIndex;
            const done = i < stepIndex;
            return (
              <li key={s.key} className="flex flex-1 items-center gap-2">
                <div
                  className={`flex items-center gap-2 rounded-full px-3 py-1.5 transition ${
                    active
                      ? "bg-petrol text-paper"
                      : done
                      ? "bg-petrol/10 text-petrol-deep"
                      : "bg-paper text-sage border border-line"
                  }`}
                >
                  <span className="code text-[11px] font-semibold">{s.n}</span>
                  <span className="text-xs font-medium">{s.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <span
                    className={`h-px flex-1 ${done ? "bg-petrol/40" : "bg-line"}`}
                  />
                )}
              </li>
            );
          })}
        </ol>

        {/* View toggle */}
        <div className="mb-5 flex items-center justify-between">
          <h1 className="font-display text-xl font-semibold text-ink">
            {stage === "intake" ? "Customer intake" : "Agent review"}
          </h1>
          <div className="flex rounded-full border border-line bg-paper p-0.5 text-sm">
            <button
              onClick={() => setStage("intake")}
              className={`rounded-full px-4 py-1.5 font-medium transition ${
                stage === "intake" ? "bg-petrol text-paper" : "text-sage hover:text-ink"
              }`}
            >
              Customer
            </button>
            <button
              onClick={() => setStage("review")}
              disabled={!response}
              className={`rounded-full px-4 py-1.5 font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                stage === "review" ? "bg-petrol text-paper" : "text-sage hover:text-ink"
              }`}
            >
              Agent
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-card border border-alert/40 bg-alert/[0.07] px-4 py-3 text-sm text-alert">
            {error}
          </div>
        )}

        <div className="animate-riseIn rounded-card border border-line bg-paper/60 p-6 shadow-desk backdrop-blur-sm">
          {stage === "intake" && (
            <div className="mx-auto max-w-xl">
              <CustomerInputForm onSubmit={handleCustomerSubmit} loading={loading} />
            </div>
          )}

          {stage === "review" &&
            (!response ? (
              <p className="py-10 text-center text-sm text-sage">
                Submit a case from the customer view to begin a review.
              </p>
            ) : (
              <>
                <div className="mb-5 flex justify-end">
                  <button
                    onClick={() => {
                      reset();
                      setStage("intake");
                    }}
                    className="text-sm font-medium text-petrol hover:text-petrol-deep"
                  >
                    + New case
                  </button>
                </div>
                <HumanReviewPanel
                  response={response}
                  loading={loading}
                  actionResult={actionResult}
                  onApprove={approve}
                  onReject={reject}
                  onEscalate={escalate}
                />
              </>
            ))}
        </div>

        <footer className="mt-6 text-center text-[11px] text-sage">
          The confidence signal and evidence panel are internal — shown to the
          agent only, never to the customer.
        </footer>
      </main>
    </div>
  );
}
