"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bot, Package, Headset } from "lucide-react";

export default function ModuleSwitcher({ language = "ar" }: { language?: "ar" | "en" }) {
  const pathname = usePathname();
  const router = useRouter();
  const isAr = language === "ar";
  
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const modules = [
    { id: "m1", path: "/m1", labelAr: "المحلل المالي", labelEn: "Finance", icon: Bot },
    { id: "m2", path: "/m2", labelAr: "المشتريات", labelEn: "Procurement", icon: Package },
    { id: "m3", path: "/m3", labelAr: "خدمة العملاء", labelEn: "Support", icon: Headset },
  ];

  const currentModule = modules.find((m) => pathname?.startsWith(m.path))?.id || "m1";

  if (!mounted) return null;

  return (
    <div className="hidden md:flex bg-slate/50 p-1 rounded-xl border border-slate-light/30 backdrop-blur-md shadow-sm mx-4">
      {modules.map((m) => {
        const isActive = currentModule === m.id;
        const Icon = m.icon;
        return (
          <button
            key={m.id}
            onClick={() => router.push(m.path)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm transition-all duration-300 ${
              isActive
                ? "bg-gold text-midnight shadow-[0_0_10px_rgba(245,158,11,0.2)] font-bold scale-105"
                : "text-ivory/60 hover:text-ivory hover:bg-slate-light/40 font-medium"
            }`}
            aria-pressed={isActive}
            title={isAr ? m.labelAr : m.labelEn}
          >
            <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
            <span className={isAr ? "font-cairo" : "font-inter"}>
              {isAr ? m.labelAr : m.labelEn}
            </span>
          </button>
        );
      })}
    </div>
  );
}
