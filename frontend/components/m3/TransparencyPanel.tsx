"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, FileText, Package, Truck, Clock } from "lucide-react";
import type { TransparencyData } from "@/types/m3";
import { formatCurrency } from "@/lib/rtl";

interface Props {
  data: TransparencyData;
  missingFields: string[];
  language: "ar" | "en";
}

const labels = {
  ar: { title: "البيانات المُستخدمة", invoice: "الفاتورة", order: "الطلب", shipping: "الشحن", history: "السجل", missing: "بيانات ناقصة", none: "—" },
  en: { title: "Data Used by Agent",  invoice: "Invoice",   order: "Order",  shipping: "Shipping", history: "History", missing: "Missing",       none: "—" },
};

function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between gap-3 text-xs">
      <span className="text-ivory/35 shrink-0">{label}</span>
      <span className="text-ivory/75 text-right font-mono truncate">{value ?? "—"}</span>
    </div>
  );
}

function Section({
  icon: Icon, title, available, defaultOpen, children,
}: {
  icon: React.ElementType;
  title: string;
  available: boolean;
  defaultOpen: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen && available);

  return (
    <div className="rounded-lg border border-slate overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-surface hover:bg-slate/40 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon size={13} className={available ? "text-gold" : "text-ivory/20"} />
          <span className={`text-xs font-medium ${available ? "text-ivory/80" : "text-ivory/30"}`}>
            {title}
          </span>
          {!available && (
            <span className="text-[10px] text-red-400/60 bg-red-400/10 px-1.5 rounded">N/A</span>
          )}
        </div>
        {open
          ? <ChevronUp size={12} className="text-ivory/30" />
          : <ChevronDown size={12} className="text-ivory/30" />}
      </button>
      {open && (
        <div className="px-3 py-2.5 space-y-1.5 bg-midnight/50 border-t border-slate">
          {children}
        </div>
      )}
    </div>
  );
}

export default function TransparencyPanel({ data, missingFields, language }: Props) {
  const l = labels[language];

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-ivory/35 uppercase tracking-widest mb-2">{l.title}</p>

      <Section icon={FileText} title={l.invoice} available={!!data.invoice} defaultOpen>
        {data.invoice ? (
          <>
            <Row label="Number" value={data.invoice.number} />
            <Row label="Date"   value={data.invoice.date} />
            <Row label="Amount" value={formatCurrency(data.invoice.amount, language)} />
            <Row label="Status" value={data.invoice.status} />
          </>
        ) : <span className="text-ivory/25 text-xs">{l.none}</span>}
      </Section>

      <Section icon={Package} title={l.order} available={!!data.order} defaultOpen>
        {data.order ? (
          <>
            <Row label="ID"       value={data.order.id} />
            <Row label="Status"   value={data.order.status} />
            <Row label="Delivery" value={data.order.estimated_delivery} />
            {data.order.total_amount != null && (
              <Row label="Total" value={formatCurrency(data.order.total_amount, language)} />
            )}
          </>
        ) : <span className="text-ivory/25 text-xs">{l.none}</span>}
      </Section>

      <Section icon={Truck} title={l.shipping} available={!!data.shipping} defaultOpen={false}>
        {data.shipping ? (
          <>
            <Row label="Carrier"  value={data.shipping.carrier} />
            <Row label="Location" value={data.shipping.location} />
            <Row label="Status"   value={data.shipping.status} />
            <Row label="Updated"  value={data.shipping.last_update} />
          </>
        ) : <span className="text-ivory/25 text-xs">{l.none}</span>}
      </Section>

      <Section icon={Clock} title={l.history} available={!!(data.history?.length)} defaultOpen={false}>
        {data.history && data.history.length > 0 ? (
          data.history.map((h, i) => (
            <div key={i} className={i > 0 ? "border-t border-slate/50 pt-2 mt-2" : ""}>
              <Row label="Date"       value={h.date} />
              <Row label="Issue"      value={h.issue_type} />
              <Row label="Resolution" value={h.resolution} />
            </div>
          ))
        ) : <span className="text-ivory/25 text-xs">{l.none}</span>}
      </Section>

      {missingFields.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[10px] text-red-400/60">{l.missing}:</span>
          {missingFields.map((f) => (
            <span key={f} className="text-[10px] bg-red-400/10 text-red-400/80 px-1.5 py-0.5 rounded font-mono">
              {f}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
