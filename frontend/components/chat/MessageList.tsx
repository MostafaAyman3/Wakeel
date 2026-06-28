"use client";

import { useEffect, useRef } from "react";
import { MessageBubble, type ChatMessage } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  loading?: boolean;
}

export function MessageList({ messages, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gold/15">
            <span className="font-cairo text-xl font-bold text-gold">و</span>
          </div>
          <p className="mb-1 font-cairo text-base font-semibold text-ivory">
            كيف يمكنني مساعدتك؟
          </p>
          <p className="text-sage">How can I help you today?</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gold">
              <span className="font-cairo text-xs font-bold text-midnight">و</span>
            </div>
            <div className="bubble-agent">
              <span className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gold/70 [animation-delay:0ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gold/70 [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gold/70 [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
