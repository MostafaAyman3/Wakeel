"use client";

import { type ChatMessage } from "./MessageBubble";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (message: string) => void;
}

export function ChatInterface({ messages, loading, onSend }: Props) {
  return (
    <div className="flex h-full min-h-[420px] flex-col rounded-card border border-line bg-paper/60 shadow-desk backdrop-blur-sm">
      <MessageList messages={messages} loading={loading} />
      <ChatInput onSend={onSend} disabled={loading} />
    </div>
  );
}
