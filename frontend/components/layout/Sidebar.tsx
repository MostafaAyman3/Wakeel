"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Headphones } from "lucide-react";

const navItems = [
  { href: "/m1", icon: BarChart2,   titleAr: "المحلل المالي",  titleEn: "Financial Analyst" },
  { href: "/m3", icon: Headphones,  titleAr: "دعم العملاء",    titleEn: "Customer Support" },
];

interface Props {
  language?: "ar" | "en";
}

export function Sidebar({ language = "ar" }: Props) {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-y-0 start-0 w-14 bg-surface border-e border-slate flex flex-col items-center py-4 gap-1 z-40">
      {/* Logo mark */}
      <div className="w-8 h-8 rounded-lg bg-gold flex items-center justify-center mb-4 shrink-0">
        <span className="text-midnight font-bold text-sm font-cairo">و</span>
      </div>

      {navItems.map(({ href, icon: Icon, titleAr, titleEn }) => {
        const active = pathname.startsWith(href);
        const label = language === "ar" ? titleAr : titleEn;
        return (
          <Link
            key={href}
            href={href}
            title={label}
            aria-label={label}
            className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
              active
                ? "bg-gold/15 text-gold"
                : "text-ivory/30 hover:text-ivory/65 hover:bg-slate/50"
            }`}
          >
            <Icon size={17} />
          </Link>
        );
      })}
    </nav>
  );
}
