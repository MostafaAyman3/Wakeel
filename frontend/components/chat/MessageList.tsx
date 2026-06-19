"use client";

import React, { forwardRef, useEffect, useRef } from "react";
import { Bot, Sparkles } from "lucide-react";
import type { ChatMessage } from "@/types/m1";
import MessageBubble from "@/components/chat/MessageBubble";

/* ─────────────────────────────────────────────────────────────
 * MessageList — scrollable conversation history.
 *
 * Auto-scrolls to bottom on new messages.
 * Shows welcome screen when empty.
 * Shows thinking indicator when loading.
 * ───────────────────────────────────────────────────────────── */

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  language: "ar" | "en";
  onSuggestionClick?: (query: string) => void;
}

const SUGGESTIONS_AR = [
  "إيه أداء المبيعات في الربع الثاني مقارنة بالأول؟",
  "مين العملاء المتأخرين في السداد أكتر من 30 يوم؟",
  "حللّي فواتير الموردين في الربع الأول",
  "ما هي عقوبات التهرب الضريبي؟",
  "ما هي المصروفات غير المعتادة؟",
];

const SUGGESTIONS_EN = [
  "How did sales perform in Q2 compared to Q1?",
  "Which customers are overdue by more than 30 days?",
  "Analyze vendor invoices for Q1",
  "What are the penalties for tax evasion?",
  "What are the unusual expenses?",
];

const MessageList = forwardRef<HTMLDivElement, MessageListProps>(
  function MessageList({ messages, isLoading, language, onSuggestionClick }, ref) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const isAr = language === "ar";
    const suggestions = isAr ? SUGGESTIONS_AR : SUGGESTIONS_EN;

    // Auto-scroll to bottom on new messages
    useEffect(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    // Empty state — welcome screen
    if (messages.length === 0 && !isLoading) {
      return (
        <div
          ref={ref}
          className="flex-1 flex flex-col items-center justify-center p-8 overflow-y-auto"
        >
          <div className="w-16 h-16 rounded-2xl bg-gold/10 border border-gold/20 flex items-center justify-center mb-6 agent-pulse">
            <Sparkles size={28} className="text-gold" />
          </div>

          <h2 className="text-2xl font-bold font-cairo mb-2 text-center">
            {isAr ? "مرحباً، أنا وكيل" : "Hello, I'm Wakeel"}
          </h2>
          <p className="text-ivory/50 text-center mb-8 max-w-md text-sm">
            {isAr
              ? "محلل مالي ذكي. اسألني عن المبيعات، الفواتير، العملاء، أو الضرائب."
              : "Your AI financial analyst. Ask me about sales, invoices, customers, or taxes."}
          </p>

          <div className="grid gap-2 w-full max-w-lg">
            {suggestions.map((suggestion, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onSuggestionClick?.(suggestion)}
                className="text-start px-4 py-3 rounded-xl bg-surface border border-slate
                           hover:border-gold/30 hover:bg-gold/5
                           text-sm text-ivory/70 hover:text-ivory
                           transition-all duration-200 font-cairo"
                dir={isAr ? "rtl" : "ltr"}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gold flex items-center justify-center agent-pulse">
                <Bot size={14} className="text-midnight" />
              </div>
              <div className="bubble-agent">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-gold animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-gold animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-gold animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span className="text-xs text-ivory/40 font-inter">
                    {isAr ? "جاري التحليل..." : "Analyzing..."}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    );
  },
);

export default MessageList;
