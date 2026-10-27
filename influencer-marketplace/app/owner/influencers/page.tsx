"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, RiskBadge, statusTone } from "@/components/admin/admin-ui";
import { AdminSearchInput, AdminSelect, AdminTable, TablePagination } from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import type { AdminInfluencerRow } from "@/types/admin";
import { formatFollowers } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function OwnerInfluencersPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [verification, setVerification] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const influencers = useQuery({
    queryKey: ["owner-influencers", { search, verification, status, page }],
    queryFn: () => adminApi.getInfluencers({ search, verification, status, page }),
    placeholderData: keepPreviousData,
  });

  const rows: AdminInfluencerRow[] = influencers.data?.results ?? [];

  return (
    <AdminShell
      active="influencers"
      title="Influencer management"
      subtitle="Creator directory with review-priority signals. A high risk score means look closer - never proof of fraud."
    >
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <div className="sm:col-span-1">
          <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-400">Search</span>
          <AdminSearchInput
            value={searchInput}
            placeholder="Search creator name or email…"
            onChange={(value) => {
              setSearchInput(value);
              setPage(1);
            }}
          />
        </div>
        <AdminSelect
          label="Verification"
          value={verification}
          onChange={(value) => {
            setVerification(value);
            setPage(1);
          }}
          options={[
            { value: "", label: "All statuses" },
            { value: "Pending", label: "Pending" },
            { value: "Approved", label: "Approved" },
            { value: "Rejected", label: "Rejected" },
          ]}
        />
        <AdminSelect
          label="Account status"
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          options={[
            { value: "", label: "All" },
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
        />
      </div>

      {influencers.isLoading ? (
        <LoadingState label="Loading influencers…" />
      ) : influencers.isError ? (
        <AdminErrorNote error={influencers.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="No influencers found" description="No creators match the current search and filters." />
      ) : (
        <>
          <InfluencerTable rows={rows} />
          <TablePagination page={page} count={influencers.data?.count ?? 0} pageSize={PAGE_SIZE} onPage={setPage} />
        </>
      )}
    </AdminShell>
  );
}

function InfluencerTable({ rows }: { rows: AdminInfluencerRow[] }) {
  return (
    <AdminTable headers={["Creator", "Category", "Followers", "Verified", "Campaigns", "Risk signal", "Status"]}>
      {rows.map((row) => (
        <tr key={row.id}>
          <td className="px-4 py-3.5">
            <p className="font-bold text-slate-900 dark:text-white">{row.full_name}</p>
            <p className="text-xs text-slate-500">{row.email}</p>
            <p className="mt-0.5 text-xs text-slate-400">
              {[row.city, row.state].filter(Boolean).join(", ")} · joined{" "}
              {new Date(row.created_at).toLocaleDateString()}
            </p>
          </td>
          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
            {row.category}
            <p className="text-xs text-slate-400">{row.language}</p>
          </td>
          <td className="px-4 py-3.5 font-semibold text-slate-900 dark:text-white">{formatFollowers(row.followers)}</td>
          <td className="px-4 py-3.5">
            <div className="flex flex-col items-start gap-1.5">
              <AdminBadge tone={statusTone(row.verification_status)}>{row.verification_status}</AdminBadge>
              {!row.email_verified && <AdminBadge tone="amber">Email unconfirmed</AdminBadge>}
            </div>
          </td>
          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
            {row.campaign_count} total
            <p className="text-xs text-emerald-600 dark:text-emerald-400">{row.completed_campaigns} completed</p>
          </td>
          <td className="px-4 py-3.5">
            <RiskBadge score={row.risk_score} />
            <p className="mt-1 max-w-52 text-xs leading-4 text-slate-400">
              {row.risk_signals.length === 0 ? "No negative signals." : row.risk_signals[0]}
              {row.risk_signals.length > 1 && ` +${row.risk_signals.length - 1} more`}
            </p>
          </td>
          <td className="px-4 py-3.5">
            <AdminBadge tone={statusTone(row.account_status)}>{row.account_status}</AdminBadge>
            <a
              href={`/owner/users/${row.user_id}`}
              className="mt-2 block text-xs font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
            >
              View &amp; moderate →
            </a>
          </td>
        </tr>
      ))}
    </AdminTable>
  );
}