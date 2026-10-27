"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { BadgeCheck, Check, Copy, ExternalLink, ImagePlus, LoaderCircle, RefreshCw, Save, ShieldAlert, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import type { Influencer } from "@/types";
import { useAuth } from "@/context/auth-context";
import { PortalShell } from "@/components/layout/portal-shell";
import { api, getApiError } from "@/services/api";
import { ErrorState, LoadingState } from "@/components/ui/state";

const schema = z.object({ full_name: z.string().min(2, "Enter your name."), bio: z.string().optional(), category: z.string().min(2, "Enter a category."), language: z.string().min(2, "Enter a language."), followers: z.number().min(0, "Enter a valid follower count."), instagram: z.string().url("Enter a valid URL.").or(z.literal("")), youtube: z.string().url("Enter a valid URL.").or(z.literal("")), facebook: z.string().url("Enter a valid URL.").or(z.literal("")), city: z.string().min(2, "Enter a city."), state: z.string().min(2, "Enter a state.") });
type ProfileValues = z.infer<typeof schema>;

function Field({ label, error, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) { return <label className="block"><span className="mb-1.5 block text-sm font-bold">{label}</span><input {...props} className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-fuchsia-500 focus:ring-4 focus:ring-fuchsia-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-fuchsia-950" />{error && <span className="mt-1 block text-xs text-rose-600">{error}</span>}</label>; }

function ProfileImageCard({ profile }: { profile: Influencer }) {
  const client = useQueryClient();
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("profile_image", file);
      return api.updateInfluencerProfile(form);
    },
    onSuccess: () => { toast.success("Profile image updated."); client.invalidateQueries({ queryKey: ["influencer-profile"] }); },
    onError: (error) => toast.error(getApiError(error)),
  });

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <h2 className="font-extrabold text-slate-900 dark:text-white">Profile photo</h2>
      <p className="mt-1 text-sm text-slate-500">JPG, PNG or WEBP up to 5 MB.</p>
      <div className="mt-4 flex items-center gap-4">
        <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-full bg-fuchsia-100 text-xl font-extrabold text-fuchsia-600 dark:bg-fuchsia-950/40">
          {profile.profile_image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={profile.profile_image} alt="Profile" className="h-full w-full object-cover" />
          ) : (
            profile.full_name.slice(0, 1).toUpperCase()
          )}
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 transition hover:border-fuchsia-300 hover:text-fuchsia-600 dark:border-slate-700 dark:text-slate-300">
          {upload.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <ImagePlus size={16} />}
          Upload photo
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

function VerificationCard({ profile }: { profile: Influencer }) {
  const client = useQueryClient();
  const [instagramUrl, setInstagramUrl] = useState(profile.instagram ?? "");
  const [copied, setCopied] = useState(false);

  const request = useMutation({
    mutationFn: (refresh?: boolean) => api.requestVerification(instagramUrl, refresh),
    onSuccess: (result) => {
      toast.success(result.message, { duration: 8000 });
      client.invalidateQueries({ queryKey: ["influencer-profile"] });
    },
    onError: (error) => toast.error(getApiError(error)),
  });

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success("Verification code copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy code to clipboard.");
    }
  };

  if (profile.is_verified) {
    return (
      <section className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-6 shadow-sm dark:border-emerald-900/60 dark:bg-emerald-950/20">
        <div className="flex items-center gap-2 font-extrabold text-emerald-800 dark:text-emerald-200">
          <BadgeCheck size={20} className="text-emerald-600 dark:text-emerald-400" />
          Verified Creator Account
        </div>
        <p className="mt-2 text-sm text-emerald-700 dark:text-emerald-300">
          Your Instagram ownership has been verified by the InfluenceHub team. The Verified badge is now visible on your public creator profile and helps brands trust your collaboration requests.
        </p>
        {profile.instagram && (
          <div className="mt-4 flex items-center gap-2">
            <a
              href={profile.instagram}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 hover:underline dark:text-emerald-300"
            >
              View verified Instagram profile <ExternalLink size={12} />
            </a>
          </div>
        )}
      </section>
    );
  }

  const code = profile.social_verification_code;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-extrabold text-slate-900 dark:text-white">
          <ShieldCheck size={20} className="text-fuchsia-600 dark:text-fuchsia-400" />
          Get the Verified Badge
        </div>
        {profile.verification_status === "Pending" ? (
          <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-950/40 dark:text-amber-300">
            Pending Review
          </span>
        ) : profile.verification_status === "Rejected" ? (
          <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-1 text-xs font-bold text-rose-700 ring-1 ring-inset ring-rose-600/20 dark:bg-rose-950/40 dark:text-rose-300">
            Review Rejected
          </span>
        ) : (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Not Verified
          </span>
        )}
      </div>

      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
        To protect businesses and authentic creators, we require proof of Instagram account ownership. Simply paste your unique code into your Instagram bio so our administrators can verify ownership.
      </p>

      {/* Code Card - persistently rendered when a code exists */}
      {code ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-violet-200 bg-violet-50/60 p-4 dark:border-violet-900/60 dark:bg-violet-950/20">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">
                  Your Instagram Bio Verification Code
                </span>
                <div className="mt-1 flex items-center gap-3">
                  <span className="font-mono text-2xl font-black tracking-wider text-violet-950 dark:text-violet-100">
                    {code}
                  </span>
                  <button
                    type="button"
                    onClick={() => copyCode(code)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-violet-500 active:scale-95"
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? "Copied!" : "Copy Code"}
                  </button>
                </div>
              </div>

              {profile.instagram && (
                <a
                  href={profile.instagram}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1.5 self-start rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-bold text-violet-700 transition hover:bg-violet-100 dark:border-violet-800 dark:bg-slate-900 dark:text-violet-300 dark:hover:bg-violet-950/50 sm:self-auto"
                >
                  Open Instagram Bio <ExternalLink size={13} />
                </a>
              )}
            </div>

            <ol className="mt-4 list-decimal space-y-1.5 border-t border-violet-200/60 pl-5 pt-3 text-xs text-violet-900 dark:border-violet-900/40 dark:text-violet-200">
              <li>
                Copy the code <strong>{code}</strong> above.
              </li>
              <li>
                Open Instagram, edit your profile, and paste <strong>{code}</strong> anywhere inside your bio.
              </li>
              <li>
                Wait for our review team to verify your account and grant your Verified badge.
              </li>
            </ol>
          </div>

          {profile.verification_status === "Rejected" && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
              <div className="flex items-center gap-1.5 font-bold">
                <ShieldAlert size={14} /> Rejection note from admin
              </div>
              <p className="mt-1">
                {profile.verification_rejection_reason || "The bio code could not be verified on the linked Instagram profile."}
              </p>
              <p className="mt-1 text-rose-600 dark:text-rose-400">
                Ensure your Instagram profile is public and contains the code above, then re-submit below.
              </p>
            </div>
          )}

          {profile.verification_status === "Pending" && (
            <div className="rounded-xl bg-amber-50 px-4 py-3 text-xs font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
              ⏳ Verification requested
              {profile.verification_submitted_at
                ? ` on ${new Date(profile.verification_submitted_at).toLocaleDateString()}`
                : ""}
              . Our admin team will inspect your bio and confirm ownership.
            </div>
          )}

          {/* Update Instagram URL or re-request code */}
          <div className="pt-2">
            <span className="mb-1.5 block text-xs font-bold text-slate-500">
              Update linked Instagram URL or refresh code:
            </span>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                value={instagramUrl}
                onChange={(event) => setInstagramUrl(event.target.value)}
                placeholder="https://instagram.com/yourhandle"
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-fuchsia-500 focus:ring-4 focus:ring-fuchsia-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-fuchsia-950"
              />
              <button
                type="button"
                onClick={() => request.mutate(false)}
                disabled={request.isPending || !instagramUrl}
                className="shrink-0 rounded-xl bg-fuchsia-600 px-4 py-2.5 text-sm font-extrabold text-white transition hover:bg-fuchsia-500 disabled:opacity-60"
              >
                {request.isPending ? <LoaderCircle size={16} className="animate-spin" /> : "Update Request"}
              </button>
              <button
                type="button"
                onClick={() => request.mutate(true)}
                disabled={request.isPending || !instagramUrl}
                title="Generate a brand new code"
                className="shrink-0 rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
              >
                <RefreshCw size={14} className="mr-1 inline" /> New code
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4">
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-500">
            <li>Submit your Instagram profile URL below.</li>
            <li>We generate a unique code — add it to your Instagram bio.</li>
            <li>Our team confirms ownership and grants the badge.</li>
          </ol>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={instagramUrl}
              onChange={(event) => setInstagramUrl(event.target.value)}
              placeholder="https://instagram.com/yourhandle"
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-fuchsia-500 focus:ring-4 focus:ring-fuchsia-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-fuchsia-950"
            />
            <button
              type="button"
              onClick={() => request.mutate(false)}
              disabled={request.isPending || !instagramUrl}
              className="shrink-0 rounded-xl bg-fuchsia-600 px-4 py-2.5 text-sm font-extrabold text-white transition hover:bg-fuchsia-500 disabled:opacity-60"
            >
              {request.isPending ? <LoaderCircle size={16} className="animate-spin" /> : "Request code"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function ProfileForm({ profile }: { profile: Influencer }) {
  const client = useQueryClient();
  const defaults: ProfileValues = { full_name: profile.full_name, bio: profile.bio ?? "", category: profile.category, language: profile.language ?? "", followers: profile.followers, instagram: profile.instagram ?? "", youtube: profile.youtube ?? "", facebook: profile.facebook ?? "", city: profile.city, state: profile.state };
  const form = useForm<ProfileValues>({ resolver: zodResolver(schema), defaultValues: defaults });
  const save = useMutation({ mutationFn: (values: ProfileValues) => api.updateInfluencerProfile(values), onSuccess: () => { toast.success("Creator profile saved."); client.invalidateQueries({ queryKey: ["influencer-profile"] }); }, onError: (error) => toast.error(getApiError(error)) });

  const completion = profile.completion_percentage ?? 0;
  const missing = profile.missing_fields ?? [];

  return (
    <>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center justify-between gap-4">
          <div><h2 className="font-extrabold text-slate-900 dark:text-white">{completion}% complete</h2><p className="mt-1 text-sm text-slate-500">{missing.length ? `Missing: ${missing.join(", ")}` : "Your profile has everything brands need."}</p></div>
          <span className={`text-2xl font-extrabold ${completion >= 80 ? "text-emerald-600" : completion >= 50 ? "text-amber-500" : "text-rose-500"}`}>{completion}%</span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-fuchsia-500 to-violet-500 transition-all" style={{ width: `${completion}%` }} /></div>
      </section>

      <ProfileImageCard profile={profile} />

      <form onSubmit={form.handleSubmit((values) => save.mutate(values))} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="grid gap-5 sm:grid-cols-2"><Field label="Full name" {...form.register("full_name")} error={form.formState.errors.full_name?.message} /><Field label="Content category" placeholder="e.g. Fashion, gaming" {...form.register("category")} error={form.formState.errors.category?.message} /><Field label="Primary language" {...form.register("language")} error={form.formState.errors.language?.message} /><Field label="Follower count" type="number" min="0" {...form.register("followers", { valueAsNumber: true })} error={form.formState.errors.followers?.message} /><Field label="City" {...form.register("city")} error={form.formState.errors.city?.message} /><Field label="State" {...form.register("state")} error={form.formState.errors.state?.message} /></div><label className="mt-5 block"><span className="mb-1.5 block text-sm font-bold">Bio</span><textarea {...form.register("bio")} placeholder="Describe your content, audience, and creative point of view." className="min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-fuchsia-500 focus:ring-4 focus:ring-fuchsia-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-fuchsia-950" /></label><div className="mt-5 grid gap-5 sm:grid-cols-3"><Field label="Instagram URL" type="url" {...form.register("instagram")} error={form.formState.errors.instagram?.message} /><Field label="YouTube URL" type="url" {...form.register("youtube")} error={form.formState.errors.youtube?.message} /><Field label="Facebook URL" type="url" {...form.register("facebook")} error={form.formState.errors.facebook?.message} /></div><div className="mt-6 flex justify-end"><button disabled={save.isPending} className="inline-flex items-center gap-2 rounded-xl bg-fuchsia-600 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-fuchsia-500 disabled:opacity-60">{save.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Save size={16} />}Save changes</button></div></form>

      <VerificationCard profile={profile} />
    </>
  );
}

export default function InfluencerProfilePage() {
  const auth = useAuth();
  const profile = useQuery({
    queryKey: ["influencer-profile"],
    queryFn: api.getInfluencerProfile,
    enabled: auth.isReady && auth.role === "influencer",
  });
  return <PortalShell role="influencer" title="Creator profile" subtitle="Keep your public details accurate so businesses can understand the work you do.">{profile.isLoading ? <LoadingState label="Loading creator profile…" /> : profile.error || !profile.data ? <ErrorState message={profile.error ? getApiError(profile.error) : "Your creator profile could not be loaded."} /> : <div className="space-y-6"><ProfileForm profile={profile.data} /></div>}</PortalShell>;
}