"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { toast } from "sonner";
import { api, getApiError } from "@/services/api";
import { formatDate } from "@/lib/utils";

export function NotificationBell({ role }: { role: "business" | "influencer" }) {
  const client = useQueryClient();
  const count = useQuery({
    queryKey: ["notification-unread-count"],
    queryFn: api.getUnreadNotificationCount,
    refetchInterval: 30_000,
  });
  const recent = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => api.getNotifications(),
    refetchInterval: 30_000,
  });

  const markAll = useMutation({
    mutationFn: api.markAllNotificationsRead,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["notifications"] });
      client.invalidateQueries({ queryKey: ["notification-unread-count"] });
    },
    onError: (error) => toast.error(getApiError(error)),
  });

  const unread = count.data?.unread_count ?? 0;
  const items = recent.data?.results.slice(0, 5) ?? [];

  return (
    <div className="group relative">
      <Link href={`/${role}/notifications`} className="relative grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:border-violet-300 hover:text-violet-600 dark:border-slate-700 dark:text-slate-300" aria-label="Notifications">
        <Bell size={18} />
        {unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-extrabold text-white">{unread > 9 ? "9+" : unread}</span>}
      </Link>
      <div className="invisible absolute right-0 top-full z-40 w-80 translate-y-1 opacity-0 transition-all group-hover:visible group-hover:translate-y-0 group-hover:opacity-100">
        <div className="mt-2 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-800">
            <span className="text-sm font-extrabold">Notifications</span>
            {unread > 0 && (
              <button onClick={() => markAll.mutate()} className="inline-flex items-center gap-1 text-xs font-bold text-violet-600 hover:underline"><CheckCheck size={13} />Mark all read</button>
            )}
          </div>
          {items.length ? (
            <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800">
              {items.map((item) => (
                <li key={item.id}>
                  <Link href={item.link || `/${role}/notifications`} className={`block px-4 py-3 transition hover:bg-slate-50 dark:hover:bg-slate-800/60 ${item.is_read ? "" : "bg-violet-50/60 dark:bg-violet-950/20"}`}>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{item.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{item.message}</p>
                    <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{formatDate(item.created_at)}</p>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-8 text-center text-sm text-slate-400">No notifications yet.</p>
          )}
          <Link href={`/${role}/notifications`} className="block border-t border-slate-100 px-4 py-3 text-center text-xs font-extrabold text-violet-600 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/60">View all notifications</Link>
        </div>
      </div>
    </div>
  );
}