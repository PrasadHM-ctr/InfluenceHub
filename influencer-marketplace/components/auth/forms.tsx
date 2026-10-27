"use client";

import React from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { toast } from "sonner";
import { api, getApiError } from "@/services/api";
import { useAuth } from "@/context/auth-context";
import type { UserRole } from "@/types";

const signInSchema = z.object({ username: z.string().min(1, "Enter your username."), password: z.string().min(1, "Enter your password.") });
const baseSchema = z.object({ username: z.string().min(3, "Use at least 3 characters."), email: z.string().email("Enter a valid email address."), password: z.string().min(8, "Use at least 8 characters.") });
const businessSchema = baseSchema.extend({ company_name: z.string().min(2, "Enter your company name."), industry: z.string().min(2, "Enter an industry."), phone: z.string().min(5, "Enter a phone number."), city: z.string().min(2, "Enter a city."), state: z.string().min(2, "Enter a state."), website: z.string().url("Enter a valid URL.").or(z.literal("")), description: z.string().optional() });
const influencerSchema = baseSchema.extend({ full_name: z.string().min(2, "Enter your name."), category: z.string().min(2, "Enter a category."), language: z.string().min(2, "Enter a language."), followers: z.number().min(0, "Enter a valid follower count."), city: z.string().min(2, "Enter a city."), state: z.string().min(2, "Enter a state."), bio: z.string().optional(), instagram: z.string().url("Enter a valid URL.").or(z.literal("")), youtube: z.string().url("Enter a valid URL.").or(z.literal("")), facebook: z.string().url("Enter a valid URL.").or(z.literal("")) });

type SignInValues = z.infer<typeof signInSchema>;
type BusinessValues = z.infer<typeof businessSchema>;
type InfluencerValues = z.infer<typeof influencerSchema>;

function Field({ label, error, required, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; required?: boolean }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">
        {label}{required && <span className="text-rose-500"> *</span>}
      </span>
      <input
        suppressHydrationWarning
        {...props}
        className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
      />
      {error && <span className="mt-1.5 block text-xs font-medium text-rose-600">{error}</span>}
    </label>
  );
}

function TextArea({ label, error, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-bold text-slate-700 dark:text-slate-200">{label}</span>
      <textarea
        suppressHydrationWarning
        {...props}
        className="min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-950"
      />
      {error && <span className="mt-1.5 block text-xs font-medium text-rose-600">{error}</span>}
    </label>
  );
}

export function SignInForm({ role }: { role: UserRole }) {
  const router = useRouter();
  const { signIn } = useAuth();
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const form = useForm<SignInValues>({ resolver: zodResolver(signInSchema), defaultValues: { username: "", password: "" } });
  const onSubmit = async (values: SignInValues) => {
    setLoginError(null);
    try {
      const tokens = await api.login(values);
      if (tokens.role !== role) {
        const msg = tokens.role
          ? `This account is registered as a ${tokens.role}. Please use that sign-in page.`
          : "This account does not have a marketplace role.";
        setLoginError(msg);
        toast.error(msg);
        return;
      }
      signIn(tokens, tokens.role);
      toast.success("Signed in successfully.");
      if (tokens.role === "business") {
        router.push("/business/dashboard");
      } else if (tokens.role === "influencer") {
        router.push("/influencer/dashboard");
      } else if (tokens.role === "owner") {
        router.push("/owner");
      } else {
        router.push("/");
      }
    } catch (error) {
      const message = getApiError(error);
      setLoginError(message);
      toast.error(message, {
        description: /verif/i.test(message) ? "Need a new code?" : undefined,
        action: /verif/i.test(message)
          ? { label: "Verify email", onClick: () => router.push(`/verify-email?email=${encodeURIComponent(values.username)}&role=${role}`) }
          : undefined,
      });
    }
  };
  const alternate = role === "business" ? "influencer" : "business";
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      <Field label="Username" required autoComplete="username" placeholder="Your username" {...form.register("username")} error={form.formState.errors.username?.message} />
      <Field label="Password" required type="password" autoComplete="current-password" placeholder="Your password" {...form.register("password")} error={form.formState.errors.password?.message} />
      {loginError && (
        <div role="alert" className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-400">
          <span className="mt-0.5 shrink-0 text-rose-500">✕</span>
          <span>
            {loginError}
            {/verif/i.test(loginError) && (
              <button
                type="button"
                onClick={() => router.push(`/verify-email?email=${encodeURIComponent(form.getValues("username"))}&role=${role}`)}
                className="ml-2 font-bold underline underline-offset-2 hover:text-rose-900 dark:hover:text-rose-200"
              >
                Verify now →
              </button>
            )}
          </span>
        </div>
      )}
      <button
        suppressHydrationWarning
        disabled={form.formState.isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {form.formState.isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
        Sign in <ArrowRight size={16} />
      </button>
      <p className="text-center text-sm text-slate-500">
        New to InfluenceHub? <Link href={`/${role}/signup`} className="font-bold text-violet-600 hover:underline">Create an account</Link>
      </p>
      <p className="border-t border-slate-100 pt-5 text-center text-xs text-slate-400 dark:border-slate-800">
        Need the {alternate} workspace? <Link href={`/${alternate}/login`} className="font-bold text-slate-600 hover:text-violet-600 dark:text-slate-300">Sign in as a {alternate}</Link>
      </p>
    </form>
  );
}

export function BusinessRegistrationForm() {
  const router = useRouter();
  const form = useForm<BusinessValues>({ resolver: zodResolver(businessSchema), defaultValues: { username: "", email: "", password: "", company_name: "", industry: "", phone: "", city: "", state: "", website: "", description: "" } });
  const onSubmit = async (values: BusinessValues) => {
    try {
      const result = await api.registerBusiness(values);
      if (result.email_sent === false) {
        toast.warning("Account created, but verification email could not be sent. Please use Resend code on the next screen.");
      } else {
        toast.success("Account created! Verification code sent to your email.");
      }
      router.push(`/verify-email?email=${encodeURIComponent(values.email)}&role=business`);
    } catch (error) {
      toast.error(getApiError(error));
    }
  };
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Username" required {...form.register("username")} error={form.formState.errors.username?.message} />
        <Field label="Email" required type="email" {...form.register("email")} error={form.formState.errors.email?.message} />
        <Field label="Password" required type="password" autoComplete="new-password" {...form.register("password")} error={form.formState.errors.password?.message} />
        <Field label="Company name" required {...form.register("company_name")} error={form.formState.errors.company_name?.message} />
        <Field label="Industry" required placeholder="e.g. Beauty, technology" {...form.register("industry")} error={form.formState.errors.industry?.message} />
        <Field label="Phone" required type="tel" {...form.register("phone")} error={form.formState.errors.phone?.message} />
        <Field label="City" required {...form.register("city")} error={form.formState.errors.city?.message} />
        <Field label="State" required {...form.register("state")} error={form.formState.errors.state?.message} />
      </div>
      <Field label="Website" type="url" placeholder="https://example.com" {...form.register("website")} error={form.formState.errors.website?.message} />
      <TextArea label="About your business" placeholder="What kind of creator partnerships are you looking for?" {...form.register("description")} error={form.formState.errors.description?.message} />
      <button
        suppressHydrationWarning
        disabled={form.formState.isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {form.formState.isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
        Create business account <ArrowRight size={16} />
      </button>
      <p className="text-center text-sm text-slate-500">
        Already have an account? <Link href="/business/login" className="font-bold text-violet-600 hover:underline">Sign in</Link>
      </p>
    </form>
  );
}

export function InfluencerRegistrationForm() {
  const router = useRouter();
  const form = useForm<InfluencerValues>({ resolver: zodResolver(influencerSchema), defaultValues: { username: "", email: "", password: "", full_name: "", category: "", language: "", followers: 0, city: "", state: "", bio: "", instagram: "", youtube: "", facebook: "" } });
  const onSubmit = async (values: InfluencerValues) => {
    try {
      const result = await api.registerInfluencer(values);
      if (result.email_sent === false) {
        toast.warning("Account created, but verification email could not be sent. Please use Resend code on the next screen.");
      } else {
        toast.success("Account created! Verification code sent to your email.");
      }
      router.push(`/verify-email?email=${encodeURIComponent(values.email)}&role=influencer`);
    } catch (error) {
      toast.error(getApiError(error));
    }
  };
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Username" required {...form.register("username")} error={form.formState.errors.username?.message} />
        <Field label="Email" required type="email" {...form.register("email")} error={form.formState.errors.email?.message} />
        <Field label="Password" required type="password" autoComplete="new-password" {...form.register("password")} error={form.formState.errors.password?.message} />
        <Field label="Full name" required {...form.register("full_name")} error={form.formState.errors.full_name?.message} />
        <Field label="Category" required placeholder="e.g. Fitness, fashion" {...form.register("category")} error={form.formState.errors.category?.message} />
        <Field label="Primary language" required {...form.register("language")} error={form.formState.errors.language?.message} />
        <Field label="Follower count" required type="number" min="0" {...form.register("followers", { valueAsNumber: true })} error={form.formState.errors.followers?.message} />
        <Field label="City" required {...form.register("city")} error={form.formState.errors.city?.message} />
        <Field label="State" required {...form.register("state")} error={form.formState.errors.state?.message} />
      </div>
      <TextArea label="Bio" placeholder="Tell brands about your content and audience." {...form.register("bio")} error={form.formState.errors.bio?.message} />
      <div className="grid gap-5 sm:grid-cols-3">
        <Field label="Instagram URL" type="url" {...form.register("instagram")} error={form.formState.errors.instagram?.message} />
        <Field label="YouTube URL" type="url" {...form.register("youtube")} error={form.formState.errors.youtube?.message} />
        <Field label="Facebook URL" type="url" {...form.register("facebook")} error={form.formState.errors.facebook?.message} />
      </div>
      <button
        suppressHydrationWarning
        disabled={form.formState.isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-fuchsia-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-fuchsia-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {form.formState.isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
        Create creator account <ArrowRight size={16} />
      </button>
      <p className="text-center text-sm text-slate-500">
        Already have an account? <Link href="/influencer/login" className="font-bold text-fuchsia-600 hover:underline">Sign in</Link>
      </p>
    </form>
  );
}
