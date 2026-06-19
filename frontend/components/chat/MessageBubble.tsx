"use client";

import React, { forwardRef } from "react";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/types/m1";
import OutputRenderer from "@/components/m1/OutputRenderer";

/* ─────────────────────────────────────────────────────────────
 * MessageBubble — renders a single chat message.
 *
 * User messages: gold-tinted bubble, aligned to end.
 * Agent messages: surface-colored bubble with OutputRenderer
 *   for structured content + gold left border.
 * ───────────────────────────────────────────────────────────── */

interface MessageBubbleProps {
  message: ChatMessage;
}

const MessageBubble = forwardRef<HTMLDivElement, MessageBubbleProps>(
  function MessageBubble({ message }, ref) {
    const isUser = message.role === "user";
    const dir = message.language === "ar" ? "rtl" : "ltr";

    if (isUser) {
      return (
        <div ref={ref} className="flex justify-end animate-fade-in" dir={dir}>
          <div className="flex items-start gap-3 max-w-[75%]">
            <div className="bubble-user">
              <p className="text-sm text-ivory leading-relaxed font-cairo">
                {message.content}
              </p>
            </div>
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center mt-1">
              <User size={14} className="text-gold" />
            </div>
          </div>
        </div>
      );
    }

    // Agent message
    return (
      <div ref={ref} className="flex justify-start animate-slide-up" dir={dir}>
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gold flex items-center justify-center mt-1">
            <Bot size={14} className="text-midnight" />
          </div>
          <div className="bubble-agent space-y-3 card-gold-border">
            {message.response ? (
              <OutputRenderer
                response={message.response}
                language={message.language}
              />
            ) : (
              <p className="text-sm text-ivory/80 leading-relaxed">
                {message.content}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  },
);

export default MessageBubble;
