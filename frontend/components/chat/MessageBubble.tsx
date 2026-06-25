"use client";

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
  greeting: "bg-green-100 text-green-800",
  general_knowledge: "bg-teal-100 text-teal-800",
  customer_issue: "bg-blue-100 text-blue-800",
  hybrid: "bg-purple-100 text-purple-800",
};

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-petrol text-paper rounded-br-sm"
              : "bg-white border border-line text-ink rounded-bl-sm shadow-sm"
          }`}
        >
          {message.content}
        </div>

        {/* Route badge + sources — assistant only */}
        {!isUser && (message.route || (message.rag_sources && message.rag_sources.length > 0)) && (
          <div className="flex flex-wrap items-center gap-1.5 px-1">
            {message.route && (
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${ROUTE_COLOR[message.route]}`}
              >
                {ROUTE_LABEL[message.route]}
              </span>
            )}
            {message.rag_sources && message.rag_sources.length > 0 && (
              <span className="text-[11px] text-sage">
                Sources: {message.rag_sources.join(", ")}
              </span>
            )}
          </div>
        )}

        {/* Review-held indicator */}
        {!isUser && message.review_required && !message.escalation_needed && (
          <div className="flex items-center gap-1 px-1 text-[11px] text-amber-600">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            Pending agent review
          </div>
        )}

        {/* Escalation indicator */}
        {!isUser && message.escalation_needed && (
          <div className="flex items-center gap-1 px-1 text-[11px] text-alert">
            <span className="h-1.5 w-1.5 rounded-full bg-alert" />
            Escalated to senior agent
          </div>
        )}
      </div>
    </div>
  );
}
