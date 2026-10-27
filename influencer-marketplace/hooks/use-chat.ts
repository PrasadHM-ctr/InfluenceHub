"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ChatMessage } from "@/types/chat";
import { chatApi, getChatSocketUrl } from "@/services/chat";

function mergeMessages(current: ChatMessage[], incoming: ChatMessage[]) {
  const byId = new Map(current.map((message) => [message.id, message]));
  incoming.forEach((message) => byId.set(message.id, { ...byId.get(message.id), ...message }));
  return Array.from(byId.values()).sort((left, right) => left.id - right.id);
}

export function useChat(conversationId: number) {
  const queryClient = useQueryClient();
  const initialMessages = useQuery({
    queryKey: ["chat-messages", conversationId],
    queryFn: () => chatApi.getMessages(conversationId),
    enabled: Number.isFinite(conversationId) && conversationId > 0,
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [isOtherOnline, setIsOtherOnline] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "reconnecting" | "offline">("connecting");
  const [socketError, setSocketError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!initialMessages.data) return;
    setMessages((current) => mergeMessages(current, initialMessages.data.messages));
    setHasMore(initialMessages.data.has_more);
  }, [initialMessages.data]);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((current) => mergeMessages(current, [message]));
    queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
  }, [queryClient]);

  const sendJson = useCallback((payload: object) => {
    if (socketRef.current?.readyState !== WebSocket.OPEN) return false;
    socketRef.current.send(JSON.stringify(payload));
    return true;
  }, []);

  const markRead = useCallback((messageIds: number[]) => {
    if (messageIds.length) sendJson({ type: "read", message_ids: messageIds });
  }, [sendJson]);

  useEffect(() => {
    if (!Number.isFinite(conversationId) || conversationId <= 0) return;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      setConnectionState(socketRef.current ? "reconnecting" : "connecting");
      const socket = new WebSocket(getChatSocketUrl(conversationId));
      socketRef.current = socket;

      socket.onopen = () => {
        setConnectionState("connected");
        setSocketError(null);
      };
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data) as { type: string; message?: ChatMessage; message_ids?: number[]; is_online?: boolean; is_typing?: boolean; detail?: string };
        if (payload.type === "message" && payload.message) {
          addMessage(payload.message);
          if (!payload.message.is_read) socket.send(JSON.stringify({ type: "read", message_ids: [payload.message.id] }));
        }
        if (payload.type === "read_receipt" && payload.message_ids) {
          setMessages((current) => current.map((message) => payload.message_ids?.includes(message.id) ? { ...message, is_read: true } : message));
        }
        if (payload.type === "typing") setIsTyping(Boolean(payload.is_typing));
        if (payload.type === "online_status") setIsOtherOnline(Boolean(payload.is_online));
        if (payload.type === "error") setSocketError(payload.detail ?? "Chat connection error.");
      };
      socket.onclose = (event) => {
        if (cancelled) return;
        if (event.code === 4403) {
          setConnectionState("offline");
          setSocketError("Unauthorized: You do not have access to this conversation.");
          return;
        }
        setConnectionState("reconnecting");
        reconnectTimer = setTimeout(connect, 2000);
      };
      socket.onerror = () => setSocketError("Live updates are temporarily unavailable. Reconnecting…");
    };

    connect();
    const presenceTimer = window.setInterval(() => sendJson({ type: "presence_ping" }), 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(presenceTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [addMessage, conversationId, sendJson]);

  useEffect(() => () => {
    if (typingTimer.current) clearTimeout(typingTimer.current);
  }, []);

  const sendMessage = useCallback((text: string) => sendJson({ type: "message", text }), [sendJson]);

  const sendTyping = useCallback(() => {
    if (!sendJson({ type: "typing", is_typing: true })) return;
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => sendJson({ type: "typing", is_typing: false }), 1200);
  }, [sendJson]);

  const loadOlder = useCallback(async () => {
    const firstMessage = messages[0];
    if (!hasMore || !firstMessage || isLoadingOlder) return;
    setIsLoadingOlder(true);
    try {
      const page = await chatApi.getMessages(conversationId, firstMessage.id);
      setMessages((current) => mergeMessages(current, page.messages));
      setHasMore(page.has_more);
    } finally {
      setIsLoadingOlder(false);
    }
  }, [conversationId, hasMore, isLoadingOlder, messages]);

  return {
    messages,
    hasMore,
    isLoading: initialMessages.isLoading,
    isLoadingOlder,
    loadOlder,
    sendMessage,
    sendTyping,
    markRead,
    addMessage,
    isOtherOnline,
    isTyping,
    connectionState,
    socketError,
  };
}
