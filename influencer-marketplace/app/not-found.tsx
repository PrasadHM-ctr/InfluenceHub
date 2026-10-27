import Link from "next/link";
import { ArrowLeft, SearchX } from "lucide-react";

export default function NotFound() {
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-6 dark:bg-[#090d19]"><section className="max-w-md text-center"><SearchX className="mx-auto text-violet-600" size={42} /><p className="mt-6 text-sm font-bold uppercase tracking-[.2em] text-violet-600">404 error</p><h1 className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">This page is not here.</h1><p className="mt-3 text-slate-500">The page may have moved, or the link is no longer valid.</p><Link href="/" className="mt-7 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-violet-500"><ArrowLeft size={16} />Back home</Link></section></main>;
}
