"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Bell, BriefcaseBusiness, LayoutDashboard, LogOut, MessageCircle, Search, UserRound, X } from "lucide-react";
import type { UserRole } from "@/types";
import { useAuth } from "@/context/auth-context";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { LoadingState } from "@/components/ui/state";
import { cn } from "@/lib/utils";

const navigation = {
  business: [
    { href: "/business/dashboard", label: "Overview", icon: LayoutDashboard },
    { href: "/business/influencers", label: "Discover creators", icon: Search },
    { href: "/business/messages", label: "Messages", icon: MessageCircle },
    { href: "/business/notifications", label: "Notifications", icon: Bell },
    { href: "/business/profile", label: "Company profile", icon: BriefcaseBusiness },
  ],
  influencer: [
    { href: "/influencer/dashboard", label: "Campaigns", icon: LayoutDashboard },
    { href: "/influencer/messages", label: "Messages", icon: MessageCircle },
    { href: "/influencer/notifications", label: "Notifications", icon: Bell },
    { href: "/influencer/profile", label: "Creator profile", icon: UserRound },
  ],
};

export function PortalShell({ role, title, subtitle, children }: { role: UserRole; title: string; subtitle: string; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = useAuth();
  const isAllowed = auth.role === role;

  if (!auth.isReady) return <LoadingState label="Restoring your session…" />;
  if (!isAllowed) {
    if (auth.role) {
      router.replace(auth.role === "owner" ? "/owner" : `/${auth.role}/dashboard`);
    } else {
      router.replace(`/${role}/login`);
    }
    return <LoadingState label="Taking you to your workspace…" />;
  }

  const exit = () => { auth.signOut(); router.push("/"); };
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#090d19]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950 lg:flex">
        <Link href={`/${role}/dashboard`} className="flex items-center gap-2.5 px-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 text-sm font-black text-white">ih</span>
          <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">influence<span className="text-violet-600">hub</span></span>
        </Link>
        <p className="mt-10 px-2 text-[11px] font-bold uppercase tracking-[.17em] text-slate-400">{role} workspace</p>
        <nav className="mt-3 space-y-1">
          {navigation[role].map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition", pathname === href ? "bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900")}>
              <Icon size={18} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-slate-100 pt-4 dark:border-slate-800">
          <button onClick={exit} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-rose-50 hover:text-rose-600 dark:text-slate-300 dark:hover:bg-rose-950/30">
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-5 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90 sm:px-8">
          <Link href={`/${role}/dashboard`} className="font-extrabold text-slate-900 dark:text-white lg:hidden">
            influence<span className="text-violet-600">hub</span>
          </Link>
          <div className="hidden lg:block" />
          <div className="flex items-center gap-2">
            <NotificationBell role={role} />
            <ThemeToggle />
            <button onClick={exit} className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-600 lg:hidden" aria-label="Sign out">
              <X size={18} />
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
          <div className="mb-8">
            <p className="text-sm font-medium text-violet-600">{role === "business" ? "Business portal" : "Creator portal"}</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{title}</h1>
            <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
