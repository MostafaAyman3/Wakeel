import type { Metadata } from "next";
import { ChatInterface } from "@/components/chat/ChatInterface";

export const metadata: Metadata = {
  title: "Wakeel — AI Financial Analyst",
  description:
    "Ask questions about sales, invoices, customers, and taxes in Arabic or English. Powered by LangGraph AI agent.",
};

export default function M1Page() {
  return <ChatInterface />;
}
