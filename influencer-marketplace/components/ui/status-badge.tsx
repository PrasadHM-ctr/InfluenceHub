import { cn } from "@/lib/utils";
import type { CampaignStatus } from "@/types";

const styles: Record<CampaignStatus, string> = {
  Pending: "bg-amber-50 text-amber-700 ring-amber-200",
  Accepted: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  Rejected: "bg-rose-50 text-rose-700 ring-rose-200",
  Completed: "bg-sky-50 text-sky-700 ring-sky-200",
  Cancelled: "bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
};

export function StatusBadge({ status }: { status: CampaignStatus }) {
  return <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset", styles[status])}>{status}</span>;
}