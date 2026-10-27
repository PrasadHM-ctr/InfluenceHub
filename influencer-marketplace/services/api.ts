"use client";

import axios, { AxiosError } from "axios";
import type {
  AppNotification,
  AuthTokens,
  BusinessDashboard,
  BusinessProfile,
  Campaign,
  CampaignPayload,
  Influencer,
  InfluencerFilters,
  Paginated,
} from "@/types";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api",
  timeout: 30000,
});

// Endpoints reachable without a JWT (registration + email verification + token refresh).
const PUBLIC_ENDPOINTS = [
  "/login/",
  "/register/",
  "/business/register/",
  "/influencer/register/",
  "/verify-email/",
  "/resend-verification/",
  "/forgot-password/",
  "/confirm-forgot-password/",
  "/token/refresh/",
  "/refresh/",
];

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const url = config.url || "";
    if (!PUBLIC_ENDPOINTS.some((endpoint) => url.includes(endpoint))) {
      const token = window.localStorage.getItem("influencehub_access");
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  failedQueue = [];
}

let hasRedirectedForExpiry = false;

function handleSessionExpired() {
  if (typeof window === "undefined" || hasRedirectedForExpiry) return;
  hasRedirectedForExpiry = true;
  const role = window.localStorage.getItem("influencehub_role");
  window.localStorage.removeItem("influencehub_access");
  window.localStorage.removeItem("influencehub_refresh");
  window.localStorage.removeItem("influencehub_role");

  setTimeout(() => {
    if (role === "influencer") {
      window.location.href = "/influencer/login";
    } else if (role === "owner") {
      window.location.href = "/owner/login";
    } else {
      window.location.href = "/business/login";
    }
  }, 100);
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (typeof window !== "undefined" && error instanceof AxiosError) {
      const originalRequest = error.config;
      const url = originalRequest?.url || "";
      const isPublic = PUBLIC_ENDPOINTS.some((endpoint) => url.includes(endpoint));
      const status = error.response?.status;

      // Only attempt refresh on 401 Unauthorized for protected endpoints
      if (!isPublic && status === 401 && originalRequest) {
        if ((originalRequest as unknown as { _retry?: boolean })._retry || url.includes("/token/refresh/")) {
          handleSessionExpired();
          return Promise.reject(error);
        }

        const refreshToken = window.localStorage.getItem("influencehub_refresh");
        if (!refreshToken) {
          handleSessionExpired();
          return Promise.reject(error);
        }

        if (isRefreshing) {
          return new Promise<string>((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((newToken) => {
              originalRequest.headers = originalRequest.headers || {};
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return apiClient(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        (originalRequest as unknown as { _retry?: boolean })._retry = true;
        isRefreshing = true;

        try {
          const baseURL = apiClient.defaults.baseURL ?? "http://127.0.0.1:8000/api";
          const res = await axios.post<AuthTokens>(`${baseURL}/token/refresh/`, {
            refresh: refreshToken,
          });
          const newAccess = res.data.access;
          if (!newAccess) throw new Error("No access token returned.");

          window.localStorage.setItem("influencehub_access", newAccess);
          if (res.data.refresh) {
            window.localStorage.setItem("influencehub_refresh", res.data.refresh);
          }

          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          processQueue(null, newAccess);
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          handleSessionExpired();
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
    }
    return Promise.reject(error);
  }
);

export function getApiError(error: unknown) {
  if (error instanceof AxiosError) {
    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      return "The server took too long to respond. Please try again.";
    }
    const data = error.response?.data;
    if (typeof data === "string") return data;
    if (typeof data === "object" && data !== null) {
      if ("detail" in data && typeof (data as Record<string, unknown>).detail === "string") {
        return String((data as Record<string, unknown>).detail);
      }
      const first = Object.values(data)[0];
      return Array.isArray(first) ? String(first[0]) : String(first ?? "Something went wrong.");
    }
  }
  return "Unable to reach the server. Please check your connection.";
}

function buildFilterParams(filters: InfluencerFilters) {
  const params: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    params[key] = value;
  }
  return params;
}

export const api = {
  // --- Authentication ---
  login: async (payload: { username: string; password: string }) => (await apiClient.post<AuthTokens>("/login/", payload)).data,
  refreshToken: async (refresh: string) => (await apiClient.post<AuthTokens>("/token/refresh/", { refresh })).data,
  getMe: async () => (await apiClient.get<{ id: number; username: string; email: string; role: string; is_active: boolean }>("/me/")).data,
  registerBusiness: async (payload: Record<string, string>) => (await apiClient.post<{ message: string; email?: string; email_sent?: boolean }>("/business/register/", payload)).data,
  registerInfluencer: async (payload: Record<string, string | number>) => (await apiClient.post<{ message: string; email?: string; email_sent?: boolean }>("/influencer/register/", payload)).data,
  verifyEmail: async (payload: { email: string; code: string }) => (await apiClient.post<{ message: string }>("/verify-email/", payload)).data,
  resendVerification: async (email: string) => (await apiClient.post<{ message: string; emailed?: boolean }>("/resend-verification/", { email })).data,
  forgotPassword: async (email: string) => (await apiClient.post<{ message: string }>("/forgot-password/", { email })).data,
  confirmForgotPassword: async (payload: { email: string; code: string; new_password: string }) => (await apiClient.post<{ message: string }>("/confirm-forgot-password/", payload)).data,

  // --- Business ---
  getBusinessDashboard: async () => (await apiClient.get<BusinessDashboard>("/business/dashboard/")).data,
  getBusinessProfile: async () => (await apiClient.get<BusinessProfile>("/business/profile/")).data,
  updateBusinessProfile: async (payload: Partial<BusinessProfile> | FormData) => (await apiClient.put("/business/profile/", payload)).data,

  // --- Influencer ---
  getInfluencerProfile: async () => (await apiClient.get<Influencer>("/influencer/profile/")).data,
  updateInfluencerProfile: async (payload: Record<string, unknown> | FormData) => (await apiClient.put<Influencer>("/influencer/profile/", payload)).data,
  requestVerification: async (instagram_url: string, refresh = false) =>
    (await apiClient.post<{ message: string; verification_code: string; social_verification_code?: string; instagram_url?: string; verification_status?: string }>("/influencer/verification/request/", { instagram_url, refresh })).data,

  // --- Discovery (server-side search, filters, pagination) ---
  getInfluencers: async (filters: InfluencerFilters = {}) =>
    (await apiClient.get<Paginated<Influencer>>("/influencers/", { params: buildFilterParams(filters) })).data,
  getInfluencer: async (id: string | number) => (await apiClient.get<Influencer>(`/influencers/${id}/`)).data,

  // --- Campaigns ---
  getCampaigns: async (status?: string) =>
    (await apiClient.get<Campaign[]>("/campaigns/", status && status !== "all" ? { params: { status } } : undefined)).data,
  createCampaign: async (payload: CampaignPayload & { attachment?: File | null }) => {
    const { attachment, ...rest } = payload;
    if (!attachment) return (await apiClient.post<Campaign>("/campaigns/send/", rest)).data;
    const form = new FormData();
    Object.entries(rest).forEach(([key, value]) => form.append(key, String(value)));
    form.append("attachment", attachment);
    return (await apiClient.post<Campaign>("/campaigns/send/", form)).data;
  },
  acceptCampaign: async (id: number) => (await apiClient.post(`/campaigns/${id}/accept/`)).data,
  rejectCampaign: async (id: number) => (await apiClient.post(`/campaigns/${id}/reject/`)).data,
  completeCampaign: async (id: number) => (await apiClient.post(`/campaigns/${id}/complete/`)).data,
  cancelCampaign: async (id: number) => (await apiClient.post(`/campaigns/${id}/cancel/`)).data,

  // --- Notifications ---
  getNotifications: async (unreadOnly = false) =>
    (await apiClient.get<Paginated<AppNotification>>("/notifications/", { params: unreadOnly ? { unread_only: true } : {} })).data,
  getUnreadNotificationCount: async () =>
    (await apiClient.get<{ unread_count: number }>("/notifications/unread-count/")).data,
  markNotificationRead: async (id: number) => (await apiClient.post(`/notifications/${id}/read/`)).data,
  markAllNotificationsRead: async () => (await apiClient.post("/notifications/read-all/")).data,

  // --- Chat extras ---
  getChatUnreadCount: async () => (await apiClient.get<{ unread_count: number }>("/chat/unread-count/")).data,
};