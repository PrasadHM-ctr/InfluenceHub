"use client";

import { useParams } from "next/navigation";
import { PortalShell } from "@/components/layout/portal-shell";
import { MessageWorkspace } from "@/components/chat/message-workspace";

export default function BusinessConversationPage() {
  const params = useParams<{ id: string }>();
  return <PortalShell role="business" title="Messages" subtitle="Private conversations open once a campaign is accepted."><MessageWorkspace role="business" conversationId={Number(params.id)} /></PortalShell>;
}
