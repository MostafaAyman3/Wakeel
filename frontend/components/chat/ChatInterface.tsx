"use client";

import React from "react";
import { getDirection } from "@/lib/rtl";
import { useM1Chat } from "@/hooks/useM1Query";
import Header from "@/components/layout/Header";
import MessageList from "@/components/chat/MessageList";
import ChatInput from "@/components/chat/ChatInput";
import type { ChatMessage } from "@/types/m1";

/* ─────────────────────────────────────────────────────────────
 * ChatInterface — main container housing the full chat experience.
 *
 * Combines:
 *   Header        – logo + language toggle
 *   MessageList   – scrollable conversation with welcome screen
 *   ChatInput     – bilingual input with send button
 * ───────────────────────────────────────────────────────────── */

interface ChatInterfaceProps {
  messages?: ChatMessage[];
  loading?: boolean;
  language?: "ar" | "en";
  onSend?: (message: string) => void;
  hideHeader?: boolean;
}

// 1. Generic Base Component (Used directly by M3)
export function BaseChatInterface({
  messages = [],
  loading = false,
  language = "ar",
  onSend = () => {},
  hideHeader = false,
}: ChatInterfaceProps) {
  
  const toggleLanguage = () => {
    const next = language === "ar" ? "en" : "ar";
    document.documentElement.lang = next;
    document.documentElement.dir = getDirection(next);
  };

  return (
    <div className={hideHeader ? "flex flex-col h-full rounded-card border border-line bg-paper/60 shadow-desk backdrop-blur-sm" : "flex flex-col h-screen bg-midnight"}>
      {!hideHeader && (
        <Header language={language} onToggleLanguage={toggleLanguage} />
      )}

      <MessageList
        messages={messages}
        isLoading={loading}
        language={language}
        onSuggestionClick={onSend}
      />

      <ChatInput
        onSend={onSend}
        disabled={loading}
        language={language}
      />
    </div>
  );
}

// 2. M1 Wrapper Component (Safely encapsulates the hook)
export function ChatInterface(props: ChatInterfaceProps) {
  // If props are passed externally (M3), bypass the internal state wrapper completely
  if (props.messages !== undefined) {
    return <BaseChatInterface {...props} />;
  }

  // Otherwise, we are in M1 mode. Initialize the hook safely.
  return <M1ChatWrapper {...props} />;
}

// Internal wrapper to prevent hook execution when used by M3
function M1ChatWrapper(props: ChatInterfaceProps) {
  const { messages, isLoading, language, sendMessage, setLanguage } = useM1Chat();

  const handleSend = props.onSend || sendMessage;
  
  return (
    <BaseChatInterface 
      messages={messages}
      loading={isLoading}
      language={language}
      onSend={handleSend}
      hideHeader={props.hideHeader}
    />
  );
}
