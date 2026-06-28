"use client";

import { Bot, User } from "lucide-react";
import type { RouteType } from "@/types/m3";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: RouteType;
  rag_sources?: string[];
  review_required?: boolean;
  escalation_needed?: boolean;
}

const ROUTE_LABEL: Record<RouteType, string> = {
  greeting: "Greeting",
  general_knowledge: "Knowledge",
  customer_issue: "Issue",
  hybrid: "Hybrid",
};

const ROUTE_COLOR: Record<RouteType, string> = {
  greeting: "bg-ok/15 text-ok",
  general_knowledge: "bg-gold/15 text-gold",
  customer_issue: "bg-slate-light/40 text-ivory/70",
  hybrid: "bg-gold/10 text-gold-light",
};

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isArabic = /[؀-ۿ]/.test(message.content);
  const dir = isArabic ? "rtl" : "ltr";

  if (isUser) {
    return (
      <div className="flex animate-fade-in justify-end" dir={dir}>
        <div className="flex max-w-[78%] items-start gap-2.5">
          <div className="bubble-user">
            <p className="text-sm leading-relaxed text-ivory">{message.content}</p>
          </div>
          <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gold/20">
            <User size={14} className="text-gold" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex animate-slide-up justify-start" dir={dir}>
      <div className="flex max-w-[85%] items-start gap-2.5">
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gold">
          <Bot size={14} className="text-midnight" />
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="bubble-agent card-gold-border">
            <p className="text-sm leading-relaxed text-ivory/90">{message.content}</p>
          </div>

          {(message.route || (message.rag_sources && message.rag_sources.length > 0)) && (
            <div className="flex flex-wrap items-center gap-1.5 px-1">
              {message.route && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${ROUTE_COLOR[message.route]}`}
                >
                  {ROUTE_LABEL[message.route]}
                </span>
              )}
              {message.rag_sources && message.rag_sources.length > 0 && (
                <span className="code text-[11px] text-sage">
                  {message.rag_sources.join(" · ")}
                </span>
              )}
            </div>
          )}

          {message.review_required && !message.escalation_needed && (
            <div className="flex items-center gap-1.5 px-1 text-[11px] text-gold">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold" />
              Pending agent review
            </div>
          )}
          {message.escalation_needed && (
            <div className="flex items-center gap-1.5 px-1 text-[11px] text-alert">
              <span className="h-1.5 w-1.5 rounded-full bg-alert" />
              Escalated to senior agent
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
