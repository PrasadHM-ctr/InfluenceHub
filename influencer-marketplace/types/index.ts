export type UserRole = "business" | "influencer";
/** Every account kind incl. the privately-provisioned platform owner. */
export type AccountRole = UserRole | "owner";

export interface AuthTokens {
  access: string;
  refresh: string;
  role: AccountRole | null;
}

export type VerificationStatus = "Pending" | "Approved" | "Rejected";

export interface Influencer {
  id: number;
  full_name: string;
  bio?: string;
  category: string;
  language?: string;
  followers: number;
  instagram?: string;
  youtube?: string;
  facebook?: string;
  city: string;
  state: string;
  profile_image?: string | null;
  completion_percentage?: number;
  missing_fields?: string[];
  email_verified?: boolean;
  is_verified?: boolean;
  verification_status?: VerificationStatus;
  social_verification_code?: string;
  verification_submitted_at?: string | null;
  verification_reviewed_at?: string | null;
  verification_rejection_reason?: string;
}

export interface BusinessProfile {
  company_name: string;
  industry: string;
  website?: string;
  description?: string;
  phone: string;
  city: string;
  state: string;
  logo?: string | null;
  completion_percentage?: number;
  missing_fields?: string[];
}

export type CampaignStatus = "Pending" | "Accepted" | "Rejected" | "Completed" | "Cancelled";

export interface Campaign {
  id: number;
  business: number;
  business_name?: string;
  influencer: number;
  influencer_name?: string;
  conversation_id?: number | null;
  title: string;
  message: string;
  budget: string;
  status: CampaignStatus;
  attachment_url?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface BusinessDashboard {
  total_campaigns: number;
  pending: number;
  accepted: number;
  rejected: number;
  completed?: number;
  cancelled?: number;
}

export interface CampaignPayload {
  influencer: number;
  title: string;
  message: string;
  budget: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface InfluencerFilters {
  search?: string;
  category?: string;
  language?: string;
  city?: string;
  state?: string;
  min_followers?: string;
  max_followers?: string;
  verified_only?: boolean;
  page?: number;
}

export type NotificationType =
  | "campaign_new"
  | "campaign_accepted"
  | "campaign_rejected"
  | "campaign_completed"
  | "campaign_cancelled"
  | "message_new"
  | "verification";

export interface AppNotification {
  id: number;
  notification_type: NotificationType;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
}