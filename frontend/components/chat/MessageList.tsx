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
      <div className="flex flex-1 items-center justify-center text-sm text-sage">
        <div className="text-center">
          <p className="mb-1 text-base font-medium text-ink">كيف يمكنني مساعدتك؟</p>
          <p className="text-sage">How can I help you today?</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="rounded-2xl border border-line bg-white px-4 py-3 shadow-sm">
            <span className="flex gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-sage [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-sage [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-sage [animation-delay:300ms]" />
            </span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
