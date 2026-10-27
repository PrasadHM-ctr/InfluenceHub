"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Copy, ExternalLink, ShieldOff, ShieldCheck, Trash2 } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, RiskBadge, statusTone } from "@/components/admin/admin-ui";
import { ConfirmDialog } from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi, getAdminApiError } from "@/services/admin-api";
import type { AdminUserProfile } from "@/types/admin";
import { formatDate, formatFollowers, formatMoney } from "@/lib/utils";

export default function OwnerUserDetailPage() {
  const params = useParams<{ id: string }>();
  const userId = Number(params.id);
  const queryClient = useQueryClient();
  const [confirmSuspend, setConfirmSuspend] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const user = useQuery({
    queryKey: ["owner-user", userId],
    queryFn: () => adminApi.getUser(userId),
    retry: false,
  });

  const action = useMutation({
    mutationFn: (act: "suspend" | "activate" | "verify_profile" | "reject_profile") =>
      adminApi.userAction(userId, act),
    onSuccess: (result) => {
      toast.success(result.detail);
      setConfirmSuspend(false);
      queryClient.invalidateQueries({ queryKey: ["owner-user", userId] });
      queryClient.invalidateQueries({ queryKey: ["owner-users"] });
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const deleteUser = useMutation({
    mutationFn: () => adminApi.deleteUser(userId),
    onSuccess: () => {
      toast.success("Account permanently deleted.");
      queryClient.invalidateQueries({ queryKey: ["owner-users"] });
      window.location.href = "/owner/users";
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const detail = user.data;
  const profile: AdminUserProfile | null = detail?.profile ?? null;
  const notFound =
    !user.isLoading &&
    String((user.error as { response?: { status?: number } })?.response?.status ?? "") === "404";

  return (
    <AdminShell
      active="users"
      title={detail ? detail.username : "User details"}
      subtitle="Full account inspection - profile signals, campaign activity and moderation controls."
    >
      <Link
        href="/owner/users"
        className="mb-5 inline-flex items-center gap-1.5 text-sm font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
      >
        <ArrowLeft size={15} /> Back to all users
      </Link>

      {user.isLoading ? (
        <LoadingState label="Loading account details…" />
      ) : user.isError ? (
        <div className="space-y-4">
          <AdminErrorNote error={user.error} />
          {notFound && <EmptyState title="User not found" description="This account may have been deleted." />}
        </div>
      ) : !detail ? null : (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
          {/* Left column */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="flex flex-wrap items-center gap-3">
              {profile?.image_url || profile?.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element -- dynamic signed media URLs
                <img
                  src={(profile.image_url ?? profile.logo_url) as string}
                  alt=""
                  className="h-14 w-14 rounded-xl object-cover ring-1 ring-slate-200 dark:ring-slate-700"
                />
              ) : (
                <span className="grid h-14 w-14 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 text-lg font-black text-white">
                  {detail.username.slice(0, 2).toUpperCase()}
                </span>
              )}
              <div>
                <h2 className="text-lg font-extrabold text-slate-900 dark:text-white">
                  {profile?.full_name || profile?.company_name || detail.username}
                </h2>
                <p className="text-sm text-slate-500">{detail.email}</p>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <AdminBadge tone={detail.role === "owner" ? "violet" : detail.role === "business" ? "blue" : "green"}>
                  {detail.role ?? "unassigned"}
                </AdminBadge>
                <AdminBadge tone={statusTone(detail.account_status)}>{detail.account_status}</AdminBadge>
              </div>
            </div>

            <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
              <Info label="Email verified">
                {detail.email_verified ? <AdminBadge tone="green">Yes</AdminBadge> : <AdminBadge tone="amber">No</AdminBadge>}
              </Info>
              <Info label="Registration date">{formatDate(detail.date_joined)}</Info>
              <Info label="Last activity">{detail.last_activity ? formatDate(detail.last_activity) : "—"}</Info>
              <Info label="Profile completion">{`${profile?.completion_percentage ?? 0}%`}</Info>
            </dl>

            {profile && <ProfileSection profile={profile} />}

            {/* Moderation actions */}
            <div className="mt-7 flex flex-wrap gap-2 border-t border-slate-100 pt-5 dark:border-slate-800">
              {detail.account_status === "Active" ? (
                <button
                  onClick={() => setConfirmSuspend(true)}
                  disabled={action.isPending}
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-200 px-4 py-2.5 text-sm font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:hover:bg-rose-950/40"
                >
                  <ShieldOff size={15} /> Suspend account
                </button>
              ) : (
                <button
                  onClick={() => action.mutate("activate")}
                  disabled={action.isPending}
                  className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 px-4 py-2.5 text-sm font-bold text-emerald-600 transition hover:bg-emerald-50 disabled:opacity-60 dark:border-emerald-900/60 dark:hover:bg-emerald-950/40"
                >
                  <ShieldCheck size={15} /> Activate account
                </button>
              )}
              {profile?.type === "influencer" && profile.verification_status === "Pending" && (
                <>
                  <button
                    onClick={() => action.mutate("verify_profile")}
                    disabled={action.isPending}
                    className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:opacity-60"
                  >
                    Approve verification
                  </button>
                  <button
                    onClick={() => action.mutate("reject_profile")}
                    disabled={action.isPending}
                    className="inline-flex items-center gap-2 rounded-xl border border-rose-200 px-4 py-2.5 text-sm font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:hover:bg-rose-950/40"
                  >
                    Reject verification
                  </button>
                </>
              )}
              <button
                onClick={() => setConfirmDelete(true)}
                disabled={deleteUser.isPending}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-200 px-4 py-2.5 text-sm font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:hover:bg-rose-950/40"
              >
                <Trash2 size={15} /> Delete account
              </button>
            </div>
          </section>

          {/* Right column: campaigns */}
          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <h3 className="font-extrabold text-slate-900 dark:text-white">Campaign activity</h3>
              <p className="mt-1 text-sm text-slate-500">
                {detail.campaigns.total} campaign{detail.campaigns.total === 1 ? "" : "s"} involving this account.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(detail.campaigns.by_status).map(([campaignStatus, count]) => (
                  <AdminBadge key={campaignStatus} tone={statusTone(campaignStatus)}>
                    {campaignStatus}: {count}
                  </AdminBadge>
                ))}
                {detail.campaigns.total === 0 && <span className="text-sm text-slate-400">No campaigns yet.</span>}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <h3 className="font-extrabold text-slate-900 dark:text-white">Recent campaigns</h3>
              {detail.campaigns.recent.length === 0 ? (
                <EmptyState
                  title="Nothing here yet"
                  description="Campaigns will appear once this account participates in one."
                />
              ) : (
                <ul className="mt-4 space-y-3">
                  {detail.campaigns.recent.map((item) => (
                    <li key={item.id} className="rounded-xl border border-slate-100 p-3.5 dark:border-slate-800">
                      <div className="flex items-center justify-between gap-2">
                        <Link
                          href={`/owner/campaigns?open=${item.id}`}
                          className="text-sm font-bold text-slate-900 hover:text-violet-600 dark:text-white dark:hover:text-violet-300"
                        >
                          {item.title} <ExternalLink size={12} className="ml-1 inline" />
                        </Link>
                        <AdminBadge tone={statusTone(item.status)}>{item.status}</AdminBadge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.business} → {item.influencer} · {formatMoney(item.budget)}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400">Updated {formatDate(item.updated_at)}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmSuspend}
        busy={action.isPending}
        title="Suspend this account?"
        message="The user will immediately lose access to their workspace. You can reactivate the account later."
        confirmLabel="Suspend account"
        onCancel={() => setConfirmSuspend(false)}
        onConfirm={() => action.mutate("suspend")}
      />
      <ConfirmDialog
        open={confirmDelete}
        busy={deleteUser.isPending}
        title="Permanently delete this account?"
        message={`Are you sure you want to permanently delete ${detail?.username ?? "this account"}? This also removes their profile and related campaigns. This action cannot be undone.`}
        confirmLabel="Delete forever"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => deleteUser.mutate()}
      />
    </AdminShell>
  );
}

function Info({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-1 font-semibold text-slate-900 dark:text-white">{children}</dd>
    </div>
  );
}

function ProfileSection({ profile }: { profile: AdminUserProfile }) {
  return (
    <>
      <h3 className="mb-3 mt-6 text-xs font-bold uppercase tracking-wide text-slate-400">
        {profile.type === "influencer" ? "Creator profile" : "Business profile"}
      </h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
        {profile.type === "influencer" ? (
          <>
            <Info label="Category">{profile.category}</Info>
            <Info label="Language">{profile.language}</Info>
            <Info label="Location">{[profile.city, profile.state].filter(Boolean).join(", ") || "—"}</Info>
            <Info label="Followers">{formatFollowers(profile.followers ?? 0)}</Info>
            <Info label="Verification badge">
              <AdminBadge tone={statusTone(profile.verification_status ?? "")}>
                {profile.verification_status}
              </AdminBadge>
            </Info>
            <Info label="Instagram bio code">
              {profile.social_verification_code || profile.verification_code ? (
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-xs font-bold text-violet-700 bg-violet-50 dark:bg-violet-950/50 dark:text-violet-300 border border-violet-200 dark:border-violet-800 rounded px-2 py-0.5">
                    {profile.social_verification_code || profile.verification_code}
                  </span>
                  <button
                    type="button"
                    onClick={async () => {
                      const c = profile.social_verification_code || profile.verification_code || "";
                      await navigator.clipboard.writeText(c);
                      toast.success(`Copied code "${c}"!`);
                    }}
                    title="Copy code"
                    className="rounded p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <Copy size={12} />
                  </button>
                </div>
              ) : (
                <span className="text-slate-400">{profile.social_code_configured ? "Configured" : "None"}</span>
              )}
            </Info>
          </>
        ) : (
          <>
            <Info label="Industry">{profile.industry}</Info>
            <Info label="Phone">{profile.phone}</Info>
            <Info label="Location">{[profile.city, profile.state].filter(Boolean).join(", ") || "—"}</Info>
            <Info label="Website">{profile.website || "—"}</Info>
          </>
        )}
      </dl>

      {profile.bio && (
        <p className="mt-4 rounded-xl bg-slate-50 p-3.5 text-sm leading-6 text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          {profile.bio}
        </p>
      )}

      {profile.type === "influencer" && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {(["instagram", "youtube", "facebook"] as const)
              .filter((network) => profile[network])
              .map((network) => (
                <a
                  key={network}
                  href={profile[network]}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold capitalize text-slate-600 transition hover:border-violet-300 hover:text-violet-600 dark:border-slate-700 dark:text-slate-300"
                >
                  {network} <ExternalLink size={11} />
                </a>
              ))}
          </div>
          {/* Explicitly a moderation signal - never presented as proof of fraud. */}
          <div className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <RiskBadge score={profile.risk_score ?? 0} />
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                Risk score · moderation signal, not proof of fraud
              </p>
              <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-xs text-slate-500">
                {(profile.risk_signals ?? []).length === 0 ? (
                  <li>No negative signals recorded.</li>
                ) : (
                  profile.risk_signals?.map((signal) => <li key={signal}>{signal}</li>)
                )}
              </ul>
            </div>
          </div>
        </div>
      )}

      {(profile.missing_fields?.length ?? 0) > 0 && (
        <p className="mt-4 text-xs text-slate-400">Missing profile fields: {profile.missing_fields?.join(", ")}</p>
      )}
    </>
  );
}