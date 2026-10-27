"use client";

import { useParams } from "next/navigation";
import { PortalShell } from "@/components/layout/portal-shell";
import { MessageWorkspace } from "@/components/chat/message-workspace";

export default function InfluencerConversationPage() {
  const params = useParams<{ id: string }>();
  return <PortalShell role="influencer" title="Messages" subtitle="Private conversations open once a campaign is accepted."><MessageWorkspace role="influencer" conversationId={Number(params.id)} /></PortalShell>;
}
