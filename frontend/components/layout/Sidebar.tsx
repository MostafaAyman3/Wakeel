"use client";

// Shared app rail — links all three modules (M1, M2, M3).
// Mirrors the dark/gold Wakeel identity.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Package, Headphones, Home } from "lucide-react";

const navItems = [
  { href: "/", icon: Home, titleAr: "الرئيسية", titleEn: "Home", exact: true },
  { href: "/m1", icon: BarChart2, titleAr: "المحلل المالي", titleEn: "Financial Analyst" },
  { href: "/m2", icon: Package, titleAr: "المشتريات", titleEn: "Procurement" },
  { href: "/m3", icon: Headphones, titleAr: "دعم العملاء", titleEn: "Customer Support" },
];

interface Props {
  language?: "ar" | "en";
}

export function Sidebar({ language = "en" }: Props) {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-y-0 start-0 z-40 flex w-14 flex-col items-center gap-1 border-e border-slate bg-surface py-4">
      <div className="mb-4 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gold">
        <span className="font-cairo text-sm font-bold text-midnight">و</span>
      </div>

      {navItems.map(({ href, icon: Icon, titleAr, titleEn, exact }) => {
        const active = exact
          ? pathname === href
          : pathname.startsWith(href);
        const label = language === "ar" ? titleAr : titleEn;
        return (
          <Link
            key={href}
            href={href}
            title={label}
            aria-label={label}
            className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
              active
                ? "bg-gold/15 text-gold"
                : "text-ivory/30 hover:bg-slate/50 hover:text-ivory/65"
            }`}
          >
            <Icon size={17} />
          </Link>
        );
      })}
    </nav>
  );
}
