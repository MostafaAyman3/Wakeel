// TransparencyPanel — the evidence the agent's draft is built on.
// Four evidence cards (invoice / order / shipping / history). Reference codes
// are set in mono because they are codes. Agent-only.

import type { TransparencyData } from "@/types/m3";

interface Props {
  data: TransparencyData;
  missingFields: string[];
}

function Row({ label, value, mono }: { label: string; value: unknown; mono?: boolean }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex items-baseline justify-between gap-4 py-1">
      <span className="text-xs uppercase tracking-wide text-sage">{label}</span>
      <span
        className={`text-right text-sm font-medium text-ink break-all ${
          mono ? "code" : ""
        }`}
      >
        {String(value)}
      </span>
    </div>
  );
}

function EvidenceCard({
  tag,
  title,
  found,
  children,
}: {
  tag: string;
  title: string;
  found: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-card border bg-paper p-4 transition ${
        found ? "border-line" : "border-dashed border-line/70"
      }`}
    >
      <div className="mb-2 flex items-center justify-between">
        <h4 className="font-display text-sm font-semibold text-ink">{title}</h4>
        <span
          className={`code text-[10px] uppercase tracking-wider ${
            found ? "text-petrol" : "text-sage/70"
          }`}
        >
          {tag} {found ? "•" : "—"}
        </span>
      </div>
      {found ? (
        children
      ) : (
        <p className="text-sm italic text-sage/70">No record</p>
      )}
    </div>
  );
}

export default function TransparencyPanel({ data, missingFields }: Props) {
  const invoice = data.invoice as Record<string, unknown> | null;
  const order = data.order as Record<string, unknown> | null;
  const shippingRaw = data.shipping;
  const shipping = Array.isArray(shippingRaw)
    ? (shippingRaw[0] as Record<string, unknown> | undefined)
    : (shippingRaw as Record<string, unknown> | null);
  const history = data.history ?? [];

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold uppercase tracking-[0.12em] text-petrol-deep">
          Evidence on file
        </h3>
        {missingFields.length > 0 && (
          <span className="code rounded-full border border-amber/40 bg-amber/10 px-2 py-0.5 text-[11px] text-warn">
            gaps: {missingFields.join(" · ")}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <EvidenceCard tag="INV" title="Invoice" found={!!invoice}>
          {invoice && (
            <>
              <Row label="Number" value={invoice.display_id} mono />
              <Row label="Amount" value={invoice.total_amount} mono />
              <Row label="Status" value={invoice.payment_status} />
              <Row label="Customer" value={invoice.customer_name} />
            </>
          )}
        </EvidenceCard>

        <EvidenceCard tag="ORD" title="Order" found={!!order}>
          {order && (
            <>
              <Row label="Order" value={order.display_id} mono />
              <Row label="Status" value={order.status} />
              <Row label="Total" value={order.total_amount} mono />
              <Row label="ETA" value={order.estimated_delivery} mono />
            </>
          )}
        </EvidenceCard>

        <EvidenceCard tag="SHP" title="Shipping" found={!!shipping}>
          {shipping && (
            <>
              <Row label="Tracking" value={shipping.tracking_id} mono />
              <Row label="Carrier" value={shipping.carrier} />
              <Row label="Status" value={shipping.status} />
              <Row label="Location" value={shipping.location} />
            </>
          )}
        </EvidenceCard>

        <EvidenceCard
          tag="HIS"
          title={`History (${history.length})`}
          found={history.length > 0}
        >
          <ul className="space-y-1.5">
            {history.slice(0, 4).map((h, i) => {
              const item = h as Record<string, unknown>;
              return (
                <li key={i} className="text-sm text-ink">
                  <span className="code text-xs text-sage">
                    {String(item.date ?? "").slice(0, 10)}
                  </span>{" "}
                  {String(item.issue_type ?? "?")}
                  <span className="text-sage"> — {String(item.resolution ?? "—")}</span>
                </li>
              );
            })}
          </ul>
        </EvidenceCard>
      </div>
    </section>
  );
}
