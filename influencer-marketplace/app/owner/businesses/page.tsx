"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AdminShell, AdminErrorNote } from "@/components/admin/admin-shell";
import { AdminBadge, statusTone } from "@/components/admin/admin-ui";
import { AdminSearchInput, AdminSelect, AdminTable, TablePagination } from "@/components/admin/admin-table";
import { EmptyState, LoadingState } from "@/components/ui/state";
import { adminApi } from "@/services/admin-api";
import type { AdminBusinessRow } from "@/types/admin";

const PAGE_SIZE = 20;

export default function OwnerBusinessesPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const businesses = useQuery({
    queryKey: ["owner-businesses", { search, status, page }],
    queryFn: () => adminApi.getBusinesses({ search, status, page }),
    placeholderData: keepPreviousData,
  });

  const rows: AdminBusinessRow[] = businesses.data?.results ?? [];

  return (
    <AdminShell
      active="businesses"
      title="Business management"
      subtitle="Every registered business with campaign volume and account standing."
    >
      <div className="mb-5 grid gap-3 sm:grid-cols-2">
        <div>
          <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-400">Search</span>
          <AdminSearchInput
            value={searchInput}
            placeholder="Search company name or email…"
            onChange={(value) => {
              setSearchInput(value);
              setPage(1);
            }}
          />
        </div>
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

      {businesses.isLoading ? (
        <LoadingState label="Loading businesses…" />
      ) : businesses.isError ? (
        <AdminErrorNote error={businesses.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="No businesses found" description="No companies match the current search and filters." />
      ) : (
        <>
          <BusinessTable rows={rows} />
          <TablePagination page={page} count={businesses.data?.count ?? 0} pageSize={PAGE_SIZE} onPage={setPage} />
        </>
      )}
    </AdminShell>
  );
}

function BusinessTable({ rows }: { rows: AdminBusinessRow[] }) {
  return (
    <AdminTable
      headers={["Business", "Location", "Email", "Campaigns", "Profile", "Status", "Joined"]}
    >
      {rows.map((row) => (
        <tr key={row.id}>
          <td className="px-4 py-3.5">
            <p className="font-bold text-slate-900 dark:text-white">{row.company_name}</p>
            <p className="text-xs text-slate-400">{row.industry}</p>
          </td>
          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
            {[row.city, row.state].filter(Boolean).join(", ") || "—"}
          </td>
          <td className="px-4 py-3.5">
            <p className="text-slate-600 dark:text-slate-300">{row.email}</p>
            {row.email_verified ? (
              <AdminBadge tone="green">Verified</AdminBadge>
            ) : (
              <AdminBadge tone="amber">Pending OTP</AdminBadge>
            )}
          </td>
          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
            {row.campaign_count} sent
            <p className="text-xs text-emerald-600 dark:text-emerald-400">{row.completed_campaigns} completed</p>
          </td>
          <td className="px-4 py-3.5 font-semibold text-slate-900 dark:text-white">{row.completion_percentage}%</td>
          <td className="px-4 py-3.5">
            <AdminBadge tone={statusTone(row.account_status)}>{row.account_status}</AdminBadge>
            <a
              href={`/owner/users/${row.user_id}`}
              className="mt-2 block text-xs font-bold text-violet-600 hover:text-violet-500 dark:text-violet-300"
            >
              View &amp; moderate →
            </a>
          </td>
          <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">
            {new Date(row.created_at).toLocaleDateString()}
          </td>
        </tr>
      ))}
    </AdminTable>
  );
}