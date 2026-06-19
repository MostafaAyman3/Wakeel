import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Wakeel — AI ERP Intelligence",
  description:
    "Enterprise AI financial advisor powered by LangGraph. Bilingual Arabic/English ERP intelligence agent.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <body className="min-h-screen bg-midnight text-ivory font-cairo antialiased">
        {children}
      </body>
    </html>
  );
}
