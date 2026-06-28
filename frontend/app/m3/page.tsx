"use client";

import { useState } from "react";
import { Languages } from "lucide-react";

import { Sidebar } from "@/components/layout/Sidebar";
import { ChatInterface } from "@/components/chat/ChatInterface";
import HumanReviewPanel from "@/components/m3/HumanReviewPanel";
import { useM3Support } from "@/hooks/useM3Support";

type View = "chat" | "review";

export default function M3Page() {
  const [view, setView] = useState<View>("chat");
  const [language, setLanguage] = useState<"ar" | "en">("en");
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
  const isAr = language === "ar";

  return (
    <div className="min-h-screen bg-midnight">
      <Sidebar language={language} />

      <div className="ps-14">
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate bg-surface/80 px-6 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold">
              <span className="font-cairo text-sm font-bold text-midnight">و</span>
            </div>
            <div>
              <h1 className="font-cairo text-lg font-bold leading-none text-ivory">
                {isAr ? "وكيل" : "Wakeel"}
              </h1>
              <p className="font-inter text-xs text-ivory/40">
                {isAr ? "دعم العملاء الذكي" : "AI Customer Support"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {hasReview && (
              <span className="flex items-center gap-1.5 rounded-full bg-gold/15 px-3 py-1 text-[11px] font-semibold text-gold">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold" />
                {isAr ? "بانتظار المراجعة" : "Review pending"}
              </span>
            )}

            {/* View toggle */}
            <div className="flex rounded-full border border-slate bg-midnight p-0.5 text-sm">
              <button
                onClick={() => setView("chat")}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                  view === "chat" ? "bg-gold text-midnight" : "text-ivory/50 hover:text-ivory"
                }`}
              >
                {isAr ? "العميل" : "Customer"}
              </button>
              <button
                onClick={() => setView("review")}
                disabled={!response}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  view === "review" ? "bg-gold text-midnight" : "text-ivory/50 hover:text-ivory"
                }`}
              >
                {isAr ? "الموظف" : "Agent"}
              </button>
            </div>

            <button
              type="button"
              onClick={() => setLanguage((l) => (l === "ar" ? "en" : "ar"))}
              className="btn-ghost flex items-center gap-2 text-sm"
              aria-label="Toggle language"
            >
              <Languages size={16} />
              <span className="font-inter font-medium">{isAr ? "EN" : "عربي"}</span>
            </button>
          </div>
        </header>

        <main className="mx-auto flex min-h-[calc(100vh-57px)] w-full max-w-3xl flex-col px-5 py-6">
          {error && (
            <div className="mb-4 rounded-card border border-alert/40 bg-alert/10 px-4 py-3 text-sm text-alert">
              {error}
            </div>
          )}

          {view === "chat" && (
            <div className="flex flex-1 flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-cairo text-lg font-semibold text-ivory">
                    {isAr ? "محادثة الدعم" : "Support Chat"}
                  </h2>
                  <p className="text-xs text-sage">
                    {isAr
                      ? "اسأل عن طلبك أو فاتورتك أو السياسات."
                      : "Ask about your order, invoice, policies, or anything else."}
                  </p>
                </div>
                {messages.length > 0 && (
                  <button onClick={reset} className="text-xs font-medium text-gold hover:text-gold-light">
                    + {isAr ? "محادثة جديدة" : "New chat"}
                  </button>
                )}
              </div>
              <div className="flex-1">
                <ChatInterface messages={messages} loading={loading} onSend={sendMessage} />
              </div>
            </div>
          )}

          {view === "review" && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="font-cairo text-lg font-semibold text-ivory">
                  {isAr ? "مراجعة الموظف" : "Agent Review"}
                </h2>
                <button
                  onClick={() => {
                    reset();
                    setView("chat");
                  }}
                  className="text-sm font-medium text-gold hover:text-gold-light"
                >
                  + {isAr ? "حالة جديدة" : "New case"}
                </button>
              </div>

              {!response ? (
                <div className="card-base px-6 py-12 text-center text-sm text-sage shadow-desk">
                  {isAr
                    ? "ابدأ محادثة من واجهة العميل لإنشاء حالة للمراجعة."
                    : "Send a message in the Customer view to generate a case for review."}
                </div>
              ) : (
                <div className="card-base p-6 shadow-desk">
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
    </div>
  );
}
