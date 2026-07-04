import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Wakeel — AI-Powered ERP Intelligence",
  description:
    "Multi-Agent AI Platform for ERP Intelligence. Financial analysis, procurement automation, and customer support — powered by LangGraph.",
};

const modules = [
  {
    id: "m1",
    href: "/m1",
    titleAr: "المحلل المالي",
    titleEn: "Financial Analyst",
    descAr:
      "اسأل عن المبيعات، الفواتير، العملاء، والضرائب بالعربي أو الإنجليزي. تحليل ذكي مع رسوم بيانية تفاعلية.",
    descEn:
      "Ask about sales, invoices, customers, and taxes in Arabic or English. Smart analysis with interactive charts.",
    icon: "📊",
    gradient: "from-amber-500/20 to-orange-500/10",
    features: ["NL→SQL", "Tax RAG", "Charts", "Multi-turn"],
  },
  {
    id: "m2",
    href: "/m2",
    titleAr: "المشتريات والمخزون",
    titleEn: "Procurement & Inventory",
    descAr:
      "مراقبة المخزون الذكية مع تنبيهات فورية وإنشاء طلبات الشراء تلقائياً وموافقات بشرية.",
    descEn:
      "Smart inventory monitoring with instant alerts, automated RFQ generation, and human-in-the-loop approvals.",
    icon: "📦",
    gradient: "from-emerald-500/20 to-teal-500/10",
    features: ["Inventory AI", "RFQ Auto-Gen", "HITL Approval", "Voice"],
  },
  {
    id: "m3",
    href: "/m3",
    titleAr: "خدمة العملاء",
    titleEn: "Customer Support",
    descAr:
      "دعم عملاء ذكي مع تحليل تلقائي للمشاكل، جلب بيانات CRM، ومراجعة بشرية.",
    descEn:
      "AI customer support with automatic issue classification, CRM data integration, and human review.",
    icon: "🎧",
    gradient: "from-blue-500/20 to-indigo-500/10",
    features: ["Intent Router", "CRM Pipeline", "Human Review", "Audit Trail"],
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-midnight">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-gold/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-5xl px-6 pt-20 pb-16 text-center">
          {/* Logo */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gold shadow-[0_0_40px_rgba(245,158,11,0.3)]">
            <span className="font-cairo text-3xl font-bold text-midnight">
              و
            </span>
          </div>
          <h1 className="mb-2 font-cairo text-5xl font-extrabold tracking-tight text-ivory">
            وكيل{" "}
            <span className="font-inter text-4xl font-light text-ivory/60">
              Wakeel
            </span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-ivory/50 font-inter leading-relaxed">
            Multi-Agent AI Platform for ERP Intelligence — built with{" "}
            <span className="text-gold/80">LangGraph</span>,{" "}
            <span className="text-gold/80">GPT</span>, and{" "}
            <span className="text-gold/80">Next.js</span>
          </p>

          {/* Tech badges */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            {[
              "LangGraph",
              "FastAPI",
              "PostgreSQL",
              "pgvector",
              "OpenAI",
              "Next.js",
            ].map((tech) => (
              <span
                key={tech}
                className="rounded-full border border-slate bg-surface px-3 py-1 font-mono text-xs text-ivory/40"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Module Cards */}
      <div className="mx-auto max-w-5xl px-6 pb-20">
        <div className="grid gap-6 md:grid-cols-3">
          {modules.map((m) => (
            <Link
              key={m.id}
              href={m.href}
              className="group relative flex flex-col overflow-hidden rounded-2xl border border-slate bg-surface transition-all duration-300 hover:border-gold/40 hover:shadow-[0_0_30px_rgba(245,158,11,0.08)] hover:-translate-y-1"
            >
              <div
                className={`absolute inset-0 bg-gradient-to-br ${m.gradient} opacity-0 transition-opacity duration-300 group-hover:opacity-100`}
              />
              <div className="relative flex flex-1 flex-col p-6">
                {/* Icon + Title */}
                <div className="mb-4 flex items-center gap-3">
                  <span className="text-3xl">{m.icon}</span>
                  <div>
                    <h2 className="font-cairo text-lg font-bold text-ivory">
                      {m.titleAr}
                    </h2>
                    <p className="font-inter text-xs text-ivory/40">
                      {m.titleEn}
                    </p>
                  </div>
                </div>

                {/* Description */}
                <p className="mb-5 flex-1 text-sm leading-relaxed text-ivory/50">
                  {m.descEn}
                </p>

                {/* Feature tags */}
                <div className="flex flex-wrap gap-1.5">
                  {m.features.map((f) => (
                    <span
                      key={f}
                      className="rounded-md bg-slate/60 px-2 py-0.5 font-mono text-[10px] text-ivory/30 transition-colors group-hover:bg-gold/10 group-hover:text-gold/60"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom action bar */}
              <div className="border-t border-slate px-6 py-3 text-center">
                <span className="font-inter text-sm font-medium text-gold/70 transition-colors group-hover:text-gold">
                  Open Module →
                </span>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-16 text-center">
          <p className="text-xs text-ivory/20 font-inter">
            Built by Mostafa Ayman — 3 LangGraph Agents · 41 Graph Nodes · 18
            SQL Templates · Bilingual AR/EN
          </p>
        </div>
      </div>
    </main>
  );
}
