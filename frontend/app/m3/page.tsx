"use client";

import React from "react";
import Link from "next/link";
import { Languages, CheckCircle2 } from "lucide-react";
import { useM3Support } from "@/hooks/useM3Support";
import { Sidebar } from "@/components/layout/Sidebar";
import CustomerInputForm from "@/components/m3/CustomerInputForm";
import HumanReviewPanel from "@/components/m3/HumanReviewPanel";
import EscalationView from "@/components/m3/EscalationView";

export default function M3Page() {
  const {
    language, setLanguage,
    isLoading, error,
    response, editedDraft, setEditedDraft,
    view,
    submitRequest, approve, reject, escalate, reset,
  } = useM3Support();

  const isAr = language === "ar";

  function toggleLanguage() {
    setLanguage(language === "ar" ? "en" : "ar");
  }

  return (
    <div className="min-h-screen bg-midnight text-ivory font-cairo flex" dir={isAr ? "rtl" : "ltr"}>
      {/* Sidebar navigation */}
      <Sidebar language={language} />

      {/* Page body — offset by sidebar width */}
      <div className="flex-1 flex flex-col ms-14">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-slate bg-surface/80 backdrop-blur-sm sticky top-0 z-30">
          {/* Module tabs */}
          <nav className="flex items-center gap-1">
            <Link
              href="/m1"
              className="px-3 py-1.5 rounded-md text-sm text-ivory/40 hover:text-ivory/70 transition-colors font-inter"
            >
              {isAr ? "المحلل المالي" : "Financial Analyst"}
            </Link>
            <div className="px-3 py-1.5 rounded-md text-sm bg-gold/12 text-gold font-semibold font-inter">
              {isAr ? "دعم العملاء" : "Customer Support"}
            </div>
          </nav>

          {/* Language toggle */}
          <button
            type="button"
            onClick={toggleLanguage}
            className="flex items-center gap-2 text-sm text-ivory/45 hover:text-ivory transition-colors"
          >
            <Languages size={15} />
            <span className="font-inter font-medium">{isAr ? "EN" : "عربي"}</span>
          </button>
        </header>

        {/* Content */}
        <main className="flex-1 flex items-start justify-center px-6 py-10">
          <div className="w-full max-w-2xl">
            {/* Error */}
            {error && (
              <div className="mb-5 px-4 py-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm animate-fade-in">
                {error}
              </div>
            )}

            {/* Card */}
            <div className="bg-surface border border-slate rounded-2xl p-6 shadow-2xl">
              {view === "input" && (
                <CustomerInputForm
                  onSubmit={submitRequest}
                  isLoading={isLoading}
                  language={language}
                />
              )}

              {view === "review" && response && (
                <HumanReviewPanel
                  response={response}
                  editedDraft={editedDraft}
                  onDraftChange={setEditedDraft}
                  onApprove={approve}
                  onReject={reject}
                  onEscalate={escalate}
                  isLoading={isLoading}
                  language={language}
                />
              )}

              {view === "escalation" && response && (
                <EscalationView
                  response={response}
                  language={language}
                  onNewCase={reset}
                />
              )}

              {view === "done" && (
                <div className="flex flex-col items-center justify-center py-14 gap-4 animate-fade-in">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <CheckCircle2 size={32} className="text-emerald-400" />
                  </div>
                  <h2 className="text-xl font-bold">
                    {isAr ? "تم الإرسال بنجاح" : "Response Sent"}
                  </h2>
                  <p className="text-sm text-ivory/45 text-center max-w-xs">
                    {isAr
                      ? "تم إرسال الرد للعميل بنجاح وتسجيله في سجل التدقيق"
                      : "The response has been sent to the customer and logged in the audit trail"}
                  </p>
                  <button
                    onClick={reset}
                    className="mt-2 px-6 py-2.5 rounded-lg bg-gold/10 text-gold border border-gold/20 text-sm font-medium hover:bg-gold/20 transition-colors"
                  >
                    {isAr ? "حالة جديدة" : "New Case"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
