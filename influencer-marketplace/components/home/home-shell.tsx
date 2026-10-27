"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Bell, LayoutDashboard, LogOut, Menu, MessageCircle, Search, UserRound, X } from "lucide-react";
import type { UserRole } from "@/types";
import { useAuth } from "@/context/auth-context";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { LoadingState } from "@/components/ui/state";
import { cn } from "@/lib/utils";

const navigation = {
  business: [
    { href: "/business/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/business/influencers", label: "Find influencers", icon: Search },
    { href: "/business/messages", label: "Messages", icon: MessageCircle },
    { href: "/business/notifications", label: "Notifications", icon: Bell },
    { href: "/business/profile", label: "Profile", icon: UserRound },
  ],
  influencer: [
    { href: "/influencer/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/influencer/messages", label: "Messages", icon: MessageCircle },
    { href: "/influencer/notifications", label: "Notifications", icon: Bell },
    { href: "/influencer/profile", label: "Profile", icon: UserRound },
  ],
};

export function HomeShell({ role, children }: { role: UserRole; children: ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!auth.isReady) return <LoadingState label="Restoring your workspace…" />;
  if (auth.role !== role) {
    if (auth.role) {
      router.replace(auth.role === "owner" ? "/owner" : `/${auth.role}/dashboard`);
    } else {
      router.replace(`/${role}/login`);
    }
    return <LoadingState label="Taking you to your workspace…" />;
  }

  const exit = () => { auth.signOut(); router.push("/"); };
  return <div className="min-h-screen bg-[#f8f8ff] text-slate-900 dark:bg-[#080b17] dark:text-white"><header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85"><div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8"><Link href={`/${role}/home`} className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 text-sm font-black text-white shadow-lg shadow-violet-500/20">ih</span><span className="text-lg font-extrabold tracking-tight">influence<span className="text-violet-600">hub</span></span></Link><nav className="hidden items-center gap-1 lg:flex">{navigation[role].map(({ href, label, icon: Icon }) => <Link key={label} href={href} className={cn("inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold transition", pathname === href ? "bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white")}><Icon size={16} />{label}</Link>)}</nav><div className="flex items-center gap-2"><ThemeToggle /><button onClick={exit} className="hidden items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold text-slate-600 transition hover:bg-rose-50 hover:text-rose-600 dark:text-slate-300 dark:hover:bg-rose-950/30 sm:inline-flex"><LogOut size={16} />Logout</button><button onClick={() => setMenuOpen((open) => !open)} className="grid h-9 w-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 lg:hidden dark:text-slate-300 dark:hover:bg-slate-900" aria-label="Toggle navigation">{menuOpen ? <X size={19} /> : <Menu size={19} />}</button></div></div>{menuOpen && <div className="border-t border-slate-100 bg-white p-3 lg:hidden dark:border-slate-800 dark:bg-slate-950"><nav className="mx-auto grid max-w-7xl gap-1">{navigation[role].map(({ href, label, icon: Icon }) => <Link key={label} onClick={() => setMenuOpen(false)} href={href} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-bold text-slate-600 hover:bg-violet-50 hover:text-violet-700 dark:text-slate-300 dark:hover:bg-violet-950/50"><Icon size={17} />{label}</Link>)}<button onClick={exit} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-bold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"><LogOut size={17} />Logout</button></nav></div>}</header><main className="mx-auto max-w-7xl px-5 py-7 sm:px-8 sm:py-10">{children}</main></div>;
}
