"use client";

import Link from "next/link";
import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, ChevronLeft, ChevronRight, MapPin, RotateCcw, Search } from "lucide-react";
import { PortalShell } from "@/components/layout/portal-shell";
import { api, getApiError } from "@/services/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";
import { formatFollowers } from "@/lib/utils";
import type { InfluencerFilters } from "@/types";

const CATEGORIES = ["all", "Fashion", "Beauty", "Fitness", "Food", "Travel", "Technology", "Gaming", "Lifestyle", "Education", "Music", "Comedy"];
const LANGUAGES = ["all", "English", "Hindi", "Tamil", "Telugu", "Kannada", "Malayalam", "Marathi", "Bengali", "Gujarati", "Punjabi"];

export default function BusinessInfluencersPage() {
  const [filters, setFilters] = useState<InfluencerFilters>({});
  const [page, setPage] = useState(1);
  const [term, setTerm] = useState("");

  const query = useQuery({
    queryKey: ["influencers", { ...filters, page }],
    queryFn: () => api.getInfluencers({ ...filters, page }),
    placeholderData: keepPreviousData,
  });

  const creators = query.data?.results ?? [];
  const totalCount = query.data?.count ?? 0;
  const totalPages = Math.max(Math.ceil(totalCount / 12), 1);

  const update = (patch: Partial<InfluencerFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  const reset = () => {
    setFilters({});
    setTerm("");
    setPage(1);
  };

  return <PortalShell role="business" title="Discover creators" subtitle="Find creators that make sense for your brief, audience, and campaign goal.">{query.isLoading ? <LoadingState label="Loading creators…" /> : query.error ? <ErrorState message={getApiError(query.error)} /> : <>
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <form onSubmit={(event) => { event.preventDefault(); update({ search: term }); }} className="grid gap-3 md:grid-cols-[1fr_180px_160px]">
        <label className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Search by name, category, or location" className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-violet-950" />
        </label>
        <select value={filters.category ?? "all"} onChange={(event) => update({ category: event.target.value })} className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900">
          {CATEGORIES.map((item) => <option key={item} value={item}>{item === "all" ? "All categories" : item}</option>)}
        </select>
        <select value={filters.language ?? "all"} onChange={(event) => update({ language: event.target.value })} className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900">
          {LANGUAGES.map((item) => <option key={item} value={item}>{item === "all" ? "All languages" : item}</option>)}
        </select>
      </form>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
        <input value={filters.city ?? ""} onChange={(event) => update({ city: event.target.value })} placeholder="City" className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900" />
        <input value={filters.state ?? ""} onChange={(event) => update({ state: event.target.value })} placeholder="State" className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900" />
        <input type="number" min="0" value={filters.min_followers ?? ""} onChange={(event) => update({ min_followers: event.target.value })} placeholder="Min followers" className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900" />
        <input type="number" min="0" value={filters.max_followers ?? ""} onChange={(event) => update({ max_followers: event.target.value })} placeholder="Max followers" className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900" />
        <div className="flex items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-bold text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={Boolean(filters.verified_only)} onChange={(event) => update({ verified_only: event.target.checked })} className="h-4 w-4 rounded accent-violet-600" />
            Verified only
          </label>
          <button type="button" onClick={reset} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-bold text-slate-400 transition hover:text-violet-600"><RotateCcw size={13} />Reset</button>
        </div>
      </div>
    </section>

    <div className="mt-6 flex items-center justify-between">
      <p className="text-sm font-medium text-slate-500">{totalCount} {totalCount === 1 ? "creator" : "creators"} found</p>
      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage((current) => current - 1)} className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 transition hover:border-violet-300 disabled:opacity-40 dark:border-slate-700"><ChevronLeft size={16} /></button>
          <span className="text-sm font-bold">Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)} className="grid h-8 w-8 place-items-center rounded-lg border border-slate-200 transition hover:border-violet-300 disabled:opacity-40 dark:border-slate-700"><ChevronRight size={16} /></button>
        </div>
      )}
    </div>

    {creators.length ? (
      <section className={`mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3 ${query.isFetching ? "opacity-60 transition-opacity" : ""}`}>
        {creators.map((creator) => (
          <article key={creator.id} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-start gap-3">
              <span className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-sm font-extrabold text-white">
                {creator.profile_image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={creator.profile_image} alt="" className="h-full w-full object-cover" />
                ) : (
                  creator.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")
                )}
              </span>
              <div className="min-w-0">
                <h2 className="flex items-center gap-1 truncate font-extrabold text-slate-900 dark:text-white">{creator.full_name}{creator.is_verified && <BadgeCheck size={15} className="shrink-0 text-sky-500" />}</h2>
                <p className="mt-0.5 text-sm text-violet-600">{creator.category}</p>
                <p className="mt-2 flex items-center gap-1 text-xs text-slate-500"><MapPin size={13} />{creator.city}, {creator.state}</p>
              </div>
            </div>
            <div className="mt-5 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500">Audience</span>
              <span className="text-sm font-extrabold text-slate-900 dark:text-white">{formatFollowers(creator.followers)}</span>
            </div>
            <Link href={`/business/influencers/${creator.id}`} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 transition group-hover:border-violet-200 group-hover:bg-violet-50 group-hover:text-violet-700 dark:border-slate-700 dark:text-slate-200 dark:group-hover:bg-violet-950/40">View profile <ArrowRight size={16} /></Link>
          </article>
        ))}
      </section>
    ) : (
      <div className="mt-5"><EmptyState title="No creators match these filters" description="Try a broader category or search phrase to see more creator profiles." /></div>
    )}
  </>}</PortalShell>;
}