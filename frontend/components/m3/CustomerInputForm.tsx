"use client";

import React, { useState } from "react";
import { Send, Hash, FileText, User } from "lucide-react";
import type { IdentifierType } from "@/types/m3";
import { isArabic } from "@/lib/rtl";

interface Props {
  onSubmit: (type: IdentifierType, value: string, description: string) => void;
  isLoading: boolean;
  language: "ar" | "en";
}

const identifiers: {
  value: IdentifierType;
  icon: React.ElementType;
  labelAr: string;
  labelEn: string;
  placeholder: string;
}[] = [
  { value: "order_id",    icon: Hash,     labelAr: "رقم الطلب",    labelEn: "Order ID",    placeholder: "ORD-2024-1567" },
  { value: "invoice_id",  icon: FileText, labelAr: "رقم الفاتورة", labelEn: "Invoice ID",  placeholder: "INV-890" },
  { value: "customer_id", icon: User,     labelAr: "رقم العميل",   labelEn: "Customer ID", placeholder: "CUST-001" },
];

const t = {
  ar: {
    title: "دعم العملاء",
    subtitle: "اكتب مشكلتك وسنعمل على حلها فوراً",
    idType: "نوع المعرّف",
    idValue: "رقم المعرّف",
    issueLabel: "وصف المشكلة",
    issuePh: "اكتب مشكلتك هنا... مثال: لم أستلم طلبي حتى الآن",
    submit: "إرسال الطلب",
    submitting: "جارٍ المعالجة...",
    hint: "جميع الحقول مطلوبة",
  },
  en: {
    title: "Customer Support",
    subtitle: "Describe your issue and we'll resolve it right away",
    idType: "Identifier Type",
    idValue: "Identifier Value",
    issueLabel: "Issue Description",
    issuePh: "Describe your issue... e.g. I haven't received my order yet",
    submit: "Submit Request",
    submitting: "Processing...",
    hint: "All fields are required",
  },
};

export default function CustomerInputForm({ onSubmit, isLoading, language }: Props) {
  const isAr = language === "ar";
  const tr = t[language];

  const [idType, setIdType] = useState<IdentifierType>("order_id");
  const [idValue, setIdValue] = useState("");
  const [issue, setIssue] = useState("");

  const selected = identifiers.find((o) => o.value === idType)!;
  const canSubmit = idValue.trim() && issue.trim() && !isLoading;
  const issueDir = issue ? (isArabic(issue) ? "rtl" : "ltr") : (isAr ? "rtl" : "ltr");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit(idType, idValue.trim(), issue.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-fade-in">
      <div className="text-center pb-1">
        <h2 className="text-xl font-bold text-ivory font-cairo">{tr.title}</h2>
        <p className="text-sm text-ivory/45 mt-1">{tr.subtitle}</p>
      </div>

      {/* Identifier type selector */}
      <div className="space-y-2">
        <label className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.idType}</label>
        <div className="grid grid-cols-3 gap-2">
          {identifiers.map(({ value, icon: Icon, labelAr, labelEn }) => {
            const active = idType === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => { setIdType(value); setIdValue(""); }}
                className={`flex flex-col items-center gap-1.5 py-3 rounded-lg border text-xs font-medium transition-all ${
                  active
                    ? "border-gold bg-gold/10 text-gold"
                    : "border-slate bg-surface text-ivory/35 hover:text-ivory/60 hover:border-slate-light"
                }`}
              >
                <Icon size={16} />
                {isAr ? labelAr : labelEn}
              </button>
            );
          })}
        </div>
      </div>

      {/* Identifier value */}
      <div className="space-y-2">
        <label className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.idValue}</label>
        <input
          type="text"
          value={idValue}
          onChange={(e) => setIdValue(e.target.value)}
          placeholder={selected.placeholder}
          dir="ltr"
          className="w-full px-4 py-3 rounded-lg bg-surface border border-slate text-ivory placeholder-ivory/20 font-mono text-sm focus:border-gold/50 focus:ring-1 focus:ring-gold/20 focus:outline-none transition-colors"
        />
      </div>

      {/* Issue description */}
      <div className="space-y-2">
        <label className="text-[10px] text-ivory/40 uppercase tracking-widest">{tr.issueLabel}</label>
        <textarea
          value={issue}
          onChange={(e) => setIssue(e.target.value)}
          placeholder={tr.issuePh}
          rows={4}
          dir={issueDir}
          className="w-full px-4 py-3 rounded-lg bg-surface border border-slate text-ivory placeholder-ivory/20 text-sm resize-none focus:border-gold/50 focus:ring-1 focus:ring-gold/20 focus:outline-none transition-colors leading-relaxed"
        />
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-gold text-midnight font-bold text-sm transition-all hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <span className="w-4 h-4 border-2 border-midnight/30 border-t-midnight rounded-full animate-spin" />
            {tr.submitting}
          </>
        ) : (
          <>
            <Send size={15} />
            {tr.submit}
          </>
        )}
      </button>

      <p className="text-center text-[11px] text-ivory/25">{tr.hint}</p>
    </form>
  );
}
