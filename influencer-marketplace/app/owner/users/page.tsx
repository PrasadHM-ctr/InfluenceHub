"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Eye, ShieldOff, ShieldCheck, Trash2 } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, statusTone } from "@/components/admin/admin-ui";
import {
  AdminSearchInput,
  AdminSelect,
  AdminTable,
  ConfirmDialog,
  TablePagination,
} from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi, getAdminApiError } from "@/services/admin-api";
import type { AdminUserRow } from "@/types/admin";
import { formatDate } from "@/lib/utils";

const PAGE_SIZE = 20;

type PendingAction = { user: AdminUserRow; action: "suspend" | "activate" | "verify_profile" } | null;

export default function OwnerUsersPage() {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [verification, setVerification] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [pending, setPending] = useState<PendingAction>(null);
  const [confirmDelete, setConfirmDelete] = useState<AdminUserRow | null>(null);

  // Debounce search so typing does not spam the API.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const users = useQuery({
    queryKey: ["owner-users", { search, role, verification, sort, page }],
    queryFn: () => adminApi.getUsers({ search, role, verification, sort, page }),
    placeholderData: keepPreviousData,
  });

  const action = useMutation({
    mutationFn: ({ id, act }: { id: number; act: "suspend" | "activate" | "verify_profile" }) =>
      adminApi.userAction(id, act),
    onSuccess: (result) => {
      toast.success(result.detail);
      setPending(null);
      queryClient.invalidateQueries({ queryKey: ["owner-users"] });
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const deleteUser = useMutation({
    mutationFn: (id: number) => adminApi.deleteUser(id),
    onSuccess: () => {
      toast.success("Account permanently deleted.");
      setConfirmDelete(null);
      queryClient.invalidateQueries({ queryKey: ["owner-users"] });
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const rows = users.data?.results ?? [];

  return (
    <AdminShell
      active="users"
      title="User management"
      subtitle="Every InfluenceHub account with moderation actions. Dangerous actions always ask for confirmation."
    >
      {/* Filters */}
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-400">Search</span>
          <AdminSearchInput
            value={searchInput}
            placeholder="Search name, username or email…"
            onChange={(value) => {
              setSearchInput(value);
              setPage(1);
            }}
          />
        </div>
        <AdminSelect
          label="Role"
          value={role}
          onChange={(value) => {
            setRole(value);
            setPage(1);
          }}
          options={[
            { value: "", label: "All roles" },
            { value: "business", label: "Business" },
            { value: "influencer", label: "Influencer" },
            { value: "owner", label: "Owner" },
            { value: "none", label: "Unassigned" },
          ]}
        />
        <AdminSelect
          label="Verification"
          value={verification}
          onChange={(value) => {
            setVerification(value);
            setPage(1);
          }}
          options={[
            { value: "", label: "All statuses" },
            { value: "verified", label: "Email verified" },
            { value: "unverified", label: "Email unverified" },
          ]}
        />
      </div>

      <div className="mb-5 max-w-xs">
        <AdminSelect
          label="Sort"
          value={sort}
          onChange={setSort}
          options={[
            { value: "newest", label: "Newest first" },
            { value: "oldest", label: "Oldest first" },
            { value: "name", label: "Name A–Z" },
            { value: "email", label: "Email A–Z" },
          ]}
        />
      </div>

      {users.isLoading ? (
        <LoadingState label="Loading users…" />
      ) : users.isError ? (
        <AdminErrorNote error={users.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="No users found" description="No accounts match the current search and filters." />
      ) : (
        <>
          <UserTable rows={rows} busy={action.isPending || deleteUser.isPending} onAction={setPending} onDelete={setConfirmDelete} />

          <TablePagination page={page} count={users.data?.count ?? 0} pageSize={PAGE_SIZE} onPage={setPage} />

          <ConfirmDialog
            open={pending !== null}
            busy={action.isPending}
            destructive={pending?.action === "suspend"}
            title={
              pending?.action === "suspend"
                ? "Suspend this account?"
                : pending?.action === "activate"
                  ? "Reactivate this account?"
                  : "Approve this creator profile?"
            }
            message={
              pending?.action === "suspend"
                ? `${pending.user.name} will immediately lose access to their workspace. You can reactivate later.`
                : pending?.action === "activate"
                  ? `${pending.user.name} will regain full access to their workspace.`
                  : `${pending?.user.name ?? ""} will receive the verified badge and an approval notification.`
            }
            confirmLabel={
              pending?.action === "suspend"
                ? "Suspend account"
                : pending?.action === "activate"
                  ? "Activate account"
                  : "Approve profile"
            }
            onCancel={() => setPending(null)}
            onConfirm={() => pending && action.mutate({ id: pending.user.id, act: pending.action })}
          />

          <ConfirmDialog
            open={confirmDelete !== null}
            busy={deleteUser.isPending}
            title="Permanently delete this account?"
            message={`Are you sure you want to permanently delete ${confirmDelete?.name ?? "this account"} (${confirmDelete?.email ?? ""})? This also removes their profile and campaigns. This action cannot be undone.`}
            confirmLabel="Delete forever"
            onCancel={() => setConfirmDelete(null)}
            onConfirm={() => confirmDelete && deleteUser.mutate(confirmDelete.id)}
          />
        </>
      )}
    </AdminShell>
  );
}

function UserTable({
  rows,
  busy,
  onAction,
  onDelete,
}: {
  rows: AdminUserRow[];
  busy: boolean;
  onAction: (pending: PendingAction) => void;
  onDelete: (user: AdminUserRow) => void;
}) {
  return (
    <AdminTable headers={["User", "Role", "Email verified", "Status", "Profile", "Joined", "Actions"]}>
      {rows.map((user) => (
        <tr key={user.id}>
          <td className="px-4 py-3.5">
            <Link
              href={`/owner/users/${user.id}`}
              className="font-bold text-slate-900 hover:text-violet-600 dark:text-white dark:hover:text-violet-300"
            >
              {user.name}
            </Link>
            <p className="text-xs text-slate-500">{user.email}</p>
          </td>
          <td className="px-4 py-3.5">
            <AdminBadge tone={user.role === "owner" ? "violet" : user.role === "business" ? "blue" : "green"}>
              {user.role ?? "unassigned"}
            </AdminBadge>
          </td>
          <td className="px-4 py-3.5">
            {user.email_verified ? (
              <AdminBadge tone="green">Verified</AdminBadge>
            ) : (
              <AdminBadge tone="amber">Pending OTP</AdminBadge>
            )}
          </td>
          <td className="px-4 py-3.5">
            <AdminBadge tone={statusTone(user.account_status)}>{user.account_status}</AdminBadge>
          </td>
          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
            {user.completion_percentage === null ? "—" : `${user.completion_percentage}%`}
          </td>
          <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">{formatDate(user.date_joined)}</td>
          <td className="px-4 py-3.5">
            <div className="flex items-center gap-1.5">
              <Link
                href={`/owner/users/${user.id}`}
                className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:border-slate-700 dark:hover:bg-slate-900 dark:hover:text-white"
                title="View details"
              >
                <Eye size={15} />
              </Link>
              {user.account_status === "Active" ? (
                <button
                  onClick={() => onAction({ user, action: "suspend" })}
                  disabled={busy}
                  className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-rose-950/40"
                  title="Suspend account"
                >
                  <ShieldOff size={15} />
                </button>
              ) : (
                <button
                  onClick={() => onAction({ user, action: "activate" })}
                  disabled={busy}
                  className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-emerald-50 hover:text-emerald-600 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-emerald-950/40"
                  title="Activate account"
                >
                  <ShieldCheck size={15} />
                </button>
              )}
              {user.role === "influencer" && user.verification_status === "Pending" && (
                <button
                  onClick={() => onAction({ user, action: "verify_profile" })}
                  disabled={busy}
                  className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-violet-50 hover:text-violet-600 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-violet-950/40"
                  title="Approve verification"
                >
                  <CheckCircle2 size={15} />
                </button>
              )}
              <button
                onClick={() => onDelete(user)}
                disabled={busy}
                className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-rose-950/40"
                title="Delete account permanently"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </td>
        </tr>
      ))}
    </AdminTable>
  );
}