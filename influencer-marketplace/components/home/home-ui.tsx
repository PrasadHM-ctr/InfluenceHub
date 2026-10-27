"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { ArrowUpRight, CheckCircle2, ChevronRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function HomeLoadingSkeleton() {
  return <div className="animate-pulse space-y-6"><div className="h-64 rounded-3xl bg-slate-200 dark:bg-slate-800" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-34 rounded-2xl bg-slate-200 dark:bg-slate-800" />)}</div><div className="grid gap-6 lg:grid-cols-2"><div className="h-80 rounded-2xl bg-slate-200 dark:bg-slate-800" /><div className="h-80 rounded-2xl bg-slate-200 dark:bg-slate-800" /></div></div>;
}

export function WelcomeHero({ eyebrow, title, description, actions, accent = "violet" }: { eyebrow: string; title: string; description: string; actions: { href: string; label: string; primary?: boolean }[]; accent?: "violet" | "fuchsia" }) {
  const gradient = accent === "fuchsia" ? "from-fuchsia-600 via-violet-600 to-indigo-700" : "from-indigo-700 via-violet-600 to-fuchsia-600";
  return <motion.section initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.42 }} className={cn("relative isolate overflow-hidden rounded-3xl bg-gradient-to-br px-6 py-8 text-white shadow-xl shadow-violet-950/10 sm:px-9 sm:py-10", gradient)}><div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-white/10 blur-2xl" /><div className="absolute bottom-0 left-1/3 h-32 w-80 rounded-full bg-fuchsia-300/20 blur-3xl" /><div className="relative max-w-2xl"><p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-violet-100"><Sparkles size={14} className="text-amber-300" />{eyebrow}</p><h1 className="mt-5 text-3xl font-extrabold tracking-[-.04em] sm:text-4xl">{title}</h1><p className="mt-3 max-w-xl text-sm leading-6 text-indigo-100 sm:text-base">{description}</p><div className="mt-7 flex flex-wrap gap-3">{actions.map((action) => <Link key={action.label} href={action.href} className={cn("inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-extrabold transition", action.primary ? "bg-white text-indigo-950 shadow-lg hover:bg-violet-100" : "border border-white/20 bg-white/10 text-white hover:bg-white/20")} >{action.label}<ChevronRight size={16} /></Link>)}</div></div></motion.section>;
}

export function MetricCard({ label, value, helper, icon: Icon, tone = "violet" }: { label: string; value: string | number; helper: string; icon: LucideIcon; tone?: "violet" | "sky" | "emerald" | "amber" }) {
  const tones = { violet: "bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300", sky: "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300", emerald: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300", amber: "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300" };
  return <motion.article initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} whileHover={{ y: -3 }} transition={{ duration: 0.25 }} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="flex items-start justify-between"><p className="text-sm font-bold text-slate-500">{label}</p><span className={cn("grid h-10 w-10 place-items-center rounded-xl", tones[tone])}><Icon size={19} /></span></div><p className="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{value}</p><p className="mt-1 text-xs font-medium text-slate-500">{helper}</p></motion.article>;
}

export function ActionCard({ title, description, href, icon: Icon, tone = "violet" }: { title: string; description: string; href: string; icon: LucideIcon; tone?: "violet" | "fuchsia" | "sky" }) {
  const tones = { violet: "from-violet-500 to-indigo-600", fuchsia: "from-fuchsia-500 to-violet-600", sky: "from-sky-500 to-cyan-600" };
  return <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.2 }}><Link href={href} className="group block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-950"><span className={cn("grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br text-white shadow-lg", tones[tone])}><Icon size={20} /></span><div className="mt-5 flex items-start justify-between gap-3"><div><h3 className="font-extrabold text-slate-900 dark:text-white">{title}</h3><p className="mt-1.5 text-sm leading-6 text-slate-500">{description}</p></div><ArrowUpRight size={18} className="shrink-0 text-slate-400 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-violet-600" /></div></Link></motion.div>;
}

export function SectionHeader({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: { href: string; label: string } }) {
  return <div className="mb-4 flex items-end justify-between gap-4"><div>{eyebrow && <p className="text-xs font-extrabold uppercase tracking-[.16em] text-violet-600">{eyebrow}</p>}<h2 className="mt-1 text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">{title}</h2></div>{action && <Link href={action.href} className="text-sm font-extrabold text-violet-600 hover:text-violet-500">{action.label}</Link>}</div>;
}

export function ProgressCard({ title, value, detail, percentage, href }: { title: string; value: string; detail: string; percentage: number; href: string }) {
  return <Link href={href} className="block rounded-2xl bg-[#28245d] p-6 text-white shadow-lg shadow-indigo-950/10 transition hover:-translate-y-1"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-bold text-violet-200">{title}</p><p className="mt-4 text-3xl font-extrabold">{value}</p><p className="mt-1 text-sm text-indigo-200">{detail}</p></div><CheckCircle2 className="text-violet-300" size={24} /></div><div className="mt-6 h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-gradient-to-r from-violet-300 to-fuchsia-300" style={{ width: `${Math.min(Math.max(percentage, 0), 100)}%` }} /></div><p className="mt-2 text-right text-xs font-bold text-violet-200">{Math.round(percentage)}% complete</p></Link>;
}
