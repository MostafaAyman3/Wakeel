"use client";

import React from "react";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import type { M3Response } from "@/types/m3";
import TransparencyPanel from "./TransparencyPanel";

interface Props {
  response: M3Response;
  language: "ar" | "en";
  onNewCase: () => void;
}

const issueLabels: Record<string, { ar: string; en: string }> = {
  status_inquiry:    { ar: "استفسار عن الحالة",  en: "Status Inquiry" },
  billing_dispute:   { ar: "نزاع في الفاتورة",   en: "Billing Dispute" },
  shipping_issue:    { ar: "مشكلة في الشحن",     en: "Shipping Issue" },
  refund_request:    { ar: "طلب استرداد",         en: "Refund Request" },
  general_complaint: { ar: "شكوى عامة",           en: "General Complaint" },
};

const t = {
  ar: {
    title: "تمت الإحالة للمشرف",
    subtitle: "تمت إحالة هذه الحالة إلى فريق الدعم المتخصص",
    issueType: "نوع المشكلة",
    agentDraft: "مسودة رد الوكيل",
    dataUsed: "البيانات المستخدمة",
    newCase: "حالة جديدة",
  },
  en: {
    title: "Case Escalated",
    subtitle: "This case has been escalated to the support team",
    issueType: "Issue Type",
    agentDraft: "Agent Draft Response",
    dataUsed: "Data Used",
    newCase: "New Case",
  },
};

export default function EscalationView({ response, language, onNewCase }: Props) {
  const isAr = language === "ar";
  const tr = t[language];
  const issueLabel = issueLabels[response.issue_type];

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Banner */}
      <div className="flex items-start gap-4 p-5 rounded-xl bg-amber-500/10 border border-amber-500/25">
        <div className="w-11 h-11 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <AlertTriangle size={20} className="text-amber-400" />
        </div>
        <div>
          <h2 className="text-base font-bold text-amber-300">{tr.title}</h2>
          <p className="text-sm text-ivory/50 mt-0.5">{tr.subtitle}</p>
        </div>
      </div>

      {/* Issue type */}
      {issueLabel && (
        <div className="px-4 py-3 rounded-lg bg-surface border border-slate">
          <p className="text-[10px] text-ivory/35 uppercase tracking-widest mb-1">{tr.issueType}</p>
          <p className="text-sm font-medium text-gold">{isAr ? issueLabel.ar : issueLabel.en}</p>
        </div>
      )}

      {/* Agent draft */}
      <div className="px-4 py-3 rounded-lg bg-surface border border-slate">
        <p className="text-[10px] text-ivory/35 uppercase tracking-widest mb-2">{tr.agentDraft}</p>
        <p
          dir={isAr ? "rtl" : "ltr"}
          className="text-sm text-ivory/75 leading-relaxed whitespace-pre-wrap"
        >
          {response.draft_response}
        </p>
      </div>

      {/* Transparency */}
      <div className="px-4 py-4 rounded-lg bg-surface border border-slate">
        <TransparencyPanel
          data={response.transparency_data}
          missingFields={response.missing_fields}
          language={language}
        />
      </div>

      {/* Back button */}
      <button
        onClick={onNewCase}
        className="flex items-center gap-2 text-sm text-ivory/40 hover:text-ivory/70 transition-colors"
      >
        <ArrowLeft size={14} />
        {tr.newCase}
      </button>
    </div>
  );
}
