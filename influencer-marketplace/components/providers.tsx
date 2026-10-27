"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/auth-context";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }));
  return <ThemeProvider attribute="class" defaultTheme="light" enableSystem><QueryClientProvider client={queryClient}><AuthProvider>{children}<Toaster richColors position="top-right" /></AuthProvider></QueryClientProvider></ThemeProvider>;
}
