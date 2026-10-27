"use client";

import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export function AccessDeniedInline({ message }: { message?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      {message ?? "You do not have permission to access the owner panel."}
    </div>
  );
}

export function AdminBadge({
  tone,
  children,
}: {
  tone: "green" | "amber" | "red" | "blue" | "slate" | "violet";
  children: ReactNode;
}) {
  const tones = {
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-900",
    amber: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-900",
    red: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:ring-rose-900",
    blue: "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:ring-sky-900",
    slate: "bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
    violet: "bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-950/40 dark:text-violet-300 dark:ring-violet-900",
  };
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset", tones[tone])}>
      {children}
    </span>
  );
}

const STATUS_TONES: Record<string, "green" | "amber" | "red" | "blue" | "slate"> = {
  Approved: "green",
  Active: "green",
  Completed: "blue",
  Accepted: "green",
  Pending: "amber",
  Rejected: "red",
  Inactive: "slate",
  Cancelled: "slate",
};

export function statusTone(status: string): "green" | "amber" | "red" | "blue" | "slate" {
  return STATUS_TONES[status] ?? "slate";
}

/** Risk score chip - a moderation SIGNAL, never proof of fraud. */
export function RiskBadge({ score }: { score: number }) {
  const tone = score >= 60 ? "red" : score >= 30 ? "amber" : "green";
  return <AdminBadge tone={tone}>Risk {score}/100</AdminBadge>;
}