// Kept in sync with backend/app/schemas/*.py

export type PublisherStatus = "pending_approval" | "active" | "suspended" | "rejected";

export interface Publisher {
  id: number;
  name: string;
  site_url: string;
  domain: string | null;
  category: string | null;
  api_key: string;
  status: PublisherStatus;
  is_active: boolean;
  ads_txt_verified: boolean;
  revenue_share_percentage: number;
  unpaid_earnings: number;
  payout_email: string;
  created_at: string;
}

export type AdFormatType = "display" | "banner" | "native" | "video" | "interstitial";

export interface AdUnit {
  id: number;
  publisher_id: number;
  slot_name: string;
  description: string | null;
  format_type: AdFormatType;
  width: number;
  height: number;
  reserve_price: number;
  is_active: boolean;
  allow_house_ads: boolean;
  settings: Record<string, unknown> | null;
  created_at: string;
}

export interface TargetingRules {
  countries?: string[];
  device_types?: string[];
  keywords?: string[];
}

export type CampaignStatus =
  | "draft"
  | "scheduled"
  | "active"
  | "paused"
  | "completed"
  | "exhausted"
  | "archived";

export type BiddingStrategy = "cpm" | "cpc" | "cpa";

export interface Campaign {
  id: number;
  advertiser_id: number;
  name: string;
  status: CampaignStatus;
  is_active: boolean;
  priority: number;
  bidding_strategy: BiddingStrategy;
  bid_amount: number;
  daily_cap: number | null;
  total_budget: number | null;
  spent_amount: number;
  start_date: string;
  end_date: string | null;
  targeting_rules: TargetingRules | null;
  created_at: string;
}

export type CreativeFormat = "image" | "html" | "video" | "native";
export type ReviewStatus = "pending" | "approved" | "rejected";

export interface Creative {
  id: number;
  campaign_id: number;
  name: string | null;
  asset_url: string;
  click_url: string;
  impression_tracker_url: string | null;
  format: CreativeFormat;
  width: number;
  height: number;
  is_active: boolean;
  review_status: ReviewStatus;
  rejection_reason: string | null;
  created_at: string;
}

export interface CampaignStats {
  campaign_id: number;
  campaign_name: string;
  impressions: number;
  clicks: number;
  ctr: number;
}

export interface MetricUpdate {
  type: "impression" | "click";
  campaign_id: number;
  ad_unit_id: number;
  timestamp: string;
}
