"use client";

import React, { useState } from 'react';
import Header from '@/components/layout/Header';

export default function M3Support() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");

  const toggleLanguage = () => {
    const next = language === "ar" ? "en" : "ar";
    setLanguage(next);
  };

  return (
    <div className="min-h-screen bg-midnight text-ivory" dir={language === "ar" ? "rtl" : "ltr"}>
      <Header language={language} onToggleLanguage={toggleLanguage} />
      
      <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] p-6 text-center">
        <h2 className={`text-3xl font-bold text-gold mb-4 ${language === 'ar' ? 'font-cairo' : 'font-inter'}`}>
          {language === 'ar' ? 'خدمة العملاء (M3)' : 'Customer Support (M3)'}
        </h2>
        <p className={`text-lg text-ivory/60 max-w-lg ${language === 'ar' ? 'font-cairo' : 'font-inter'}`}>
          {language === 'ar'
            ? 'هذه الواجهة قيد التطوير. سيتم توفير دعم العملاء والمراجعة البشرية هنا قريباً.'
            : 'This interface is under development. Customer support and human review will be available here soon.'}
        </p>
      </div>
    </div>
  );
}
