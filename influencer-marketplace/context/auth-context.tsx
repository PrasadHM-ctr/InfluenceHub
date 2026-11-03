"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { AccountRole, AuthTokens } from "@/types";
import { api } from "@/services/api";

interface AuthContextValue {
  role: AccountRole | null;
  isReady: boolean;
  signIn: (tokens: AuthTokens, role: AccountRole) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const ACCESS = "influencehub_access";
const REFRESH = "influencehub_refresh";
const ROLE = "influencehub_role";

function isValidRole(value: string | null): value is AccountRole {
  return value === "business" || value === "influencer" || value === "owner";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<AccountRole | null>(null);
  const [isReady, setIsReady] = useState(false);

  const signOut = () => {
    window.localStorage.removeItem(ACCESS);
    window.localStorage.removeItem(REFRESH);
    window.localStorage.removeItem(ROLE);
    setRole(null);
  };

  const signIn = (tokens: AuthTokens, nextRole: AccountRole) => {
    window.localStorage.setItem(ACCESS, tokens.access);
    window.localStorage.setItem(REFRESH, tokens.refresh || "");
    window.localStorage.setItem(ROLE, nextRole);
    setRole(nextRole);
  };

  useEffect(() => {
    const token = window.localStorage.getItem(ACCESS);

    if (!token) {
      setRole(null);
      setIsReady(true);
      return;
    }

    // Verify token with backend /api/me/ FIRST and synchronize the real role.
    // Only after the backend confirms the role do we set isReady and auth.role.
    // This prevents stale-localStorage roles from gate-keeping protected pages.
    api
      .getMe()
      .then((me) => {
        if (me && isValidRole(me.role)) {
          window.localStorage.setItem(ROLE, me.role);
          setRole(me.role);
        }
      })
      .catch((err) => {
        if (err?.response?.status === 401) {
          signOut();
        }
      })
      .finally(() => {
        setIsReady(true);
      });
  }, []);


  return <AuthContext.Provider value={{ role, isReady, signIn, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
