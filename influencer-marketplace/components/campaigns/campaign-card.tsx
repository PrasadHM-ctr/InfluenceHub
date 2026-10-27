import { CalendarDays, IndianRupee } from "lucide-react";
import type { Campaign } from "@/types";
import { formatDate, formatMoney } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/status-badge";

export function CampaignCard({ campaign, actions }: { campaign: Campaign; actions?: React.ReactNode }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-bold uppercase tracking-[.14em] text-slate-400">{campaign.business_name ?? "Campaign request"}</p><h3 className="mt-1 truncate text-base font-extrabold text-slate-900 dark:text-white">{campaign.title}</h3></div><StatusBadge status={campaign.status} /></div><p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600 dark:text-slate-400">{campaign.message}</p><div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 pt-4 text-xs font-semibold text-slate-500 dark:border-slate-800"><span className="inline-flex items-center gap-1.5"><IndianRupee size={14} className="text-violet-500" />{formatMoney(campaign.budget)}</span><span className="inline-flex items-center gap-1.5"><CalendarDays size={14} className="text-violet-500" />{formatDate(campaign.created_at)}</span></div>{actions && <div className="mt-4 flex gap-2">{actions}</div>}</article>;
}
