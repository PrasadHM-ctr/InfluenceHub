import { AlertCircle, Inbox, LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="flex min-h-[240px] items-center justify-center gap-2 text-sm font-medium text-slate-500"><LoaderCircle className="animate-spin" size={18} />{label}</div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-14 text-center dark:border-slate-700 dark:bg-slate-900/40"><Inbox className="mx-auto text-violet-500" size={30} /><h3 className="mt-4 font-bold text-slate-900 dark:text-white">{title}</h3><p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">{description}</p></div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"><AlertCircle size={18} className="mt-0.5 shrink-0" />{message}</div>;
}
