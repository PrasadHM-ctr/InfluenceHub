"use client";

import type { LucideIcon } from "lucide-react";

export function AdminStatCard({
  label,
  value,
  icon: Icon,
  tone = "violet",
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone?: "violet" | "blue" | "emerald" | "amber" | "rose";
}) {
  const tones = {
    violet: "bg-violet-50 text-violet-600 dark:bg-violet-950/50 dark:text-violet-300",
    blue: "bg-sky-50 text-sky-600 dark:bg-sky-950/50 dark:text-sky-300",
    emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300",
    rose: "bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-300",
  };
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`grid h-9 w-9 place-items-center rounded-xl ${tones[tone]}`}>
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{value}</p>
    </article>
  );
}