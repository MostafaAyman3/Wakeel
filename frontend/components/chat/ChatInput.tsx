"use client";

import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import { SendHorizonal } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 border-t border-slate bg-surface px-4 py-3"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        rows={1}
        placeholder={placeholder ?? "اكتب رسالتك… / Type your message…"}
        className="flex-1 resize-none rounded-xl border border-slate bg-midnight px-3 py-2 text-sm text-ivory placeholder:text-sage focus:border-gold/50 focus:outline-none disabled:opacity-50"
        style={{ minHeight: "40px", maxHeight: "160px" }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gold text-midnight transition hover:bg-gold-light disabled:opacity-40"
        aria-label="Send"
      >
        <SendHorizonal size={16} />
      </button>
    </form>
  );
}
