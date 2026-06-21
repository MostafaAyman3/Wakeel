// ConfidenceIndicator — the desk's signature element.
// Confidence rendered as a 5-segment "signal strength" meter: how strongly the
// AI draft is backed by retrieved evidence. Agent-only — never shown to the
// customer.

import type { ConfidenceLabel } from "@/types/m3";

interface Props {
  score: number;
  label: ConfidenceLabel;
}

const TONE: Record<ConfidenceLabel, { on: string; text: string }> = {
  High: { on: "bg-ok", text: "text-ok" },
  Medium: { on: "bg-warn", text: "text-warn" },
  Low: { on: "bg-alert", text: "text-alert" },
};

export default function ConfidenceIndicator({ score, label }: Props) {
  const pct = Math.round(score * 100);
  const filled = Math.max(1, Math.min(5, Math.ceil(score * 5)));
  const tone = TONE[label] ?? TONE.Low;

  return (
    <div
      className="flex items-end gap-3"
      title="Evidence signal — how strongly the draft is backed by data. Internal only."
    >
      {/* Signal bars */}
      <div className="flex items-end gap-1" aria-hidden>
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={`signal-seg w-1.5 animate-segIn ${
              i < filled ? tone.on : "bg-line"
            }`}
            style={{
              height: `${8 + i * 5}px`,
              animationDelay: `${i * 60}ms`,
            }}
          />
        ))}
      </div>

      <div className="leading-none">
        <div className={`code text-base font-semibold ${tone.text}`}>{pct}%</div>
        <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-sage">
          {label} signal
        </div>
      </div>
    </div>
  );
}
