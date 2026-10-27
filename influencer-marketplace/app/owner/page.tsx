"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BadgeCheck,
  Building2,
  CheckCircle2,
  Clock3,
  Megaphone,
  ShieldCheck,
  TrendingUp,
  UserRoundX,
  UsersRound,
  XCircle,
} from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge } from "@/components/admin/admin-ui";
import { AdminStatCard } from "@/components/admin/stat-card";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import { formatMoney } from "@/lib/utils";

export default function OwnerDashboardPage() {
  const dashboard = useQuery({ queryKey: ["owner-dashboard"], queryFn: adminApi.getDashboard });
  const stats = dashboard.data;

  const registrationChart = [
    { name: "Businesses", count: stats?.users.business ?? 0 },
    { name: "Influencers", count: stats?.users.influencer ?? 0 },
    { name: "Owners", count: stats?.users.owner ?? 0 },
  ];
  const campaignChart = [
    { name: "Pending", count: stats?.campaigns.pending ?? 0 },
    { name: "Accepted", count: stats?.campaigns.accepted ?? 0 },
    { name: "Completed", count: stats?.campaigns.completed ?? 0 },
    { name: "Rejected", count: stats?.campaigns.rejected ?? 0 },
    { name: "Cancelled", count: stats?.campaigns.cancelled ?? 0 },
  ];

  return (
    <AdminShell
      active="dashboard"
      title="Platform overview"
      subtitle="Live figures straight from the InfluenceHub database - nothing cached, nothing faked."
    >
      {dashboard.isLoading ? (
        <LoadingState label="Loading platform statistics…" />
      ) : dashboard.isError ? (
        <AdminErrorNote error={dashboard.error} />
      ) : !stats ? (
        <EmptyState title="No data yet" description="Statistics will appear as soon as accounts exist." />
      ) : (
        <>
          {/* Attention strip */}
          <div className="mb-6 flex flex-wrap items-center gap-3">
            {stats.moderation.pending_verifications > 0 ? (
              <Link
                href="/owner/verifications"
                className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm font-bold text-amber-800 transition hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
              >
                <Clock3 size={16} />
                {stats.moderation.pending_verifications} verification
                {stats.moderation.pending_verifications === 1 ? "" : "s"} awaiting review
              </Link>
            ) : (
              <span className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-bold text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300">
                <ShieldCheck size={16} /> Verification queue clear
              </span>
            )}
            <AdminBadge tone="violet">
              {stats.campaigns.new_today} new campaign{stats.campaigns.new_today === 1 ? "" : "s"} today
            </AdminBadge>
            <AdminBadge tone="blue">{stats.users.new_today} signups today</AdminBadge>
          </div>

          {/* User cards */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminStatCard label="Total users" value={stats.users.total} icon={UsersRound} />
            <AdminStatCard label="Business users" value={stats.users.business} icon={Building2} tone="blue" />
            <AdminStatCard label="Influencers" value={stats.users.influencer} icon={BadgeCheck} tone="emerald" />
            <AdminStatCard label="Verified users" value={stats.users.verified} icon={ShieldCheck} tone="emerald" />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminStatCard label="Unverified users" value={stats.users.unverified} icon={UserRoundX} tone="amber" />
            <AdminStatCard label="New this week" value={stats.users.new_this_week} icon={TrendingUp} />
            <AdminStatCard label="Total campaigns" value={stats.campaigns.total} icon={Megaphone} tone="blue" />
            <AdminStatCard
              label="Campaign budget"
              value={formatMoney(stats.campaigns.budget_total)}
              icon={Megaphone}
              tone="violet"
            />
          </div>

          {/* Campaign status */}
          <h2 className="mb-3 mt-8 font-extrabold text-slate-900 dark:text-white">Campaign pipeline</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminStatCard label="Pending campaigns" value={stats.campaigns.pending} icon={Clock3} tone="amber" />
            <AdminStatCard label="Active (accepted)" value={stats.campaigns.accepted} icon={CheckCircle2} tone="emerald" />
            <AdminStatCard label="Completed" value={stats.campaigns.completed} icon={CheckCircle2} tone="blue" />
            <AdminStatCard label="Rejected" value={stats.campaigns.rejected} icon={XCircle} tone="rose" />
          </div>

          {/* Charts */}
          <DashboardCharts
            registrationChart={registrationChart}
            campaignChart={campaignChart}
          />
          <RegistrationsTrend />
        </>
      )}
    </AdminShell>
  );
}

function DashboardCharts({
  registrationChart,
  campaignChart,
}: {
  registrationChart: { name: string; count: number }[];
  campaignChart: { name: string; count: number }[];
}) {
  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h3 className="font-extrabold text-slate-900 dark:text-white">Users by role</h3>
        <p className="mt-1 text-sm text-slate-500">Registered accounts per account type.</p>
        <div className="mt-5 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={registrationChart} margin={{ top: 8, right: 0, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
              <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
              <Bar dataKey="count" radius={[8, 8, 0, 0]} fill="#7c3aed" maxBarSize={64} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h3 className="font-extrabold text-slate-900 dark:text-white">Campaign status distribution</h3>
        <p className="mt-1 text-sm text-slate-500">Every campaign request by current decision state.</p>
        <div className="mt-5 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={campaignChart} margin={{ top: 8, right: 0, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
              <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
              <Bar dataKey="count" radius={[8, 8, 0, 0]} fill="#a21caf" maxBarSize={44} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}

function RegistrationsTrend() {
  const analytics = useQuery({ queryKey: ["owner-analytics"], queryFn: adminApi.getAnalytics });
  if (analytics.isLoading || analytics.isError) return null;
  const series = (analytics.data?.users_over_time ?? []).map((point) => ({
    date: point.date.slice(5),
    count: point.count,
  }));
  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <h3 className="font-extrabold text-slate-900 dark:text-white">New registrations · last 14 days</h3>
      <p className="mt-1 text-sm text-slate-500">Daily signup volume across all roles.</p>
      <div className="mt-5 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="regGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
            <Area type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2.5} fill="url(#regGradient)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}