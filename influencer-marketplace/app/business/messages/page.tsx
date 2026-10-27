"use client";

import { PortalShell } from "@/components/layout/portal-shell";
import { MessageWorkspace } from "@/components/chat/message-workspace";

export default function BusinessMessagesPage() {
  return <PortalShell role="business" title="Messages" subtitle="Private conversations open once a campaign is accepted."><MessageWorkspace role="business" /></PortalShell>;
}
