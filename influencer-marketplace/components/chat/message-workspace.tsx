"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import EmojiPicker, { type EmojiClickData, Theme } from "emoji-picker-react";
import { ArrowLeft, Check, CheckCheck, ChevronUp, FileText, ImageIcon, LoaderCircle, MessageCircle, Mic, Paperclip, Search, SendHorizontal, Smile, WifiOff } from "lucide-react";
import { toast } from "sonner";
import type { UserRole } from "@/types";
import type { ChatConversation, ChatMessage } from "@/types/chat";
import { chatApi } from "@/services/chat";
import { getApiError } from "@/services/api";
import { useChat } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";

function formatConversationTime(value: string) {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(date);
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" }).format(date);
}

function formatMessageTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function formatDay(value: string) {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(date);
}

function fileName(url: string) {
  return decodeURIComponent(url.split("/").pop() ?? "Attachment").replace(/_[A-Za-z0-9]{7}(?=\.)/, "");
}

function Avatar({ name, imageUrl, className }: { name: string; imageUrl?: string | null; className?: string }) {
  if (imageUrl) return <img src={imageUrl} alt="" className={cn("rounded-full object-cover", className)} />;
  return <span className={cn("grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 font-extrabold text-white", className)}>{name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span>;
}

function ConversationList({ role, activeId, compact = false }: { role: UserRole; activeId?: number; compact?: boolean }) {
  const [search, setSearch] = useState("");
  const conversations = useQuery({ queryKey: ["chat-conversations"], queryFn: chatApi.getConversations });
  const filtered = useMemo(() => (conversations.data ?? []).filter((conversation) => `${conversation.other_party.name} ${conversation.campaign_title}`.toLowerCase().includes(search.toLowerCase())), [conversations.data, search]);

  return <aside className={cn("flex min-h-0 flex-col border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950", compact ? "border-b" : "border-r")}><div className="border-b border-slate-100 px-5 py-5 dark:border-slate-800"><div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-violet-600">Private chat</p><h2 className="mt-1 text-xl font-extrabold text-slate-900 dark:text-white">Messages</h2></div><span className="grid h-9 w-9 place-items-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-950/50"><MessageCircle size={18} /></span></div><label className="relative mt-4 block"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search conversations" className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-violet-950" /></label></div><div className="min-h-0 flex-1 overflow-y-auto">{conversations.isLoading ? <div className="grid place-items-center p-10"><LoaderCircle className="animate-spin text-violet-600" size={22} /></div> : conversations.error ? <p className="p-5 text-sm text-rose-600">{getApiError(conversations.error)}</p> : filtered.length ? filtered.map((conversation) => <ConversationRow key={conversation.id} conversation={conversation} href={`/${role}/messages/${conversation.id}`} active={conversation.id === activeId} />) : <div className="p-8 text-center"><MessageCircle className="mx-auto text-slate-300" size={26} /><p className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No accepted campaign chats yet</p><p className="mt-1 text-xs leading-5 text-slate-500">A private chat opens automatically as soon as a campaign is accepted.</p></div>}</div></aside>;
}

function ConversationRow({ conversation, href, active }: { conversation: ChatConversation; href: string; active: boolean }) {
  const preview = conversation.latest_message?.text || (conversation.latest_message?.image_url ? "Image" : conversation.latest_message?.file_url ? "File attachment" : "No messages yet");
  return <Link href={href} className={cn("flex gap-3 border-b border-slate-100 px-5 py-4 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900", active && "bg-violet-50 dark:bg-violet-950/35")}><Avatar name={conversation.other_party.name} imageUrl={conversation.other_party.image_url} className="h-11 w-11 text-sm" /><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-3"><p className="truncate text-sm font-extrabold text-slate-900 dark:text-white">{conversation.other_party.name}</p><span className="shrink-0 text-[11px] text-slate-400">{formatConversationTime(conversation.latest_message?.created_at ?? conversation.updated_at)}</span></div><p className="mt-1 truncate text-xs font-medium text-violet-600">{conversation.campaign_title}</p><div className="mt-1 flex items-center justify-between gap-2"><p className="truncate text-xs text-slate-500">{preview}</p>{conversation.unread_count > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-violet-600 px-1 text-[10px] font-extrabold text-white">{conversation.unread_count > 99 ? "99+" : conversation.unread_count}</span>}</div></div></Link>;
}

function MessageBubble({ message, role }: { message: ChatMessage; role: UserRole }) {
  const isMine = message.sender_role === role;
  return <div className={cn("flex", isMine ? "justify-end" : "justify-start")}><div className={cn("max-w-[85%] rounded-2xl px-3.5 py-2.5 shadow-sm sm:max-w-[70%]", isMine ? "rounded-br-md bg-violet-600 text-white" : "rounded-bl-md bg-white text-slate-800 dark:bg-slate-900 dark:text-slate-100")}>
    {message.image_url && <a href={message.image_url} target="_blank" rel="noreferrer"><img src={message.image_url} alt="Shared image" className="max-h-72 w-full rounded-xl object-cover" /></a>}
    {message.file_url && <a href={message.file_url} target="_blank" rel="noreferrer" className={cn("flex items-center gap-3 rounded-xl p-2 transition", isMine ? "bg-white/15 hover:bg-white/20" : "bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700")}><span className={cn("grid h-9 w-9 place-items-center rounded-lg", isMine ? "bg-white/15" : "bg-white dark:bg-slate-900")}><FileText size={18} /></span><span className="min-w-0"><span className="block truncate text-xs font-bold">{fileName(message.file_url)}</span><span className={cn("mt-0.5 block text-[10px]", isMine ? "text-violet-100" : "text-slate-500")}>Open attachment</span></span></a>}
    {message.text && <p className={cn("whitespace-pre-wrap break-words text-sm leading-6", (message.image_url || message.file_url) && "mt-2")}>{message.text}</p>}
    <div className={cn("mt-1 flex items-center justify-end gap-1 text-[10px]", isMine ? "text-violet-100" : "text-slate-400")}><span>{formatMessageTime(message.created_at)}</span>{isMine && (message.is_read ? <CheckCheck size={13} /> : <Check size={13} />)}</div>
  </div></div>;
}

function MessageComposer({ conversationId, onMessage, onTyping, onUploaded }: { conversationId: number; onMessage: (text: string) => boolean; onTyping: () => void; onUploaded?: (message: ChatMessage) => void }) {
  const [text, setText] = useState("");
  const [showEmoji, setShowEmoji] = useState(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const upload = useMutation({ mutationFn: ({ file, type }: { file: File; type: "image" | "file" }) => chatApi.upload(conversationId, file, type), onSuccess: (message) => { onUploaded?.(message); toast.success("Attachment sent."); }, onError: (error) => toast.error(getApiError(error)) });
  const send = () => {
    const value = text.trim();
    if (!value) return;
    if (onMessage(value)) setText("");
    else toast.error("The chat is reconnecting. Please try again in a moment.");
  };
  const chooseFile = (event: React.ChangeEvent<HTMLInputElement>, type: "image" | "file") => { const file = event.target.files?.[0]; if (file) upload.mutate({ file, type }); event.target.value = ""; };
  const addEmoji = (emoji: EmojiClickData) => { setText((value) => `${value}${emoji.emoji}`); setShowEmoji(false); };
  return <div className="relative border-t border-slate-200 bg-white p-3 sm:p-4 dark:border-slate-800 dark:bg-slate-950">{showEmoji && <div className="absolute bottom-full left-3 z-20 mb-2 shadow-2xl"><EmojiPicker onEmojiClick={addEmoji} theme={Theme.AUTO} width={320} height={390} /></div>}<input ref={imageInput} type="file" accept="image/*" className="hidden" onChange={(event) => chooseFile(event, "image")} /><input ref={fileInput} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt" className="hidden" onChange={(event) => chooseFile(event, "file")} /><div className="flex items-end gap-2"><button type="button" onClick={() => setShowEmoji((open) => !open)} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-violet-600 dark:hover:bg-slate-900" aria-label="Choose emoji"><Smile size={20} /></button><button type="button" onClick={() => imageInput.current?.click()} disabled={upload.isPending} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-violet-600 disabled:opacity-50 dark:hover:bg-slate-900" aria-label="Upload image"><ImageIcon size={20} /></button><button type="button" onClick={() => fileInput.current?.click()} disabled={upload.isPending} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-violet-600 disabled:opacity-50 dark:hover:bg-slate-900" aria-label="Upload file"><Paperclip size={20} /></button><div className="relative flex-1"><textarea value={text} onChange={(event) => { setText(event.target.value); onTyping(); }} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Write a message…" rows={1} className="max-h-32 min-h-10 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-violet-950" /></div><button type="button" disabled title="Voice messages are not available yet" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-300 dark:text-slate-700" aria-label="Voice message"><Mic size={20} /></button><button type="button" onClick={send} disabled={!text.trim()} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-45" aria-label="Send message">{upload.isPending ? <LoaderCircle className="animate-spin" size={18} /> : <SendHorizontal size={18} />}</button></div></div>;
}

function ChatPanel({ conversation, role }: { conversation: ChatConversation; role: UserRole }) {
  const chat = useChat(conversation.id);
  const scrollAnchor = useRef<HTMLDivElement>(null);
  const latestId = chat.messages.at(-1)?.id;

  useEffect(() => { scrollAnchor.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [latestId]);
  useEffect(() => { chat.markRead(chat.messages.filter((message) => !message.is_read).map((message) => message.id)); }, [chat, chat.messages]);

  return <section className="flex min-h-0 flex-1 flex-col bg-slate-50 dark:bg-[#090d19]"><header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3.5 dark:border-slate-800 dark:bg-slate-950"><div className="flex min-w-0 items-center gap-3"><Link href={`/${role}/messages`} className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-900" aria-label="Back to messages"><ArrowLeft size={18} /></Link><Avatar name={conversation.other_party.name} imageUrl={conversation.other_party.image_url} className="h-10 w-10 text-sm" /><div className="min-w-0"><h2 className="truncate text-sm font-extrabold text-slate-900 dark:text-white">{conversation.other_party.name}</h2><p className="mt-0.5 truncate text-xs text-slate-500">{chat.isTyping ? "Typing…" : chat.isOtherOnline ? "Online" : conversation.campaign_title}</p></div></div><span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold", chat.connectionState === "connected" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300")}><span className={cn("h-1.5 w-1.5 rounded-full", chat.connectionState === "connected" ? "bg-emerald-500" : "bg-amber-500")} />{chat.connectionState === "connected" ? "Live" : "Reconnecting"}</span></header>{chat.socketError && <div className="flex items-center gap-2 border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300"><WifiOff size={14} />{chat.socketError}</div>}<div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">{chat.isLoading ? <div className="grid h-full place-items-center"><LoaderCircle className="animate-spin text-violet-600" size={24} /></div> : <><div className="mb-5 flex justify-center">{chat.hasMore && <button onClick={() => chat.loadOlder()} disabled={chat.isLoadingOlder} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 hover:border-violet-200 hover:text-violet-600 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">{chat.isLoadingOlder ? <LoaderCircle className="animate-spin" size={13} /> : <ChevronUp size={13} />}Load earlier messages</button>}</div>{chat.messages.length ? <div className="space-y-3">{chat.messages.map((message, index) => <div key={message.id}>{(index === 0 || new Date(message.created_at).toDateString() !== new Date(chat.messages[index - 1].created_at).toDateString()) && <div className="my-5 flex justify-center"><span className="rounded-full bg-slate-200 px-3 py-1 text-[10px] font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">{formatDay(message.created_at)}</span></div>}<MessageBubble message={message} role={role} /></div>)}</div> : <div className="grid h-full place-items-center text-center"><div><MessageCircle className="mx-auto text-violet-300" size={34} /><p className="mt-3 text-sm font-extrabold text-slate-700 dark:text-slate-200">Start the conversation</p><p className="mt-1 text-xs text-slate-500">This chat is private to the accepted campaign.</p></div></div>}<div ref={scrollAnchor} /></>}</div><MessageComposer conversationId={conversation.id} onMessage={chat.sendMessage} onTyping={chat.sendTyping} /></section>;
}

export function MessageWorkspace({ role, conversationId }: { role: UserRole; conversationId?: number }) {
  const conversations = useQuery({ queryKey: ["chat-conversations"], queryFn: chatApi.getConversations });
  const conversation = conversations.data?.find((item) => item.id === conversationId);
  return <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950"><div className="grid h-[calc(100vh-13.5rem)] min-h-[560px] lg:grid-cols-[340px_minmax(0,1fr)]"><div className={cn(conversationId && "hidden lg:block")}><ConversationList role={role} activeId={conversationId} /></div>{conversationId && conversations.isLoading ? <div className="grid place-items-center"><LoaderCircle className="animate-spin text-violet-600" size={24} /></div> : conversation ? <ChatPanel conversation={conversation} role={role} /> : conversationId ? <div className="grid place-items-center p-8 text-center"><div><MessageCircle className="mx-auto text-slate-300" size={36} /><h2 className="mt-4 font-extrabold text-slate-800 dark:text-slate-100">Conversation unavailable</h2><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">This chat may no longer be available to your account.</p><Link href={`/${role}/messages`} className="mt-5 inline-flex rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-bold text-white">Back to messages</Link></div></div> : <div className="hidden place-items-center bg-slate-50 p-8 text-center lg:grid dark:bg-[#090d19]"><div><MessageCircle className="mx-auto text-violet-300" size={42} /><h2 className="mt-4 text-xl font-extrabold text-slate-800 dark:text-slate-100">Select a conversation</h2><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Messages open after a campaign is accepted, keeping every discussion tied to its collaboration.</p></div></div>}</div></div>;
}
