"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CheckCircle2, Clock3, Send, UsersRound, XCircle } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/auth-context";
import { PortalShell } from "@/components/layout/portal-shell";
import { api, getApiError } from "@/services/api";
import { CampaignCard } from "@/components/campaigns/campaign-card";
import { ErrorState, EmptyState, LoadingState } from "@/components/ui/state";
import { StatCard } from "@/components/ui/stat-card";

export default function BusinessDashboard() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const dashboard = useQuery({
    queryKey: ["business-dashboard"],
    queryFn: api.getBusinessDashboard,
    enabled: auth.isReady && auth.role === "business",
  });
  const campaigns = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.getCampaigns(),
    enabled: auth.isReady && auth.role === "business",
  });

  const cancelAction = useMutation({
    mutationFn: (id: number) => api.cancelCampaign(id),
    onSuccess: () => {
      toast.success("Campaign request cancelled.");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["business-dashboard"] });
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const completeAction = useMutation({
    mutationFn: (id: number) => api.completeCampaign(id),
    onSuccess: () => {
      toast.success("Campaign marked as completed.");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["business-dashboard"] });
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const isLoading = dashboard.isLoading || campaigns.isLoading;
  const error = dashboard.error ?? campaigns.error;
  const stats = dashboard.data;
  const chartData = stats
    ? [
        { name: "Pending", value: stats.pending },
        { name: "Accepted", value: stats.accepted },
        { name: "Rejected", value: stats.rejected },
      ]
    : [];

  return (
    <PortalShell
      role="business"
      title="Campaign overview"
      subtitle="Keep a clear view of every creator conversation and campaign decision."
    >
      {isLoading ? (
        <LoadingState label="Loading campaign workspace…" />
      ) : error ? (
        <ErrorState message={getApiError(error)} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total campaigns" value={stats?.total_campaigns ?? 0} icon={Send} />
            <StatCard label="Pending review" value={stats?.pending ?? 0} icon={Clock3} tone="amber" />
            <StatCard label="Accepted" value={stats?.accepted ?? 0} icon={CheckCircle2} tone="emerald" />
            <StatCard label="Declined" value={stats?.rejected ?? 0} icon={XCircle} tone="blue" />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-extrabold text-slate-900 dark:text-white">Campaign decisions</h2>
                  <p className="mt-1 text-sm text-slate-500">A status breakdown across your campaign requests.</p>
                </div>
              </div>
              <div className="mt-5 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 0, left: -28, bottom: 0 }}>
                    <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                    <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#7c3aed" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="rounded-2xl bg-[#28245c] p-6 text-white">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 text-violet-200">
                <UsersRound size={20} />
              </span>
              <h2 className="mt-6 text-xl font-extrabold">Find your next great fit.</h2>
              <p className="mt-3 max-w-sm text-sm leading-6 text-indigo-100">
                Search creators by their category, audience size, and location. Open a profile when you are ready to send a campaign proposal.
              </p>
              <Link
                href="/business/influencers"
                className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-indigo-950 transition hover:bg-violet-100"
              >
                Discover creators <UsersRound size={16} />
              </Link>
            </section>
          </div>

          <section className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-extrabold text-slate-900 dark:text-white">Recent campaigns</h2>
                <p className="mt-1 text-sm text-slate-500">Latest requests sent from your business workspace.</p>
              </div>
              <Link href="/business/influencers" className="text-sm font-bold text-violet-600 hover:text-violet-500">
                Find creators
              </Link>
            </div>

            {campaigns.data?.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {campaigns.data.slice(0, 6).map((campaign) => (
                  <CampaignCard
                    key={campaign.id}
                    campaign={campaign}
                    actions={
                      campaign.status === "Pending" ? (
                        <button
                          disabled={cancelAction.isPending}
                          onClick={() => {
                            if (window.confirm("Are you sure you want to cancel this campaign proposal?")) {
                              cancelAction.mutate(campaign.id);
                            }
                          }}
                          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300"
                        >
                          {cancelAction.isPending ? "Cancelling…" : "Cancel proposal"}
                        </button>
                      ) : campaign.status === "Accepted" ? (
                        <button
                          disabled={completeAction.isPending}
                          onClick={() => {
                            if (window.confirm("Mark this campaign partnership as completed?")) {
                              completeAction.mutate(campaign.id);
                            }
                          }}
                          className="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-emerald-500 disabled:opacity-60"
                        >
                          {completeAction.isPending ? "Completing…" : "Mark completed"}
                        </button>
                      ) : undefined
                    }
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No campaigns yet"
                description="When you send a proposal to a creator, it will appear here with its current status."
              />
            )}
          </section>
        </>
      )}
    </PortalShell>
  );
}
