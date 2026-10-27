"use client";

import { PortalShell } from "@/components/layout/portal-shell";
import { NotificationsPageContent } from "@/components/notifications/notifications-page";

export default function InfluencerNotificationsPage() {
  return <PortalShell role="influencer" title="Notifications" subtitle="Campaign requests, messages, and verification updates in one place."><NotificationsPageContent role="influencer" /></PortalShell>;
}