"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, LoaderCircle, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { adminApi, fetchMe, getAdminApiError, ownerLogin } from "@/services/admin-api";
import { useAuth } from "@/context/auth-context";

const loginSchema = z.object({
  username: z.string().min(1, "Enter your username."),
  password: z.string().min(1, "Enter your password."),
});
type LoginValues = z.infer<typeof loginSchema>;

/**
 * Private owner sign-in. There is deliberately NO admin signup: the owner
 * account is provisioned server-side via `python manage.py create_owner`.
 * The session is only kept when the server confirms the owner role.
 */
export default function OwnerLoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [denied, setDenied] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (values: LoginValues) => {
    setDenied(false);
    setLoginError(null);
    try {
      // Trim: e.g. pasted emails often carry a trailing space that would 401.
      const tokens = await ownerLogin(values.username.trim(), values.password);
      // Persist the token so the identity check can run, then verify the
      // role against SERVER state (never the login response alone).
      window.localStorage.setItem("influencehub_access", tokens.access);
      window.localStorage.setItem("influencehub_refresh", tokens.refresh || "");
      try {
        const me = await fetchMe();
        if (me.role !== "owner") {
          auth.signOut();
          setDenied(true);
          return;
        }
        auth.signIn(tokens, "owner");
        try {
          await adminApi.recordLoginAudit();
        } catch {
          // Audit recording must never block a valid sign-in.
        }
        toast.success("Welcome back, owner.");
        router.push("/owner");
      } catch (error) {
        auth.signOut();
        setDenied(true);
        const msg = getAdminApiError(error);
        setLoginError(msg);
        toast.error(msg);
      }
    } catch (error) {
      const msg = getAdminApiError(error);
      setLoginError(msg);
      toast.error(msg);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-5 dark:bg-[#090d19]">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 text-sm font-black text-white">
              ih
            </span>
            <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
              influence<span className="text-violet-600">hub</span>
            </span>
          </Link>
          <ThemeToggle />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs font-bold uppercase tracking-[.18em] text-violet-600">Private access</p>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Owner panel sign in
          </h1>
          <p className="mt-1.5 text-sm text-slate-500">
            Restricted to the platform owner account. Activity on this panel is audited.
          </p>

          {denied && (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300">
              <ShieldAlert size={18} className="mt-0.5 shrink-0" />
              You do not have permission to access the owner panel.
            </div>
          )}

          {loginError && !denied && (
            <div role="alert" className="mt-5 flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-400">
              <span className="mt-0.5 shrink-0">✕</span>
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={form.handleSubmit(onSubmit)} className="mt-6 space-y-5">
            <label className="block">
              <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">Email or username</span>
              <input
                suppressHydrationWarning
                {...form.register("username")}
                autoComplete="username"
                placeholder="prasadhm064@gmail.com"
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
              />
              {form.formState.errors.username && (
                <span className="mt-1.5 block text-xs font-medium text-rose-600">
                  {form.formState.errors.username.message}
                </span>
              )}
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">Password</span>
              <input
                suppressHydrationWarning
                type="password"
                {...form.register("password")}
                autoComplete="current-password"
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
              />
              {form.formState.errors.password && (
                <span className="mt-1.5 block text-xs font-medium text-rose-600">
                  {form.formState.errors.password.message}
                </span>
              )}
            </label>
            <button
              suppressHydrationWarning
              disabled={form.formState.isSubmitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {form.formState.isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
              Sign in securely <ArrowRight size={16} />
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs leading-5 text-slate-400">
          This page is not linked anywhere on the public site.
          <br />
          Owner accounts are provisioned by the platform operator only.
        </p>
      </div>
    </div>
  );
}
