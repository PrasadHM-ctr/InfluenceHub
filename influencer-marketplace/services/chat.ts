"use client";

import type { ChatConversation, ChatMessage, ChatMessagesPage } from "@/types/chat";
import { apiClient } from "@/services/api";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export const chatApi = {
  getConversations: async () => (await apiClient.get<ChatConversation[]>("/chat/conversations/")).data,
  getMessages: async (conversationId: number, before?: number) => {
    const suffix = before ? `?before=${before}` : "";
    return (await apiClient.get<ChatMessagesPage>(`/chat/messages/${conversationId}/${suffix}`)).data;
  },
  start: async (campaignId: number) => (await apiClient.post<ChatConversation>("/chat/start/", { campaign_id: campaignId })).data,
  upload: async (conversationId: number, file: File, type: "image" | "file") => {
    const form = new FormData();
    form.append("conversation", String(conversationId));
    form.append(type, file);
    return (await apiClient.post<ChatMessage>("/chat/upload/", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
};

export function getChatSocketUrl(conversationId: number) {
  const explicitUrl = process.env.NEXT_PUBLIC_WS_URL;
  const backendUrl = explicitUrl ?? apiUrl.replace(/\/api\/?$/, "");
  const webSocketBase = backendUrl.replace(/^http:/, "ws:").replace(/^https:/, "wss:").replace(/\/$/, "");
  const token = typeof window === "undefined" ? "" : window.localStorage.getItem("influencehub_access") ?? "";
  return `${webSocketBase}/ws/chat/${conversationId}/?token=${encodeURIComponent(token)}`;
}
