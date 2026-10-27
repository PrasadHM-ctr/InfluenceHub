import type { AccountRole, CampaignStatus, VerificationStatus } from "./index";

// ---------------------------------------------------------------------------
// Owner admin panel DTOs (mirror backend/adminpanel responses)
// ---------------------------------------------------------------------------

export interface AdminDashboardStats {
  users: {
    total: number;
    business: number;
    influencer: number;
    owner: number;
    verified: number;
    unverified: number;
    new_today: number;
    new_this_week: number;
  };
  campaigns: {
    total: number;
    pending: number;
    accepted: number;
    rejected: number;
    completed: number;
    cancelled: number;
    new_today: number;
    budget_total: string;
  };
  moderation: {
    pending_verifications: number;
    approved_verifications: number;
    rejected_verifications: number;
    inactive_accounts: number;
  };
}

export type AdminRoleFilter = "business" | "influencer" | "owner" | "none" | "";

export interface AdminUserRow {
  id: number;
  username: string;
  name: string;
  email: string;
  role: AccountRole | null;
  is_superuser: boolean;
  email_verified: boolean;
  account_status: "Active" | "Inactive";
  date_joined: string;
  last_activity: string | null;
  completion_percentage: number | null;
  verification_status?: string | null;
}

export interface AdminCampaignSummary {
  id: number;
  title: string;
  status: CampaignStatus;
  budget: string;
  business: string;
  influencer: string;
  created_at: string;
  updated_at: string;
}

export interface AdminUserProfile {
  type: "influencer" | "business";
  full_name?: string;
  company_name?: string;
  bio?: string;
  category?: string;
  language?: string;
  followers?: number;
  city?: string;
  state?: string;
  industry?: string;
  website?: string;
  description?: string;
  phone?: string;
  instagram?: string;
  youtube?: string;
  facebook?: string;
  email_verified?: boolean;
  is_verified?: boolean;
  verification_status?: VerificationStatus;
  social_code_configured?: boolean;
  social_verification_code?: string;
  verification_code?: string;
  verification_submitted_at?: string | null;
  verification_reviewed_at?: string | null;
  verification_rejection_reason?: string;
  image_url?: string | null;
  logo_url?: string | null;
  completion_percentage: number;
  missing_fields?: string[];
  risk_score?: number;
  risk_signals?: string[];
}

export interface AdminUserDetail {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: AccountRole | null;
  is_superuser: boolean;
  email_verified: boolean;
  account_status: "Active" | "Inactive";
  date_joined: string;
  last_login: string | null;
  last_activity: string | null;
  profile: AdminUserProfile | null;
  campaigns: {
    total: number;
    by_status: Record<string, number>;
    recent: AdminCampaignSummary[];
  };
}

export interface AdminInfluencerRow {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  category: string;
  language: string;
  city: string;
  state: string;
  followers: number;
  email_verified: boolean;
  account_status: "Active" | "Inactive";
  verification_status: VerificationStatus;
  social_verification_code?: string;
  social_code_configured?: boolean;
  campaign_count: number;
  completed_campaigns: number;
  completion_percentage: number;
  risk_score: number;
  risk_signals: string[];
  image_url: string | null;
  created_at: string;
}

export interface AdminBusinessRow {
  id: number;
  user_id: number;
  company_name: string;
  email: string;
  industry: string;
  city: string;
  state: string;
  website: string;
  email_verified: boolean;
  account_status: "Active" | "Inactive";
  campaign_count: number;
  completed_campaigns: number;
  completion_percentage: number;
  logo_url: string | null;
  created_at: string;
}

export interface AdminCampaignRow {
  id: number;
  business_id: number;
  business: string;
  influencer_id: number;
  influencer: string;
  title: string;
  budget: string;
  status: CampaignStatus;
  has_attachment: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminCampaignDetail extends AdminCampaignRow {
  message: string;
  attachment_url: string | null;
  business_detail: { company_name: string; email: string; city: string; state: string };
  influencer_detail: { full_name: string; email: string; followers: number; category: string };
}

export interface AdminVerificationRow {
  id: number;
  user_id: number;
  username?: string;
  full_name: string;
  email: string;
  category: string;
  language: string;
  city: string;
  state: string;
  followers: number;
  bio: string;
  instagram: string;
  youtube: string;
  facebook: string;
  social_code_configured: boolean;
  social_verification_code?: string;
  verification_code?: string;
  email_verified: boolean;
  account_status: "Active" | "Inactive";
  is_verified?: boolean;
  verification_status: VerificationStatus;
  verification_submitted_at?: string | null;
  verification_reviewed_at?: string | null;
  verification_rejection_reason?: string;
  reviewed_by?: string | null;
  image_url: string | null;
  completion_percentage: number;
  missing_fields: string[];
  risk_score: number;
  risk_signals: string[];
  created_at: string;
}

export interface AdminAnalytics {
  totals: {
    users: number;
    business_users: number;
    influencers: number;
    verified_users: number;
    unverified_users: number;
    campaigns: number;
    accepted_campaigns: number;
    completed_campaigns: number;
    rejected_campaigns: number;
    budget_total: string;
  };
  users_over_time: { date: string; count: number }[];
  business_registrations: { date: string; count: number }[];
  influencer_registrations: { date: string; count: number }[];
  campaign_activity: { date: string; count: number }[];
  campaign_status_distribution: { status: string; count: number }[];
}

export interface AdminAuditEntry {
  id: number;
  actor: string;
  action: string;
  target_type: string;
  target_id: string;
  description: string;
  created_at: string;
}

export interface AdminAttentionItem {
  key: string;
  label: string;
  count: number;
  link: string;
  latest_at: string | null;
  is_unread: boolean;
}

export interface AdminNotificationsFeed {
  unread_count: number;
  results: AdminAttentionItem[];
}

export interface AdminSettingsInfo {
  session_user: {
    id: number;
    username: string;
    email: string;
    role: AccountRole | null;
    is_superuser: boolean;
    date_joined: string;
  };
  owner_accounts: {
    id: number;
    username: string;
    email: string;
    is_superuser: boolean;
    date_joined: string;
  }[];
  recent_admin_actions: {
    id: number;
    actor: string;
    action: string;
    description: string;
    created_at: string;
  }[];
}