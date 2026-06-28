import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wakeel — AI Support & Financial Analyst",
  description:
    "Human-supervised AI customer support and financial analysis, in Arabic and English.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
