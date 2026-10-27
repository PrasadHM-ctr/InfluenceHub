"use client";

import { PortalShell } from "@/components/layout/portal-shell";
import { NotificationsPageContent } from "@/components/notifications/notifications-page";

export default function BusinessNotificationsPage() {
  return <PortalShell role="business" title="Notifications" subtitle="Campaign decisions, messages, and account updates in one place."><NotificationsPageContent role="business" /></PortalShell>;
}