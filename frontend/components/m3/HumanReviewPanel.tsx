"use client";

import React, { useState } from "react";
import { CheckCircle, XCircle, ArrowUpCircle, Edit3, Eye } from "lucide-react";
import type { M3Response } from "@/types/m3";
import ConfidenceIndicator from "./ConfidenceIndicator";
import TransparencyPanel from "./TransparencyPanel";

interface Props {
  response: M3Response;
  editedDraft: string;
  onDraftChange: (v: string) => void;
  onApprove: () => void;
  onReject: (reason: string, feedback: string) => void;
  onEscalate: () => void;
  isLoading: boolean;
  language: "ar" | "en";
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
    reviewRequired: "مراجعة إلزامية",
    autoSend: "إرسال تلقائي متاح",
    issueType: "نوع المشكلة",
    empOnly: "للموظف فقط",
    draft: "مسودة الرد",
    editHint: "يمكنك تعديل النص قبل الإرسال",
    edit: "تعديل", preview: "معاينة",
    approve: "موافق وإرسال",
    reject: "رفض وإعادة توليد",
    escalate: "إحالة لمشرف",
    rejectTitle: "سبب الرفض",
    reason: "السبب", reasonPh: "لماذا ترفض هذا الرد؟",
    feedback: "ملاحظات", feedbackPh: "ما الذي يجب تحسينه؟",
    confirmReject: "تأكيد الرفض",
    cancel: "إلغاء",
  },
  en: {
    reviewRequired: "Review Required",
    autoSend: "Auto-send Available",
    issueType: "Issue Type",
    empOnly: "Employee only",
    draft: "Draft Response",
    editHint: "You can edit the text before sending",
    edit: "Edit", preview: "Preview",
    approve: "Approve & Send",
    reject: "Reject & Regenerate",
    escalate: "Escalate to Manager",
    rejectTitle: "Rejection Reason",
    reason: "Reason", reasonPh: "Why are you rejecting this response?",
    feedback: "Notes", feedbackPh: "What should be improved?",
    confirmReject: "Confirm Rejection",
    cancel: "Cancel",
  },
};

export default function HumanReviewPanel({
  response, editedDraft, onDraftChange,
  onApprove, onReject, onEscalate,
  isLoading, language,
}: Props) {
  const isAr = language === "ar";
  const tr = t[language];
  const [isEditing, setIsEditing] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState("");

  const issueLabel = issueLabels[response.issue_type];
  const isRequired = response.review_required;

  function handleConfirmReject() {
    if (!reason.trim()) return;
    onReject(reason.trim(), feedback.trim());
    setShowReject(false);
    setReason("");
    setFeedback("");
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Status banner */}
      <div className={`flex items-center justify-between p-4 rounded-xl border ${
        isRequired
          ? "bg-amber-500/10 border-amber-500/25"
          : "bg-emerald-500/10 border-emerald-500/25"
      }`}>
        <div>
          <p className={`text-sm font-semibold ${isRequired ? "text-amber-300" : "text-emerald-300"}`}>
            {isRequired ? tr.reviewRequired : tr.autoSend}
          </p>
          {issueLabel && (
            <p className="text-xs text-ivory/45 mt-0.5">
              {tr.issueType}: {isAr ? issueLabel.ar : issueLabel.en}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] text-ivory/30">{tr.empOnly}</span>
          <ConfidenceIndicator
            score={response.confidence_score}
            label={response.confidence_label}
            language={language}
          />
        </div>
      </div>

      {/* Draft response */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.draft}</span>
          <button
            type="button"
            onClick={() => setIsEditing((v) => !v)}
            className="flex items-center gap-1 text-xs text-ivory/35 hover:text-gold transition-colors"
          >
            {isEditing ? <Eye size={12} /> : <Edit3 size={12} />}
            {isEditing ? tr.preview : tr.edit}
          </button>
        </div>

        {isEditing ? (
          <textarea
            value={editedDraft}
            onChange={(e) => onDraftChange(e.target.value)}
            rows={6}
            dir={isAr ? "rtl" : "ltr"}
            className="w-full px-4 py-3 rounded-lg bg-surface border border-gold/30 text-ivory text-sm resize-none focus:outline-none focus:ring-1 focus:ring-gold/25 leading-relaxed"
          />
        ) : (
          <div
            dir={isAr ? "rtl" : "ltr"}
            className="px-4 py-3 rounded-lg bg-surface border border-slate text-sm text-ivory/80 leading-relaxed whitespace-pre-wrap min-h-[96px]"
          >
            {editedDraft}
          </div>
        )}
        <p className="text-[11px] text-ivory/25">{tr.editHint}</p>
      </div>

      {/* Transparency */}
      <div className="p-4 rounded-xl bg-surface border border-slate">
        <TransparencyPanel
          data={response.transparency_data}
          missingFields={response.missing_fields}
          language={language}
        />
      </div>

      {/* Reject form */}
      {showReject && (
        <div className="p-4 rounded-xl border border-red-400/25 bg-surface space-y-3 animate-fade-in">
          <p className="text-sm font-semibold text-red-400">{tr.rejectTitle}</p>
          <div className="space-y-1.5">
            <label className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.reason}</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={tr.reasonPh}
              className="w-full px-3 py-2 rounded-lg bg-midnight border border-slate text-sm text-ivory placeholder-ivory/20 focus:border-red-400/40 focus:outline-none"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.feedback}</label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={tr.feedbackPh}
              rows={3}
              className="w-full px-3 py-2 rounded-lg bg-midnight border border-slate text-sm text-ivory placeholder-ivory/20 focus:border-red-400/40 focus:outline-none resize-none"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleConfirmReject}
              disabled={!reason.trim() || isLoading}
              className="flex-1 px-4 py-2 rounded-lg bg-red-500/15 border border-red-400/30 text-red-400 text-sm font-medium hover:bg-red-500/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {tr.confirmReject}
            </button>
            <button
              onClick={() => setShowReject(false)}
              className="px-4 py-2 rounded-lg bg-surface border border-slate text-ivory/45 text-sm hover:text-ivory transition-colors"
            >
              {tr.cancel}
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {!showReject && (
        <div className="grid grid-cols-3 gap-2 pt-1">
          <button
            onClick={onApprove}
            disabled={isLoading}
            className="flex flex-col items-center gap-2 py-3 rounded-xl border border-emerald-500/25 bg-emerald-500/8 text-emerald-400 text-xs font-medium hover:bg-emerald-500/15 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <CheckCircle size={20} />
            {tr.approve}
          </button>
          <button
            onClick={() => setShowReject(true)}
            disabled={isLoading}
            className="flex flex-col items-center gap-2 py-3 rounded-xl border border-red-500/25 bg-red-500/8 text-red-400 text-xs font-medium hover:bg-red-500/15 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <XCircle size={20} />
            {tr.reject}
          </button>
          <button
            onClick={onEscalate}
            disabled={isLoading}
            className="flex flex-col items-center gap-2 py-3 rounded-xl border border-amber-500/25 bg-amber-500/8 text-amber-400 text-xs font-medium hover:bg-amber-500/15 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <ArrowUpCircle size={20} />
            {tr.escalate}
          </button>
        </div>
      )}
    </div>
  );
}
