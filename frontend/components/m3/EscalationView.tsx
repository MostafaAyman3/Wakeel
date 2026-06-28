// EscalationView — escalated-case summary for the supervisor: who, what, which
// evidence was found, and why it was routed up.

interface Props {
  summary: Record<string, unknown>;
}

export default function EscalationView({ summary }: Props) {
  if (!summary || Object.keys(summary).length === 0) return null;

  const identifier = summary.identifier as { type?: string; value?: string } | undefined;
  const dataSummary = (summary.data_summary as Record<string, boolean>) ?? {};
  const reason = String(summary.escalation_reason ?? "—");
  const issueType = String(summary.issue_type ?? "—");
  const description = String(summary.issue_description ?? "");

  return (
    <div className="overflow-hidden rounded-card border border-amber/40 bg-amber/[0.07]">
      <div className="flex items-center gap-2 border-b border-amber/30 bg-amber/10 px-4 py-2.5">
        <span className="code text-[11px] font-semibold uppercase tracking-[0.14em] text-warn">
          ▲ Escalated to supervisor
        </span>
      </div>

      <div className="space-y-2.5 p-4">
        <div className="flex justify-between gap-4">
          <span className="text-xs uppercase tracking-wide text-sage">Reference</span>
          <span className="code text-sm font-medium text-ink">
            {identifier?.value ?? "—"}
            <span className="text-sage"> · {identifier?.type ?? "—"}</span>
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-xs uppercase tracking-wide text-sage">Issue</span>
          <span className="text-sm font-medium text-ink">{issueType}</span>
        </div>
        {description && (
          <div className="flex justify-between gap-4">
            <span className="text-xs uppercase tracking-wide text-sage">Summary</span>
            <span className="text-right text-sm text-ink">{description}</span>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <span className="text-xs uppercase tracking-wide text-sage">Reason</span>
          <span className="text-right text-sm font-medium text-warn">{reason}</span>
        </div>

        <div className="flex flex-wrap gap-1.5 pt-1">
          {Object.entries(dataSummary).map(([k, found]) => (
            <span
              key={k}
              className={`code rounded px-2 py-0.5 text-[11px] ${
                found
                  ? "bg-ok/10 text-ok"
                  : "bg-sand text-sage line-through"
              }`}
            >
              {k}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
