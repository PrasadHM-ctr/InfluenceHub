import type { LucideIcon } from "lucide-react";

export function StatCard({ label, value, icon: Icon, tone = "violet" }: { label: string; value: string | number; icon: LucideIcon; tone?: "violet" | "blue" | "emerald" | "amber" }) {
  const tones = { violet: "bg-violet-50 text-violet-600", blue: "bg-sky-50 text-sky-600", emerald: "bg-emerald-50 text-emerald-600", amber: "bg-amber-50 text-amber-600" };
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="flex items-start justify-between"><p className="text-sm font-medium text-slate-500">{label}</p><span className={`grid h-9 w-9 place-items-center rounded-xl ${tones[tone]}`}><Icon size={18} /></span></div><p className="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{value}</p></article>;
}
