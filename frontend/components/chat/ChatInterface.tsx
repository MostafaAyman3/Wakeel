"use client";

import React from "react";
import { getDirection } from "@/lib/rtl";
import { useM1Chat } from "@/hooks/useM1Query";
import Header from "@/components/layout/Header";
import MessageList from "@/components/chat/MessageList";
import ChatInput from "@/components/chat/ChatInput";

/* ─────────────────────────────────────────────────────────────
 * ChatInterface — main container housing the full chat experience.
 *
 * Combines:
 *   Header        – logo + language toggle
 *   MessageList   – scrollable conversation with welcome screen
 *   ChatInput     – bilingual input with send button
 * ───────────────────────────────────────────────────────────── */

export function ChatInterface() {
  const {
    messages,
    isLoading,
    language,
    sendMessage,
    setLanguage,
  } = useM1Chat();

  const toggleLanguage = () => {
    const next = language === "ar" ? "en" : "ar";
    setLanguage(next);
    // Update document direction
    document.documentElement.lang = next;
    document.documentElement.dir = getDirection(next);
  };

  return (
    <div className="flex flex-col h-screen bg-midnight">
      <Header language={language} onToggleLanguage={toggleLanguage} />

      <MessageList
        messages={messages}
        isLoading={isLoading}
        language={language}
        onSuggestionClick={sendMessage}
      />

      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
        language={language}
      />
    </div>
  );
}
