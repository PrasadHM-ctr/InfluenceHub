"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Building2, ImagePlus, LoaderCircle, Save } from "lucide-react";
import { toast } from "sonner";
import type { BusinessProfile } from "@/types";
import { useAuth } from "@/context/auth-context";
import { PortalShell } from "@/components/layout/portal-shell";
import { api, getApiError } from "@/services/api";
import { ErrorState, LoadingState } from "@/components/ui/state";

const schema = z.object({ company_name: z.string().min(2, "Enter your company name."), industry: z.string().min(2, "Enter your industry."), website: z.string().url("Enter a valid URL.").or(z.literal("")), description: z.string().optional(), phone: z.string().min(5, "Enter a phone number."), city: z.string().min(2, "Enter a city."), state: z.string().min(2, "Enter a state.") });
type ProfileValues = z.infer<typeof schema>;

function Field({ label, error, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) { return <label className="block"><span className="mb-1.5 block text-sm font-bold">{label}</span><input {...props} className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-violet-950" />{error && <span className="mt-1 block text-xs text-rose-600">{error}</span>}</label>; }

function LogoCard({ profile }: { profile: BusinessProfile }) {
  const client = useQueryClient();
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("logo", file);
      return api.updateBusinessProfile(form);
    },
    onSuccess: () => { toast.success("Business logo updated."); client.invalidateQueries({ queryKey: ["business-profile"] }); },
    onError: (error) => toast.error(getApiError(error)),
  });

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <h2 className="font-extrabold text-slate-900 dark:text-white">Business logo</h2>
      <p className="mt-1 text-sm text-slate-500">JPG, PNG or WEBP up to 5 MB.</p>
      <div className="mt-4 flex items-center gap-4">
        <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-2xl bg-violet-100 text-violet-600 dark:bg-violet-950/40">
          {profile.logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={profile.logo} alt="Logo" className="h-full w-full object-cover" />
          ) : (
            <Building2 size={28} />
          )}
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 transition hover:border-violet-300 hover:text-violet-600 dark:border-slate-700 dark:text-slate-300">
          {upload.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <ImagePlus size={16} />}
          Upload logo
          <input
            type="file"
            accept=".jpg,.jpeg,.png,.webp"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload.mutate(file);
              event.target.value = "";
            }}
          />
        </label>
      </div>
    </section>
  );
}

function ProfileForm({ profile }: { profile: BusinessProfile }) {
  const client = useQueryClient();
  const form = useForm<ProfileValues>({ resolver: zodResolver(schema), defaultValues: profile });
  const save = useMutation({ mutationFn: (values: ProfileValues) => api.updateBusinessProfile(values), onSuccess: () => { toast.success("Business profile saved."); client.invalidateQueries({ queryKey: ["business-profile"] }); }, onError: (error) => toast.error(getApiError(error)) });

  const completion = profile.completion_percentage ?? 0;
  const missing = profile.missing_fields ?? [];

  return (
    <>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center justify-between gap-4">
          <div><h2 className="font-extrabold text-slate-900 dark:text-white">{completion}% complete</h2><p className="mt-1 text-sm text-slate-500">{missing.length ? `Missing: ${missing.join(", ")}` : "Your brand profile is complete."}</p></div>
          <span className={`text-2xl font-extrabold ${completion >= 80 ? "text-emerald-600" : completion >= 50 ? "text-amber-500" : "text-rose-500"}`}>{completion}%</span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all" style={{ width: `${completion}%` }} /></div>
      </section>

      <LogoCard profile={profile} />

      <form onSubmit={form.handleSubmit((values) => save.mutate(values))} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="grid gap-5 sm:grid-cols-2"><Field label="Company name" {...form.register("company_name")} error={form.formState.errors.company_name?.message} /><Field label="Industry" {...form.register("industry")} error={form.formState.errors.industry?.message} /><Field label="Phone" type="tel" {...form.register("phone")} error={form.formState.errors.phone?.message} /><Field label="Website" type="url" placeholder="https://example.com" {...form.register("website")} error={form.formState.errors.website?.message} /><Field label="City" {...form.register("city")} error={form.formState.errors.city?.message} /><Field label="State" {...form.register("state")} error={form.formState.errors.state?.message} /></div><label className="mt-5 block"><span className="mb-1.5 block text-sm font-bold">Company description</span><textarea {...form.register("description")} placeholder="Tell creators about your company and the partnerships you want to build." className="min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-violet-950" /></label><div className="mt-6 flex justify-end"><button disabled={save.isPending} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-violet-500 disabled:opacity-60">{save.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Save size={16} />}Save changes</button></div></form>
    </>
  );
}

export default function BusinessProfilePage() {
  const auth = useAuth();
  const profile = useQuery({
    queryKey: ["business-profile"],
    queryFn: api.getBusinessProfile,
    enabled: auth.isReady && auth.role === "business",
  });
  return <PortalShell role="business" title="Company profile" subtitle="Keep the details creators need to understand your brand and campaign opportunities.">{profile.isLoading ? <LoadingState label="Loading company profile…" /> : profile.error || !profile.data ? <ErrorState message={profile.error ? getApiError(profile.error) : "Your business profile could not be loaded."} /> : <div className="space-y-6"><ProfileForm profile={profile.data} /></div>}</PortalShell>;
}