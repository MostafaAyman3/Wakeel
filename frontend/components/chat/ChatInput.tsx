"use client";

import React, { forwardRef, useRef, KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { isArabic } from "@/lib/rtl";

/* ─────────────────────────────────────────────────────────────
 * ChatInput — bilingual textarea with auto RTL detection.
 *
 * forwardRef + standard HTML attributes for future shadcn swap.
 * ───────────────────────────────────────────────────────────── */

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  language: "ar" | "en";
}

const ChatInput = forwardRef<HTMLDivElement, ChatInputProps>(
  function ChatInput({ onSend, disabled = false, language }, ref) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSend = () => {
      const value = textareaRef.current?.value.trim();
      if (!value || disabled) return;
      onSend(value);
      if (textareaRef.current) {
        textareaRef.current.value = "";
        textareaRef.current.style.height = "auto";
      }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    };

    const handleInput = () => {
      const el = textareaRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;

      // Auto-detect text direction
      const dir = isArabic(el.value) ? "rtl" : "ltr";
      el.dir = dir;
    };

    const placeholder =
      language === "ar"
        ? "اكتب سؤالك هنا... مثال: إيه أداء المبيعات؟"
        : "Type your question... e.g. What is total revenue?";

    return (
      <div ref={ref} className="flex items-end gap-3 p-4 border-t border-slate bg-surface/80 backdrop-blur-sm">
        <textarea
          ref={textareaRef}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          dir={language === "ar" ? "rtl" : "ltr"}
          className="input-field resize-none font-cairo text-sm leading-relaxed"
          aria-label="Chat input"
          id="chat-input"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled}
          className="btn-primary flex-shrink-0 p-3 rounded-xl"
          aria-label="Send message"
          id="send-button"
        >
          <Send size={18} className={language === "ar" ? "rotate-180" : ""} />
        </button>
      </div>
    );
  },
);

export default ChatInput;
