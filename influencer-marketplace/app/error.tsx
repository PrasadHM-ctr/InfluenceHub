"use client";

import { useEffect } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-6 dark:bg-[#090d19]"><section className="max-w-md text-center"><TriangleAlert className="mx-auto text-amber-500" size={42} /><p className="mt-6 text-sm font-bold uppercase tracking-[.2em] text-amber-600">Something went wrong</p><h1 className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">Please try again.</h1><p className="mt-3 text-slate-500">We could not complete that request. Your data has not been changed.</p><button onClick={reset} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-violet-500"><RefreshCw size={16} />Try again</button></section></main>;
}
