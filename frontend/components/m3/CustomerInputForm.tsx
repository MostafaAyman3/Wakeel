"use client";

// CustomerInputForm — the intake desk. Customer states their issue and,
// optionally, a reference code. Identifier is optional: the agent parses it
// from the text when omitted.

import { useState } from "react";

import type { CustomerIdentifier, IdentifierType } from "@/types/m3";

interface Props {
  onSubmit: (query: string, identifier: CustomerIdentifier | null) => void;
  loading: boolean;
}

const ID_TYPES: { value: IdentifierType; label: string }[] = [
  { value: "order_id", label: "Order" },
  { value: "invoice_id", label: "Invoice" },
  { value: "customer_id", label: "Customer" },
];

const SAMPLES = [
  { label: "Order status", code: "ORD-2024-1567", query: "Where is my order ORD-2024-1567?", type: "order_id" as IdentifierType, value: "ORD-2024-1567" },
  { label: "Invoice dispute", code: "INV-0001", query: "I did not order this, the invoice is wrong", type: "invoice_id" as IdentifierType, value: "INV-0001" },
  { label: "Repeat issue", code: "CUST-001", query: "أنا عميل قديم وعندي مشكلة متكررة في التوصيل", type: "customer_id" as IdentifierType, value: "CUST-001" },
  { label: "Unknown ref", code: "DEL-999", query: "مشكلة في التوصيلة رقم DEL-999", type: "order_id" as IdentifierType, value: "DEL-999" },
];

export default function CustomerInputForm({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState("");
  const [idType, setIdType] = useState<IdentifierType>("order_id");
  const [idValue, setIdValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim().length < 3) return;
    const identifier = idValue.trim() ? { type: idType, value: idValue.trim() } : null;
    onSubmit(query.trim(), identifier);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">
          How can we help?
        </h2>
        <p className="mt-1 text-sm text-sage">
          Tell us what happened — العربية أو English. A reference code helps but
          isn&apos;t required.
        </p>
      </div>

      {/* Reference */}
      <div>
        <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-petrol-deep">
          Reference <span className="font-normal normal-case text-sage">(optional)</span>
        </label>
        <div className="flex overflow-hidden rounded-card border border-line bg-paper focus-within:border-petrol">
          <div className="flex shrink-0 divide-x divide-line border-r border-line">
            {ID_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setIdType(t.value)}
                className={`px-3 py-2.5 text-xs font-medium transition ${
                  idType === t.value
                    ? "bg-petrol text-paper"
                    : "bg-transparent text-sage hover:bg-sand"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <input
            value={idValue}
            onChange={(e) => setIdValue(e.target.value)}
            placeholder="ORD-2024-1567"
            className="code w-full bg-transparent px-3 py-2.5 text-sm text-ink placeholder:text-sage/50 focus:outline-none"
          />
        </div>
      </div>

      {/* Issue */}
      <div>
        <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-petrol-deep">
          Your issue
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={4}
          placeholder="اكتب مشكلتك هنا…"
          className="w-full rounded-card border border-line bg-paper px-4 py-3 text-sm leading-relaxed text-ink placeholder:text-sage/50 focus:border-petrol focus:outline-none"
        />
      </div>

      {/* Demo presets */}
      <div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.12em] text-sage">
          Demo cases
        </p>
        <div className="grid grid-cols-2 gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s.code}
              type="button"
              onClick={() => {
                setQuery(s.query);
                setIdType(s.type);
                setIdValue(s.value);
              }}
              className="group flex items-center justify-between rounded-card border border-line bg-paper px-3 py-2 text-left transition hover:border-petrol hover:shadow-desk"
            >
              <span className="text-sm font-medium text-ink">{s.label}</span>
              <span className="code text-[11px] text-sage group-hover:text-petrol">
                {s.code}
              </span>
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || query.trim().length < 3}
        className="w-full rounded-card bg-petrol px-4 py-3 font-display text-sm font-semibold text-paper transition hover:bg-petrol-deep disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? "Routing to agent…" : "Submit to support"}
      </button>
    </form>
  );
}
