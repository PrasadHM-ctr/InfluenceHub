"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, BadgeCheck, LoaderCircle, MailCheck } from "lucide-react";
import { toast } from "sonner";
import { api, getApiError } from "@/services/api";

function VerifyEmailInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [verified, setVerified] = useState(false);
  // The signup form passes the account role so verified users land on the
  // correct sign-in page (influencers must not be sent to /business/login).
  const [loginPath, setLoginPath] = useState("/business/login");

  useEffect(() => {
    setEmail(params.get("email") ?? params.get("username") ?? "");
    setLoginPath(params.get("role") === "influencer" ? "/influencer/login" : "/business/login");
  }, [params]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email || code.length !== 6) {
      toast.error("Enter your email and the 6-digit code.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.verifyEmail({ email, code });
      toast.success(result.message);
      setVerified(true);
      setTimeout(() => router.push(loginPath), 1200);
    } catch (error) {
      toast.error(getApiError(error));
    } finally {
      setSubmitting(false);
    }
  };

  const resend = async () => {
    if (!email) {
      toast.error("Enter your account email first.");
      return;
    }
    setResending(true);
    try {
      const result = await api.resendVerification(email);
      // Reflect the backend's real delivery result — never claim success
      // when the email service rejected the send.
      if (result.emailed === false) {
        toast.error("Unable to send verification email. Please try again.");
      } else {
        toast.success(result.message || "Verification code sent to your email.");
      }
    } catch (error) {
      toast.error(getApiError(error));
    } finally {
      setResending(false);
    }
  };

  return (
    <main className="grid min-h-dvh place-items-center bg-slate-50 px-4 py-12 dark:bg-slate-950">
      <div className="w-full max-w-md">
        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-violet-600 dark:bg-violet-950 dark:text-violet-300">
            {verified ? <BadgeCheck size={24} /> : <MailCheck size={24} />}
          </span>
          <h1 className="mt-5 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {verified ? "Email verified" : "Verify your email"}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            {verified
              ? "Your account is active. Redirecting you to sign in…"
              : "We emailed a 6-digit code to your inbox. Click \"Resend code\" if it hasn't arrived."}
          </p>

          {!verified && (
            <form onSubmit={submit} className="mt-6 space-y-5">
              <label className="block">
                <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">Account email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">Verification code</span>
                <input
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-center text-lg font-extrabold tracking-[.5em] outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
                />
              </label>
              <button
                disabled={submitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting && <LoaderCircle size={16} className="animate-spin" />}
                Verify email <ArrowRight size={16} />
              </button>
              <button
                type="button"
                onClick={resend}
                disabled={resending}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-600 transition hover:border-violet-300 hover:text-violet-600 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300"
              >
                {resending && <LoaderCircle size={16} className="animate-spin" />}
                Resend code
              </button>
            </form>
          )}

          <p className="mt-6 border-t border-slate-100 pt-5 text-center text-sm text-slate-500 dark:border-slate-800">
            Already verified?{" "}
            <Link href={loginPath} className="font-bold text-violet-600 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<main className="grid min-h-dvh place-items-center bg-slate-50 dark:bg-slate-950"><LoaderCircle className="animate-spin text-violet-500" /></main>}>
      <VerifyEmailInner />
    </Suspense>
  );
}