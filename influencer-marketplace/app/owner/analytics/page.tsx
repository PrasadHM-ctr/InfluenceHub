"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BadgeCheck, Building2, CheckCircle2, Megaphone, ShieldCheck, UserRoundX, UsersRound } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminStatCard } from "@/components/admin/stat-card";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import { formatMoney } from "@/lib/utils";

export default function OwnerAnalyticsPage() {
  const analytics = useQuery({ queryKey: ["owner-analytics"], queryFn: adminApi.getAnalytics });
  const data = analytics.data;

  return (
    <AdminShell
      active="analytics"
      title="Platform analytics"
      subtitle="Every metric below is aggregated live from PostgreSQL with efficient database queries."
    >
      {analytics.isLoading ? (
        <LoadingState label="Crunching platform numbers…" />
      ) : analytics.isError ? (
        <AdminErrorNote error={analytics.error} />
      ) : !data ? (
        <EmptyState title="No data yet" description="Analytics will appear once accounts and campaigns exist." />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminStatCard label="Total users" value={data.totals.users} icon={UsersRound} />
            <AdminStatCard label="Business users" value={data.totals.business_users} icon={Building2} tone="blue" />
            <AdminStatCard label="Influencers" value={data.totals.influencers} icon={BadgeCheck} tone="emerald" />
            <AdminStatCard label="Campaign budget" value={formatMoney(data.totals.budget_total)} icon={Megaphone} tone="violet" />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminStatCard label="Verified users" value={data.totals.verified_users} icon={ShieldCheck} tone="emerald" />
            <AdminStatCard label="Unverified users" value={data.totals.unverified_users} icon={UserRoundX} tone="amber" />
            <AdminStatCard label="Total campaigns" value={data.totals.campaigns} icon={Megaphone} tone="blue" />
            <AdminStatCard
              label="Completed campaigns"
              value={data.totals.completed_campaigns}
              icon={CheckCircle2}
              tone="rose"
            />
          </div>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="font-extrabold text-slate-900 dark:text-white">Registrations · last 14 days</h3>
            <p className="mt-1 text-sm text-slate-500">Business vs influencer signup volume per day.</p>
            <div className="mt-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={mergeSeries(data.business_registrations, data.influencer_registrations)}
                  margin={{ top: 8, right: 8, left: -24, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="bizGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="infGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="Business" stroke="#0ea5e9" strokeWidth={2} fill="url(#bizGrad)" />
                  <Area type="monotone" dataKey="Influencer" stroke="#7c3aed" strokeWidth={2} fill="url(#infGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <h3 className="font-extrabold text-slate-900 dark:text-white">Campaign status distribution</h3>
              <div className="mt-5 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.campaign_status_distribution.map((row) => ({ name: row.status, count: row.count }))}
                    margin={{ top: 8, right: 0, left: -24, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <Tooltip
                      cursor={{ fill: "#f8fafc" }}
                      contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                    />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]} fill="#a21caf" maxBarSize={48} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <h3 className="font-extrabold text-slate-900 dark:text-white">Campaign activity · last 14 days</h3>
              <div className="mt-5 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={data.campaign_activity.map((point) => ({ date: point.date.slice(5), count: point.count }))}
                    margin={{ top: 8, right: 8, left: -24, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="campGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Campaigns created"
                      stroke="#10b981"
                      strokeWidth={2.5}
                      fill="url(#campGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>
        </>
      )}
    </AdminShell>
  );
}

function mergeSeries(
  business: { date: string; count: number }[],
  influencer: { date: string; count: number }[]
) {
  return business.map((point, index) => ({
    date: point.date.slice(5),
    Business: point.count,
    Influencer: influencer[index]?.count ?? 0,
  }));
}