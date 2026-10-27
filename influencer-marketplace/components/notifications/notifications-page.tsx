"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api, getApiError } from "@/services/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";
import { formatDate } from "@/lib/utils";

export function NotificationsPageContent({ role }: { role: "business" | "influencer" }) {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const query = useQuery({
    queryKey: ["notifications", { page, unreadOnly }],
    queryFn: () => api.getNotifications(unreadOnly),
  });

  const markRead = useMutation({
    mutationFn: (id: number) => api.markNotificationRead(id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["notifications"] });
      client.invalidateQueries({ queryKey: ["notification-unread-count"] });
    },
    onError: (error) => toast.error(getApiError(error)),
  });

  const markAll = useMutation({
    mutationFn: api.markAllNotificationsRead,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["notifications"] });
      client.invalidateQueries({ queryKey: ["notification-unread-count"] });
      toast.success("All notifications marked as read.");
    },
    onError: (error) => toast.error(getApiError(error)),
  });

  const items = query.data?.results ?? [];
  const totalCount = query.data?.count ?? 0;
  const totalPages = Math.max(Math.ceil(totalCount / 20), 1);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-bold text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={unreadOnly} onChange={(event) => { setUnreadOnly(event.target.checked); setPage(1); }} className="h-4 w-4 rounded accent-violet-600" />
          Unread only
        </label>
        <button onClick={() => markAll.mutate()} disabled={markAll.isPending} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600 transition hover:border-violet-300 hover:text-violet-600 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300">
          <CheckCheck size={15} /> Mark all read
        </button>
      </div>

      {query.isLoading ? (
        <LoadingState label="Loading notifications…" />
      ) : query.error ? (
        <ErrorState message={getApiError(query.error)} />
      ) : items.length ? (
        <>
          <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-950">
            {items.map((item) => (
              <li key={item.id} className={`flex items-start gap-3 p-4 ${item.is_read ? "" : "bg-violet-50/60 dark:bg-violet-950/20"}`}>
                <span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${item.is_read ? "bg-slate-100 text-slate-400 dark:bg-slate-800" : "bg-violet-100 text-violet-600 dark:bg-violet-950 dark:text-violet-300"}`}>
                  <Bell size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-extrabold text-slate-900 dark:text-white">{item.title}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{item.message}</p>
                  <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{formatDate(item.created_at)}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  {!item.is_read && (
                    <button onClick={() => markRead.mutate(item.id)} disabled={markRead.isPending} className="rounded-lg px-2 py-1 text-xs font-bold text-violet-600 transition hover:bg-violet-50 disabled:opacity-60 dark:hover:bg-violet-950/40">Mark read</button>
                  )}
                  {item.link && (
                    <Link href={item.link} className="rounded-lg px-2 py-1 text-xs font-bold text-slate-400 transition hover:text-violet-600">Open</Link>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button disabled={page <= 1} onClick={() => setPage((current) => current - 1)} className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 transition hover:border-violet-300 disabled:opacity-40 dark:border-slate-700"><ChevronLeft size={16} /></button>
              <span className="text-sm font-bold">Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)} className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 transition hover:border-violet-300 disabled:opacity-40 dark:border-slate-700"><ChevronRight size={16} /></button>
            </div>
          )}
        </>
      ) : (
        <EmptyState title="No notifications yet" description={`Campaign updates, messages, and verification results for your ${role} workspace will appear here.`} />
      )}
    </div>
  );
}