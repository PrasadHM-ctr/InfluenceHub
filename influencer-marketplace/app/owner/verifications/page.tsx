"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Copy, ExternalLink, ShieldCheck, XCircle } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, RiskBadge, statusTone } from "@/components/admin/admin-ui";
import {
  AdminSearchInput,
  AdminTable,
  TablePagination,
} from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi, getAdminApiError } from "@/services/admin-api";
import type { AdminVerificationRow } from "@/types/admin";

const PAGE_SIZE = 20;

type Decision = {
  profile: AdminVerificationRow;
  decision: "approved" | "rejected";
} | null;

export default function OwnerVerificationsPage() {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("Pending");
  const [page, setPage] = useState(1);
  const [pending, setPending] = useState<Decision>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const queue = useQuery({
    queryKey: ["owner-verifications", { search, status: statusFilter, page }],
    queryFn: () => adminApi.getVerifications({ search, status: statusFilter, page }),
    placeholderData: keepPreviousData,
  });

  const review = useMutation({
    mutationFn: ({
      id,
      decision,
      reason,
    }: {
      id: number;
      decision: "approved" | "rejected";
      reason?: string;
    }) => adminApi.reviewVerification(id, decision, reason),
    onSuccess: (result) => {
      toast.success(result.detail);
      setPending(null);
      setRejectionReason("");
      queryClient.invalidateQueries({ queryKey: ["owner-verifications"] });
      queryClient.invalidateQueries({ queryKey: ["owner-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["owner-attention"] });
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const rows: AdminVerificationRow[] = queue.data?.results ?? [];
  const counts = queue.data?.counts ?? {};

  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success(`Copied code "${code}" to clipboard!`);
    } catch {
      toast.error("Failed to copy code to clipboard.");
    }
  };

  return (
    <AdminShell
      active="verifications"
      title="Verification review"
      subtitle="Creator badge requests. Match the generated bio verification code against the influencer's live Instagram bio before approving."
    >
      <div className="mb-5 flex flex-wrap items-end gap-2">
        {(["Pending", "Approved", "Rejected", "all"] as const).map((value) => {
          const count = value === "all" ? counts["all"] ?? 0 : counts[value] ?? 0;
          return (
            <button
              key={value}
              onClick={() => {
                setStatusFilter(value);
                setPage(1);
              }}
              className={`rounded-xl px-4 py-2 text-sm font-bold capitalize transition ${
                statusFilter === value
                  ? "bg-violet-600 text-white shadow-sm"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
              }`}
            >
              {value === "all" ? "All requests" : value} · {count}
            </button>
          );
        })}
        <div className="ml-auto w-full sm:w-80">
          <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-400">
            Search
          </span>
          <AdminSearchInput
            value={searchInput}
            placeholder="Name, email, username, or code…"
            onChange={setSearchInput}
          />
        </div>
      </div>

      {queue.isLoading ? (
        <LoadingState label="Loading verification queue…" />
      ) : queue.isError ? (
        <AdminErrorNote error={queue.error} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nothing to review"
          description={
            statusFilter === "all"
              ? "No verification requests match your search criteria."
              : `There are no ${statusFilter.toLowerCase()} verification requests right now.`
          }
        />
      ) : (
        <>
          <ReviewTable
            rows={rows}
            busy={review.isPending}
            onDecide={(decision) => {
              setRejectionReason("");
              setPending(decision);
            }}
            onCopyCode={handleCopyCode}
          />
          <TablePagination
            page={page}
            count={queue.data?.count ?? 0}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />

          {/* Action confirmation dialog */}
          {pending !== null && (
            <div
              className="fixed inset-0 z-50 grid place-items-center px-4"
              role="alertdialog"
              aria-modal="true"
            >
              <button
                aria-label="Cancel action"
                className="absolute inset-0 bg-slate-950/60"
                onClick={() => setPending(null)}
              />
              <div className="relative w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-950">
                <div className="flex items-start gap-3">
                  <span
                    className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${
                      pending.decision === "approved"
                        ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-300"
                        : "bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-300"
                    }`}
                  >
                    {pending.decision === "approved" ? (
                      <CheckCircle2 size={20} />
                    ) : (
                      <XCircle size={20} />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
                      {pending.decision === "approved"
                        ? `Approve ${pending.profile.full_name}?`
                        : `Reject ${pending.profile.full_name}?`}
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {pending.decision === "approved"
                        ? `${pending.profile.full_name} (Account ID #${pending.profile.user_id}) will receive the verified badge on their creator profile and a notification.`
                        : `${pending.profile.full_name} will be marked as rejected. They will be notified and can re-apply after updating their Instagram bio.`}
                    </p>

                    {pending.profile.social_verification_code && (
                      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-900">
                        <span className="font-bold text-slate-500">Expected Bio Code: </span>
                        <span className="font-mono font-black text-violet-600 dark:text-violet-400">
                          {pending.profile.social_verification_code}
                        </span>
                      </div>
                    )}

                    {pending.decision === "rejected" && (
                      <div className="mt-4">
                        <label className="block text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Rejection Reason (optional — shared with creator)
                        </label>
                        <textarea
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder="e.g. Verification code not found in Instagram bio, or Instagram profile is private."
                          className="mt-1.5 min-h-20 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none transition focus:border-rose-500 focus:ring-4 focus:ring-rose-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-rose-950"
                        />
                      </div>
                    )}

                    <div className="mt-6 flex justify-end gap-2">
                      <button
                        type="button"
                        disabled={review.isPending}
                        onClick={() => setPending(null)}
                        className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={review.isPending}
                        onClick={() =>
                          review.mutate({
                            id: pending.profile.id,
                            decision: pending.decision,
                            reason: rejectionReason,
                          })
                        }
                        className={`rounded-xl px-4 py-2 text-sm font-bold text-white transition disabled:opacity-60 ${
                          pending.decision === "approved"
                            ? "bg-emerald-600 hover:bg-emerald-500"
                            : "bg-rose-600 hover:bg-rose-500"
                        }`}
                      >
                        {review.isPending
                          ? "Processing…"
                          : pending.decision === "approved"
                          ? "Approve verification"
                          : "Reject verification"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </AdminShell>
  );
}

function formatFollowersShort(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

function extractInstagramHandle(url?: string): { handle: string; href: string } | null {
  if (!url) return null;
  try {
    const raw = url.startsWith("http") ? url : `https://${url}`;
    const parsed = new URL(raw);
    const parts = parsed.pathname.split("/").filter(Boolean);
    const handle = parts[0] ? `@${parts[0]}` : "Instagram Profile";
    return { handle, href: parsed.href };
  } catch {
    return { handle: "Instagram Profile", href: url };
  }
}

function ReviewTable({
  rows,
  busy,
  onDecide,
  onCopyCode,
}: {
  rows: AdminVerificationRow[];
  busy: boolean;
  onDecide: (decision: Decision) => void;
  onCopyCode: (code: string) => void;
}) {
  return (
    <AdminTable
      headers={[
        "Creator & Account",
        "Instagram Bio Code",
        "Social Links",
        "Signals & Requested",
        "Status",
        "Actions",
      ]}
    >
      {rows.map((row) => {
        const ig = extractInstagramHandle(row.instagram);
        const code = row.social_verification_code || row.verification_code;

        return (
          <tr key={row.id}>
            {/* Creator Column */}
            <td className="px-4 py-3.5">
              <div className="flex items-center gap-3">
                {row.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element -- dynamic signed media URLs
                  <img
                    src={row.image_url}
                    alt=""
                    className="h-10 w-10 shrink-0 rounded-xl object-cover ring-1 ring-slate-200 dark:ring-slate-700"
                  />
                ) : (
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-xs font-black text-slate-500 dark:bg-slate-800">
                    {row.full_name.slice(0, 2).toUpperCase()}
                  </span>
                )}
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 dark:text-white">{row.full_name}</p>
                  <p className="text-xs text-slate-500">{row.email}</p>
                  <p className="text-xs text-slate-400">
                    <span className="font-mono text-violet-600 dark:text-violet-400">
                      ID #{row.user_id}
                    </span>
                    {row.username ? ` · @${row.username}` : ""}
                  </p>
                  <p className="text-xs text-slate-400">
                    {row.category} · {[row.city, row.state].filter(Boolean).join(", ")}
                  </p>
                </div>
              </div>
            </td>

            {/* Generated Instagram Bio Verification Code */}
            <td className="px-4 py-3.5">
              {code ? (
                <div>
                  <div className="inline-flex items-center gap-1.5 rounded-xl border border-violet-200 bg-violet-50/80 px-2.5 py-1.5 shadow-xs dark:border-violet-900/60 dark:bg-violet-950/40">
                    <span className="font-mono text-sm font-black tracking-wider text-violet-900 dark:text-violet-100">
                      {code}
                    </span>
                    <button
                      type="button"
                      onClick={() => onCopyCode(code)}
                      title="Copy verification code"
                      className="rounded-md p-1 text-violet-600 hover:bg-violet-200/60 dark:text-violet-300 dark:hover:bg-violet-900/60"
                    >
                      <Copy size={13} />
                    </button>
                  </div>
                  <span className="mt-1 block text-[11px] text-slate-400">
                    Check for this code in bio
                  </span>
                </div>
              ) : (
                <span className="text-xs italic text-slate-400">No code generated</span>
              )}
            </td>

            {/* Social Links */}
            <td className="px-4 py-3.5">
              <div className="flex flex-col gap-1.5">
                {ig ? (
                  <a
                    href={ig.href}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 text-xs font-bold text-fuchsia-600 hover:underline dark:text-fuchsia-400"
                  >
                    <ExternalLink size={12} />
                    {ig.handle}
                  </a>
                ) : (
                  <span className="text-xs text-slate-400">No Instagram URL</span>
                )}

                <div className="flex flex-wrap gap-1">
                  {(["youtube", "facebook"] as const)
                    .filter((network) => row[network])
                    .map((network) => (
                      <a
                        key={network}
                        href={row[network]}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] font-bold capitalize text-slate-600 transition hover:border-violet-300 hover:text-violet-600 dark:border-slate-700 dark:text-slate-300"
                      >
                        {network}
                      </a>
                    ))}
                </div>
              </div>
            </td>

            {/* Profile signals & request date */}
            <td className="px-4 py-3.5">
              <div className="flex flex-col items-start gap-1">
                <RiskBadge score={row.risk_score} />
                <span className="text-xs text-slate-400">
                  {formatFollowersShort(row.followers)} followers · {row.completion_percentage}% complete
                </span>
                {!row.email_verified && <AdminBadge tone="amber">Email unconfirmed</AdminBadge>}
                {row.verification_submitted_at ? (
                  <span className="text-[11px] text-slate-400">
                    Submitted {new Date(row.verification_submitted_at).toLocaleDateString()}
                  </span>
                ) : (
                  <span className="text-[11px] text-slate-400">
                    Joined {new Date(row.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </td>

            {/* Status */}
            <td className="px-4 py-3.5">
              <div className="flex flex-col items-start gap-1">
                <AdminBadge tone={statusTone(row.verification_status)}>
                  {row.verification_status}
                </AdminBadge>
                <span className="text-[11px] text-slate-400">{row.account_status}</span>
                {row.verification_rejection_reason && (
                  <span
                    className="max-w-[180px] truncate text-[11px] text-rose-500 italic"
                    title={row.verification_rejection_reason}
                  >
                    {row.verification_rejection_reason}
                  </span>
                )}
              </div>
            </td>

            {/* Actions */}
            <td className="px-4 py-3.5">
              {row.verification_status === "Pending" ? (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onDecide({ profile: row, decision: "approved" })}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-emerald-500 disabled:opacity-60"
                  >
                    <CheckCircle2 size={13} /> Approve
                  </button>
                  <button
                    onClick={() => onDecide({ profile: row, decision: "rejected" })}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-2 text-xs font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:hover:bg-rose-950/40"
                  >
                    <XCircle size={13} /> Reject
                  </button>
                </div>
              ) : row.verification_status === "Approved" ? (
                <div className="flex flex-col items-start gap-1">
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck size={14} /> Verified Badge
                  </span>
                  <a
                    href={`/owner/users/${row.user_id}`}
                    className="text-xs font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
                  >
                    View account →
                  </a>
                </div>
              ) : (
                <div className="flex flex-col items-start gap-1">
                  <button
                    onClick={() => onDecide({ profile: row, decision: "approved" })}
                    disabled={busy}
                    className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600 hover:underline disabled:opacity-60"
                  >
                    <CheckCircle2 size={12} /> Re-approve
                  </button>
                  <a
                    href={`/owner/users/${row.user_id}`}
                    className="text-xs font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
                  >
                    View account →
                  </a>
                </div>
              )}
            </td>
          </tr>
        );
      })}
    </AdminTable>
  );
}
