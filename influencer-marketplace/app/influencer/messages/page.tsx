"use client";

import { PortalShell } from "@/components/layout/portal-shell";
import { MessageWorkspace } from "@/components/chat/message-workspace";

export default function InfluencerMessagesPage() {
  return <PortalShell role="influencer" title="Messages" subtitle="Private conversations open once a campaign is accepted."><MessageWorkspace role="influencer" /></PortalShell>;
}
