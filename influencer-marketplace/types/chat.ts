export interface ChatParticipant {
  id: number;
  name: string;
  role: "business" | "influencer";
  image_url: string | null;
}

export interface ChatMessage {
  id: number;
  conversation: number;
  sender_id: number;
  sender_name: string;
  sender_role: "business" | "influencer" | null;
  text: string;
  image_url: string | null;
  file_url: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ChatConversation {
  id: number;
  campaign_id: number;
  campaign_title: string;
  campaign_budget: string;
  other_party: ChatParticipant;
  latest_message: ChatMessage | null;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessagesPage {
  messages: ChatMessage[];
  has_more: boolean;
}
