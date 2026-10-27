"use client";

import { useQuery } from "@tanstack/react-query";
import { KeyRound, ShieldCheck, UserCog } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge } from "@/components/admin/admin-ui";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import { formatDate } from "@/lib/utils";

export default function OwnerSettingsPage() {
  const settings = useQuery({ queryKey: ["owner-settings"], queryFn: adminApi.getSettings });
  const data = settings.data;

  return (
    <AdminShell
      active="settings"
      title="Security & account settings"
      subtitle="Read-only overview of owner accounts and recent privileged activity."
    >
      {settings.isLoading ? (
        <LoadingState label="Loading security overview…" />
      ) : settings.isError ? (
        <AdminErrorNote error={settings.error} />
      ) : !data ? (
        <EmptyState title="No data" description="Settings could not be loaded." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Session identity */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-950/50 dark:text-violet-300">
                <UserCog size={20} />
              </span>
              <h2 className="font-extrabold text-slate-900 dark:text-white">Your session</h2>
            </div>
            <dl className="mt-5 space-y-3 text-sm">
              <Row label="Username" value={data.session_user.username} />
              <Row label="Email" value={data.session_user.email} />
              <Row
                label="Role"
                value={
                  <span className="flex items-center gap-2">
                    <AdminBadge tone="violet">{data.session_user.role ?? "owner"}</AdminBadge>
                    {data.session_user.is_superuser && <AdminBadge tone="blue">Django superuser</AdminBadge>}
                  </span>
                }
              />
              <Row label="Member since" value={formatDate(data.session_user.date_joined)} />
            </dl>
          </section>

          {/* Security posture */}
          <section className="rounded-2xl bg-[#28245c] p-6 text-white">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 text-violet-200">
                <ShieldCheck size={20} />
              </span>
              <h2 className="font-extrabold">How this panel is protected</h2>
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-indigo-100">
              <li>• Authorization is enforced by the Django backend on every request - never by the browser.</li>
              <li>• Only accounts with the explicit database role `owner` (or a Django superuser) pass.</li>
              <li>• There is no public admin signup; owner accounts exist only via `manage.py create_owner`.</li>
              <li>• Dangerous actions require confirmation and are written to an immutable audit log.</li>
              <li>• Passwords, OTP codes and cloud credentials are never stored or displayed here.</li>
            </ul>
            <p className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 text-xs font-bold">
              <KeyRound size={14} /> {data.owner_accounts.length} active owner account
              {data.owner_accounts.length === 1 ? "" : "s"} configured
            </p>
          </section>

          <OwnerAccounts data={data.owner_accounts} />
          <RecentActions entries={data.recent_admin_actions} />
        </div>
      )}
    </AdminShell>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2.5 last:border-none dark:border-slate-800">
      <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="font-semibold text-slate-900 dark:text-white">{value}</dd>
    </div>
  );
}

type SettingsData = Awaited<ReturnType<typeof adminApi.getSettings>>;

function OwnerAccounts({ data }: { data: SettingsData["owner_accounts"] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950 lg:col-span-2">
      <h2 className="font-extrabold text-slate-900 dark:text-white">Owner accounts</h2>
      <p className="mt-1 text-sm text-slate-500">
        Accounts holding the platform-owner role. Provision new ones from the server with{" "}
        <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs dark:bg-slate-900">
          python manage.py create_owner --username &lt;name&gt; --email &lt;email&gt;
        </code>
      </p>
      <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
        {data.map((account) => (
          <li key={account.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
            <div>
              <p className="font-bold text-slate-900 dark:text-white">{account.username}</p>
              <p className="text-xs text-slate-500">{account.email}</p>
            </div>
            <div className="flex items-center gap-2">
              <AdminBadge tone="violet">owner</AdminBadge>
              {account.is_superuser && <AdminBadge tone="blue">superuser</AdminBadge>}
              <span className="text-xs text-slate-400">since {formatDate(account.date_joined)}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function RecentActions({ entries }: { entries: SettingsData["recent_admin_actions"] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950 lg:col-span-2">
      <h2 className="font-extrabold text-slate-900 dark:text-white">Recent privileged actions</h2>
      {entries.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">No admin actions recorded yet.</p>
      ) : (
        <ul className="mt-4 space-y-2.5">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="flex flex-wrap items-baseline justify-between gap-x-3 rounded-xl border border-slate-100 p-3 text-sm dark:border-slate-800"
            >
              <span className="text-slate-600 dark:text-slate-300">
                <strong className="text-slate-900 dark:text-white">{entry.actor}</strong> {entry.description || entry.action}
              </span>
              <span className="text-xs text-slate-400">{new Date(entry.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}