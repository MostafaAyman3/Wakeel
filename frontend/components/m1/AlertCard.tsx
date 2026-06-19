"use client";

import React, { forwardRef } from "react";
import { AlertTriangle, AlertOctagon } from "lucide-react";
import type { AlertPayload } from "@/types/m1";

/* ─────────────────────────────────────────────────────────────
 * AlertCard — colored alert for anomaly detection.
 *
 * Critical: red border with pulse animation + octagon icon.
 * Warning:  amber border + triangle icon.
 * forwardRef for shadcn swap.
 * ───────────────────────────────────────────────────────────── */

interface AlertCardProps {
  alert: AlertPayload;
  language: "ar" | "en";
}

const AlertCard = forwardRef<HTMLDivElement, AlertCardProps>(
  function AlertCard({ alert, language }, ref) {
    const isCritical = alert.severity === "critical";
    const Icon = isCritical ? AlertOctagon : AlertTriangle;

    return (
      <div
        ref={ref}
        className={`card-base border-2 ${
          isCritical ? "alert-critical border-danger" : "alert-warning border-warning"
        }`}
        id="alert-card"
        role="alert"
      >
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          <div
            className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
              isCritical ? "bg-danger/20" : "bg-warning/20"
            }`}
          >
            <Icon
              size={20}
              className={isCritical ? "text-danger" : "text-warning"}
            />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-xs font-semibold uppercase tracking-wider font-inter ${
                  isCritical ? "text-danger" : "text-warning"
                }`}
              >
                {isCritical
                  ? language === "ar" ? "تنبيه حرج" : "Critical Alert"
                  : language === "ar" ? "تحذير" : "Warning"}
              </span>
            </div>
            <h3 className="text-sm font-bold font-cairo text-ivory">
              {alert.title}
            </h3>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-ivory/70 leading-relaxed mb-3 font-cairo">
          {alert.description}
        </p>

        {/* Recommendation */}
        <div className="bg-midnight/50 rounded-lg px-3 py-2 border border-slate/50">
          <p className="text-xs text-ivory/40 font-inter mb-1">
            {language === "ar" ? "التوصية" : "Recommendation"}
          </p>
          <p className="text-sm text-gold font-cairo">
            {alert.recommendation}
          </p>
        </div>
      </div>
    );
  },
);

export default AlertCard;
