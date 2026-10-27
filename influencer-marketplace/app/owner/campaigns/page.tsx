"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Ban, Eye, X } from "lucide-react";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, statusTone } from "@/components/admin/admin-ui";
import {
  AdminSearchInput,
  AdminSelect,
  AdminTable,
  TablePagination,
  ConfirmDialog,
} from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi, getAdminApiError } from "@/services/admin-api";
import type { AdminCampaignDetail, AdminCampaignRow } from "@/types/admin";
import type { CampaignStatus } from "@/types";
import { formatDate, formatMoney } from "@/lib/utils";

const PAGE_SIZE = 20;
const STATUSES: ("" | CampaignStatus)[] = ["", "Pending", "Accepted", "Rejected", "Completed", "Cancelled"];

export default function OwnerCampaignsPage() {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<number | null>(null);
  const [confirmCancel, setConfirmCancel] = useState<AdminCampaignDetail | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const campaigns = useQuery({
    queryKey: ["owner-campaigns", { search, status, page }],
    queryFn: () => adminApi.getCampaigns({ search, status, page }),
    placeholderData: keepPreviousData,
  });

  // Deep-link support (?open=ID) arriving from user detail pages.
  useEffect(() => {
    if (openId) return;
    const target = new URLSearchParams(window.location.search).get("open");
    if (target) setOpenId(Number(target));
  }, [openId]);

  const cancelCampaign = useMutation({
    mutationFn: (id: number) => adminApi.cancelCampaign(id),
    onSuccess: (result) => {
      toast.success(result.detail);
      setConfirmCancel(null);
      queryClient.invalidateQueries({ queryKey: ["owner-campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["owner-campaign", openId] });
    },
    onError: (error) => toast.error(getAdminApiError(error)),
  });

  const rows: AdminCampaignRow[] = campaigns.data?.results ?? [];
  const detail = useQuery({
    queryKey: ["owner-campaign", openId],
    queryFn: () => adminApi.getCampaign(openId as number),
    enabled: openId !== null,
  });

  return (
    <AdminShell
      active="campaigns"
      title="Campaign oversight"
      subtitle="Inspect any campaign exchange. Admin changes always require explicit confirmation."
    >
      <div className="mb-5 grid gap-3 sm:grid-cols-[1fr_220px]">
        <div>
          <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-400">Search</span>
          <AdminSearchInput
            value={searchInput}
            placeholder="Search title, business or influencer…"
            onChange={(value) => {
              setSearchInput(value);
              setPage(1);
            }}
          />
        </div>
        <AdminSelect
          label="Status filter"
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          options={STATUSES.map((value) => ({ value, label: value || "All statuses" }))}
        />
      </div>

      {campaigns.isLoading ? (
        <LoadingState label="Loading campaigns…" />
      ) : campaigns.isError ? (
        <AdminErrorNote error={campaigns.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="No campaigns found" description="No campaign requests match the current filters." />
      ) : (
        <>
          <AdminTable headers={["#", "Title", "Business", "Influencer", "Budget", "Status", "Created", ""]}>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-4 py-3.5 font-mono text-xs text-slate-400">#{row.id}</td>
                <td className="px-4 py-3.5 font-bold text-slate-900 dark:text-white">{row.title}</td>
                <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{row.business}</td>
                <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{row.influencer}</td>
                <td className="whitespace-nowrap px-4 py-3.5 font-semibold text-slate-900 dark:text-white">
                  {formatMoney(row.budget)}
                </td>
                <td className="px-4 py-3.5">
                  <AdminBadge tone={statusTone(row.status)}>{row.status}</AdminBadge>
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">{formatDate(row.created_at)}</td>
                <td className="px-4 py-3.5">
                  <button
                    onClick={() => setOpenId(row.id)}
                    className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:border-slate-700 dark:hover:bg-slate-900 dark:hover:text-white"
                    title="Inspect campaign"
                  >
                    <Eye size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </AdminTable>

          <TablePagination page={page} count={campaigns.data?.count ?? 0} pageSize={PAGE_SIZE} onPage={setPage} />
        </>
      )}

      {/* Detail drawer */}
      {openId !== null && (
        <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true">
          <button aria-label="Close details" className="absolute inset-0 bg-slate-950/50" onClick={() => setOpenId(null)} />
          <aside className="relative h-full w-full max-w-xl overflow-y-auto border-l border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-950 sm:p-8">
            <button
              onClick={() => setOpenId(null)}
              className="absolute right-5 top-5 grid h-8 w-8 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900"
              aria-label="Close panel"
            >
              <X size={16} />
            </button>
            {detail.isLoading ? (
              <LoadingState label="Loading campaign…" />
            ) : detail.isError || !detail.data ? (
              <AdminErrorNote error={detail.error ?? "Campaign unavailable."} />
            ) : (
              <CampaignDetailBody
                detail={detail.data}
                onCancelClick={() => setConfirmCancel(detail.data)}
                busy={cancelCampaign.isPending}
              />
            )}
          </aside>
        </div>
      )}

      <ConfirmDialog
        open={confirmCancel !== null}
        busy={cancelCampaign.isPending}
        title="Force-cancel this campaign?"
        message={`Are you sure you want to permanently cancel "${confirmCancel?.title ?? ""}"? Both participants will be notified and the campaign cannot be reopened.`}
        confirmLabel="Cancel this campaign"
        onCancel={() => setConfirmCancel(null)}
        onConfirm={() => confirmCancel && cancelCampaign.mutate(confirmCancel.id)}
      />
    </AdminShell>
  );
}

function CampaignDetailBody({
  detail,
  onCancelClick,
  busy,
}: {
  detail: AdminCampaignDetail;
  onCancelClick: () => void;
  busy: boolean;
}) {
  return (
    <div>
      <p className="font-mono text-xs text-slate-400">Campaign #{detail.id}</p>
      <h2 className="mt-1 pr-8 text-xl font-extrabold text-slate-900 dark:text-white">{detail.title}</h2>
      <div className="mt-2 flex items-center gap-2">
        <AdminBadge tone={statusTone(detail.status)}>{detail.status}</AdminBadge>
        <span className="text-sm font-bold text-slate-900 dark:text-white">{formatMoney(detail.budget)}</span>
      </div>

      <p className="mt-5 whitespace-pre-line rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:bg-slate-900 dark:text-slate-300">
        {detail.message}
      </p>

      {detail.attachment_url && (
        <a
          href={detail.attachment_url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
        >
          View attached brief <Eye size={13} />
        </a>
      )}

      <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">Business</dt>
          <dd className="mt-1 font-semibold text-slate-900 dark:text-white">
            {detail.business_detail.company_name}
            <span className="block text-xs font-normal text-slate-500">{detail.business_detail.email}</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">Influencer</dt>
          <dd className="mt-1 font-semibold text-slate-900 dark:text-white">
            {detail.influencer_detail.full_name}
            <span className="block text-xs font-normal text-slate-500">{detail.influencer_detail.email}</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">Created</dt>
          <dd className="mt-1 text-slate-600 dark:text-slate-300">{formatDate(detail.created_at)}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">Last updated</dt>
          <dd className="mt-1 text-slate-600 dark:text-slate-300">{formatDate(detail.updated_at)}</dd>
        </div>
      </dl>

      {detail.status !== "Cancelled" && (
        <button
          onClick={onCancelClick}
          disabled={busy}
          className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-rose-200 px-4 py-3 text-sm font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:hover:bg-rose-950/40"
        >
          <Ban size={15} /> Force-cancel campaign (requires confirmation)
        </button>
      )}
    </div>
  );
}