"use client";

import axios, { AxiosError } from "axios";
import type { AuthTokens } from "@/types";
import type {
  AdminAnalytics,
  AdminAuditEntry,
  AdminBusinessRow,
  AdminCampaignDetail,
  AdminCampaignRow,
  AdminDashboardStats,
  AdminInfluencerRow,
  AdminNotificationsFeed,
  AdminSettingsInfo,
  AdminUserDetail,
  AdminUserRow,
  AdminVerificationRow,
} from "@/types/admin";

/**
 * Dedicated axios client for owner-panel endpoints.
 *
 * Deliberately separate from `services/api.ts`: a 403 from an admin API
 * must surface as "no permission" instead of the shared interceptor's
 * logout-and-redirect behaviour used by business/influencer portals.
 * A dead session (401) still sends the owner back to the private login.
 */

export const OWNER_LOGIN_ROUTE = "/owner/login";

const TOKEN_KEY = "influencehub_access";

function redirectToOwnerLogin() {
  if (typeof window !== "undefined") window.location.href = OWNER_LOGIN_ROUTE;
}

export const adminClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api",
  timeout: 20000,
});

adminClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isAdminRefreshing = false;
let adminFailedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processAdminQueue(error: unknown, token: string | null = null) {
  adminFailedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  adminFailedQueue = [];
}

adminClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (typeof window !== "undefined" && error instanceof AxiosError) {
      const originalRequest = error.config;
      const url = originalRequest?.url || "";
      const status = error.response?.status;

      if (status === 401 && originalRequest) {
        if ((originalRequest as unknown as { _retry?: boolean })._retry || url.includes("/token/refresh/")) {
          redirectToOwnerLogin();
          return Promise.reject(error);
        }

        const refreshToken = window.localStorage.getItem("influencehub_refresh");
        if (!refreshToken) {
          redirectToOwnerLogin();
          return Promise.reject(error);
        }

        if (isAdminRefreshing) {
          return new Promise<string>((resolve, reject) => {
            adminFailedQueue.push({ resolve, reject });
          })
            .then((newToken) => {
              originalRequest.headers = originalRequest.headers || {};
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return adminClient(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        (originalRequest as unknown as { _retry?: boolean })._retry = true;
        isAdminRefreshing = true;

        try {
          const baseURL = adminClient.defaults.baseURL ?? "http://127.0.0.1:8000/api";
          const res = await axios.post<AuthTokens>(`${baseURL}/token/refresh/`, {
            refresh: refreshToken,
          });
          const newAccess = res.data.access;
          if (!newAccess) throw new Error("No access token returned.");

          window.localStorage.setItem(TOKEN_KEY, newAccess);
          if (res.data.refresh) {
            window.localStorage.setItem("influencehub_refresh", res.data.refresh);
          }

          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          processAdminQueue(null, newAccess);
          return adminClient(originalRequest);
        } catch (refreshError) {
          processAdminQueue(refreshError, null);
          redirectToOwnerLogin();
          return Promise.reject(refreshError);
        } finally {
          isAdminRefreshing = false;
        }
      }
    }
    return Promise.reject(error);
  }
);

export function getAdminApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response?.status === 403) {
      return "You do not have permission to access the owner panel.";
    }
    const data = error.response?.data;
    if (typeof data === "string" && data) return data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      return String((data as { detail: unknown }).detail);
    }
    if (error.response?.status === 500) return "Server error. Please try again.";
    if (error.response?.status === 404) return "Not found.";
  }
  return "Unable to reach the server. Please try again.";
}

type Params = Record<string, string | number | boolean | undefined>;

export interface UserListFilters extends Params {
  search?: string;
  role?: string;
  verification?: string;
  status?: string;
  sort?: string;
  page?: number;
}

function buildParams(filters: Params) {
  const params: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    params[key] = value;
  }
  return params;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Login via the standard Cognito-backed endpoint (same as every account). */
export async function ownerLogin(username: string, password: string): Promise<AuthTokens> {
  return (await adminClient.post<AuthTokens>("/login/", { username, password })).data;
}

/** Server-truth identity check - never trust localStorage alone. */
export async function fetchMe(): Promise<{ id: number; username: string; email: string; role: string | null }> {
  return (await adminClient.get("/me/")).data;
}

export const adminApi = {
  getDashboard: async () => (await adminClient.get<AdminDashboardStats>("/admin/dashboard/")).data,

  getUsers: async (filters: UserListFilters = {}) =>
    (
      await adminClient.get<PaginatedResponse<AdminUserRow> & { role_counts: Record<string, number> }>(
        "/admin/users/",
        { params: buildParams(filters) }
      )
    ).data,

  getUser: async (id: number | string) => (await adminClient.get<AdminUserDetail>(`/admin/users/${id}/`)).data,

  userAction: async (
    id: number | string,
    action: "suspend" | "activate" | "verify_profile" | "reject_profile"
  ) => (await adminClient.patch<{ detail: string }>(`/admin/users/${id}/`, { action })).data,

  deleteUser: async (id: number | string) => {
    await adminClient.delete(`/admin/users/${id}/`);
  },

  getInfluencers: async (filters: UserListFilters = {}) =>
    (await adminClient.get<PaginatedResponse<AdminInfluencerRow>>("/admin/influencers/", { params: buildParams(filters) }))
      .data,

  getBusinesses: async (filters: UserListFilters = {}) =>
    (await adminClient.get<PaginatedResponse<AdminBusinessRow>>("/admin/businesses/", { params: buildParams(filters) })).data,

  getCampaigns: async (filters: UserListFilters = {}) =>
    (
      await adminClient.get<PaginatedResponse<AdminCampaignRow> & { status_counts: Record<string, number> }>(
        "/admin/campaigns/",
        { params: buildParams(filters) }
      )
    ).data,

  getCampaign: async (id: number | string) =>
    (await adminClient.get<AdminCampaignDetail>(`/admin/campaigns/${id}/`)).data,

  cancelCampaign: async (id: number | string) =>
    (await adminClient.patch<{ detail: string }>(`/admin/campaigns/${id}/`, { status: "Cancelled", confirm: true })).data,

  getVerifications: async (filters: UserListFilters = {}) =>
    (
      await adminClient.get<PaginatedResponse<AdminVerificationRow> & { counts: Record<string, number> }>(
        "/admin/verifications/",
        { params: buildParams(filters) }
      )
    ).data,

  reviewVerification: async (profileId: number, decision: "approved" | "rejected", reason = "") =>
    (await adminClient.post<{ detail: string }>(`/admin/verifications/${profileId}/review/`, { decision, reason })).data,

  getAnalytics: async () => (await adminClient.get<AdminAnalytics>("/admin/analytics/")).data,

  getActivity: async (filters: UserListFilters = {}) =>
    (await adminClient.get<PaginatedResponse<AdminAuditEntry>>("/admin/activity/", { params: buildParams(filters) })).data,

  getAttentionFeed: async () => (await adminClient.get<AdminNotificationsFeed>("/admin/notifications/")).data,

  markAttentionSeen: async () => (await adminClient.post<{ detail: string }>("/admin/notifications/")).data,

  recordLoginAudit: async () => (await adminClient.post<{ detail: string }>("/admin/login-audit/")).data,

  getSettings: async () => (await adminClient.get<AdminSettingsInfo>("/admin/settings/")).data,
};