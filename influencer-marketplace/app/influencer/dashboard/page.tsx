"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, IndianRupee } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/auth-context";
import { PortalShell } from "@/components/layout/portal-shell";
import { api, getApiError } from "@/services/api";
import { CampaignCard } from "@/components/campaigns/campaign-card";
import { ErrorState, EmptyState, LoadingState } from "@/components/ui/state";
import { StatCard } from "@/components/ui/stat-card";
import { formatMoney } from "@/lib/utils";

export default function InfluencerDashboard() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const campaigns = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.getCampaigns(),
    enabled: auth.isReady && auth.role === "influencer",
  });

  const action = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: "accept" | "reject" }) =>
      decision === "accept" ? api.acceptCampaign(id) : api.rejectCampaign(id),
    onSuccess: (_, variables) => {
      toast.success(variables.decision === "accept" ? "Campaign accepted." : "Campaign declined.");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (error) => toast.error(getApiError(error)),
  });

  const data = campaigns.data ?? [];
  const pending = data.filter((item) => item.status === "Pending");
  const accepted = data.filter((item) => item.status === "Accepted");
  const acceptedValue = accepted.reduce((sum, item) => sum + Number(item.budget), 0);

  return (
    <PortalShell
      role="influencer"
      title="Your campaign inbox"
      subtitle="Review incoming offers, make confident decisions, and keep opportunities moving."
    >
      {campaigns.isLoading ? (
        <LoadingState label="Loading campaign requests…" />
      ) : campaigns.error ? (
        <ErrorState message={getApiError(campaigns.error)} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="All requests" value={data.length} icon={IndianRupee} tone="blue" />
            <StatCard label="Need a response" value={pending.length} icon={Clock3} tone="amber" />
            <StatCard label="Accepted campaigns" value={accepted.length} icon={CheckCircle2} tone="emerald" />
            <StatCard label="Accepted value" value={formatMoney(acceptedValue)} icon={IndianRupee} />
          </div>

          <section className="mt-8">
            <div className="mb-4">
              <h2 className="font-extrabold text-slate-900 dark:text-white">Requests awaiting your decision</h2>
              <p className="mt-1 text-sm text-slate-500">
                Accept a campaign when it is a good fit, or decline it if it is not right for you.
              </p>
            </div>

            {pending.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {pending.map((campaign) => (
                  <CampaignCard
                    key={campaign.id}
                    campaign={campaign}
                    actions={
                      <>
                        <button
                          disabled={action.isPending}
                          onClick={() => action.mutate({ id: campaign.id, decision: "accept" })}
                          className="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:opacity-60"
                        >
                          {action.isPending ? "Updating…" : "Accept"}
                        </button>
                        <button
                          disabled={action.isPending}
                          onClick={() => action.mutate({ id: campaign.id, decision: "reject" })}
                          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300"
                        >
                          {action.isPending ? "Updating…" : "Decline"}
                        </button>
                      </>
                    }
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="Your inbox is clear"
                description="New brand proposals will appear here when a business sends one to you."
              />
            )}
          </section>

          <section className="mt-8">
            <div className="mb-4">
              <h2 className="font-extrabold text-slate-900 dark:text-white">Campaign history</h2>
              <p className="mt-1 text-sm text-slate-500">Your accepted and declined campaign requests.</p>
            </div>

            {data.filter((item) => item.status !== "Pending").length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data
                  .filter((item) => item.status !== "Pending")
                  .map((campaign) => (
                    <CampaignCard key={campaign.id} campaign={campaign} />
                  ))}
              </div>
            ) : (
              <EmptyState
                title="No decisions yet"
                description="Campaigns you accept or decline will remain available here for reference."
              />
            )}
          </section>
        </>
      )}
    </PortalShell>
  );
}
