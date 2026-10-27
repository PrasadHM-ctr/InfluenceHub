"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BadgeCheck,
  BarChart3,
  Building2,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  Settings,
  ShieldAlert,
  UsersRound,
  X,
} from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { LoadingState } from "@/components/ui/state";
import { AccessDeniedInline } from "@/components/admin/admin-ui";
import { adminApi, fetchMe, getAdminApiError } from "@/services/admin-api";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/owner", label: "Dashboard", icon: LayoutDashboard },
  { href: "/owner/users", label: "Users", icon: UsersRound },
  { href: "/owner/influencers", label: "Influencers", icon: BadgeCheck },
  { href: "/owner/businesses", label: "Businesses", icon: Building2 },
  { href: "/owner/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/owner/verifications", label: "Verifications", icon: ClipboardList },
  { href: "/owner/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/owner/activity", label: "Activity Logs", icon: Activity },
  { href: "/owner/settings", label: "Settings", icon: Settings },
];

function AdminAccessDenied() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-5 dark:bg-[#090d19]">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">
          <ShieldAlert size={28} />
        </span>
        <h1 className="mt-5 text-xl font-extrabold text-slate-900 dark:text-white">Access denied</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          You do not have permission to access the owner panel. If you believe this is a mistake, contact the
          platform operator.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-violet-500"
        >
          Back to InfluenceHub
        </Link>
      </div>
    </div>
  );
}

export function AdminShell({
  active,
  title,
  subtitle,
  children,
}: {
  active: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Server-truth authorization check on every mount. The stored role is a
  // convenience only; the backend enforces everything for real.
  const session = useQuery({
    queryKey: ["owner-session"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 60_000,
  });
  const attention = useQuery({
    queryKey: ["owner-attention"],
    queryFn: adminApi.getAttentionFeed,
    refetchInterval: 60_000,
    retry: false,
  });

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  if (!auth.isReady || session.isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#090d19]">
        <LoadingState label="Verifying your owner session…" />
      </div>
    );
  }

  // No token at all -> straight to the private login page.
  if (!session.data) return <AdminAccessDenied />;
  if (session.data.role !== "owner") return <AdminAccessDenied />;

  const unread = attention.data?.unread_count ?? 0;
  const exit = () => {
    auth.signOut();
    router.push("/");
  };

  const sidebar = (
    <>
      <Link href="/owner" className="flex items-center gap-2.5 px-2">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 text-sm font-black text-white">
          ih
        </span>
        <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
          influence<span className="text-violet-600">hub</span>
        </span>
      </Link>
      <p className="mt-10 px-2 text-[11px] font-bold uppercase tracking-[.17em] text-slate-400">Owner console</p>
      <nav className="mt-3 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition",
              pathname === href
                ? "bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900"
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto border-t border-slate-100 pt-4 dark:border-slate-800">
        <button
          onClick={exit}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-rose-50 hover:text-rose-600 dark:text-slate-300 dark:hover:bg-rose-950/30"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#090d19]" data-admin-page={active}>
      {/* Desktop fixed sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950 lg:flex">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-950/50"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-slate-200 bg-white p-5 shadow-xl dark:border-slate-800 dark:bg-slate-950">
            <button
              onClick={() => setDrawerOpen(false)}
              className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900"
              aria-label="Close menu"
            >
              <X size={16} />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-5 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90 sm:px-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDrawerOpen(true)}
              className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300 lg:hidden"
              aria-label="Open navigation"
            >
              <Menu size={18} />
            </button>
            <span className="hidden rounded-full bg-violet-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-violet-700 dark:bg-violet-950/50 dark:text-violet-300 sm:inline-flex">
              Owner panel · private
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/owner/activity"
              className="relative grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label={`Admin attention items${unread ? ` (${unread} unread)` : ""}`}
              title="Attention items"
            >
              <ClipboardList size={16} />
              {unread > 0 && (
                <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-black text-white">
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </Link>
            <ThemeToggle />
            <div className="hidden items-center gap-2 sm:flex" title={session.data?.email ?? ""}>
              <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-500 text-xs font-black text-white">
                {(session.data?.username ?? "O").slice(0, 2).toUpperCase()}
              </span>
              <span className="text-sm font-bold text-slate-900 dark:text-white">{session.data?.username}</span>
            </div>
            <button
              onClick={exit}
              className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/30 lg:hidden"
              aria-label="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
          <div className="mb-8">
            <p className="text-sm font-medium text-violet-600">Owner administration</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{title}</h1>
            <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}

export function AdminErrorNote({ error }: { error: unknown }) {
  return <AccessDeniedInline message={getAdminApiError(error)} />;
}