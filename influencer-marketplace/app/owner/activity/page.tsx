"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge } from "@/components/admin/admin-ui";
import { AdminSelect, AdminTable, TablePagination } from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import type { AdminAuditEntry } from "@/types/admin";

const PAGE_SIZE = 20;

const ACTION_LABELS: Record<string, string> = {
  admin_login: "Admin login",
  user_viewed: "User viewed",
  user_approved: "User approved",
  user_rejected: "User rejected",
  user_suspended: "User suspended",
  user_activated: "User activated",
  user_deleted: "User deleted",
  campaign_viewed: "Campaign viewed",
  campaign_cancelled: "Campaign cancelled",
  alerts_seen: "Alerts seen",
};

export default function OwnerActivityPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);

  const activity = useQuery({
    queryKey: ["owner-activity", { action, page }],
    queryFn: () => adminApi.getActivity({ action, page }),
    placeholderData: keepPreviousData,
  });

  const rows: AdminAuditEntry[] = activity.data?.results ?? [];

  return (
    <AdminShell
      active="activity"
      title="Activity logs"
      subtitle="Immutable audit trail of every privileged action taken in this panel. Secrets and credentials are never recorded."
    >
      <div className="mb-5 max-w-xs">
        <AdminSelect
          label="Action filter"
          value={action}
          onChange={(value) => {
            setAction(value);
            setPage(1);
          }}
          options={[
            { value: "", label: "All actions" },
            ...Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label })),
          ]}
        />
      </div>

      {activity.isLoading ? (
        <LoadingState label="Loading audit trail…" />
      ) : activity.isError ? (
        <AdminErrorNote error={activity.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="No activity yet" description="Admin actions will be recorded here as they happen." />
      ) : (
        <>
          <AdminTable headers={["When", "Actor", "Action", "Target", "Details"]}>
            {rows.map((entry) => (
              <tr key={entry.id}>
                <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3.5 font-bold text-slate-900 dark:text-white">{entry.actor}</td>
                <td className="px-4 py-3.5">
                  <AdminBadge tone={toneFor(entry.action)}>{ACTION_LABELS[entry.action] ?? entry.action}</AdminBadge>
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-500">
                  {entry.target_type ? `${entry.target_type} #${entry.target_id}` : "—"}
                </td>
                <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{entry.description || "—"}</td>
              </tr>
            ))}
          </AdminTable>

          <TablePagination page={page} count={activity.data?.count ?? 0} pageSize={PAGE_SIZE} onPage={setPage} />
        </>
      )}
    </AdminShell>
  );
}

function toneFor(action: string): "green" | "amber" | "red" | "blue" | "slate" | "violet" {
  if (["user_deleted", "user_suspended", "campaign_cancelled", "user_rejected"].includes(action)) return "red";
  if (["user_approved", "user_activated", "admin_login"].includes(action)) return "green";
  if (["user_viewed", "campaign_viewed", "alerts_seen"].includes(action)) return "slate";
  return "violet";
}