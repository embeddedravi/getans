// Kept in sync with backend/app/schemas/*.py

export type PublisherStatus = "pending_approval" | "active" | "suspended" | "rejected";

export type UserRole = "admin" | "staff" | "publisher" | "advertiser";
export interface AdminUser {
  id: number;
  mobile: string | null;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  publisher_id: number | null;
  advertiser_id: number | null;
  last_login_at: string | null;
  created_at: string;
}

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
  rejection_reason: string | null;
  created_at: string;
}

export type AdFormatType = "display" | "banner" | "native" | "video" | "interstitial";
export type AdUnitStatus = "pending_review" | "approved" | "rejected";

export type AccountStatus = "pending_verification" | "active" | "suspended" | "rejected" | "archived";

export interface Advertiser {
  id: number;
  name: string;
  company_legal_name: string | null;
  billing_email: string;
  website_url: string | null;
  industry: string | null;
  status: AccountStatus;
  is_verified: boolean;
  currency: "INR";
  balance: number;
  credit_limit: number;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdvertiserWallet {
  balance: number;
  currency: "INR";
  credit_limit: number;
}

export interface AdvertiserTopUp {
  id: number;
  advertiser_id: number;
  advertiser_name: string;
  billing_email: string;
  amount: number;
  status: "created" | "paid";
  order_id: string;
  payment_id: string | null;
  paid_at: string | null;
  created_at: string;
}

export type PayoutStatus = "pending" | "processing" | "paid" | "failed" | "cancelled";

export interface Payout {
  id: number;
  publisher_id: number;
  amount: number;
  status: PayoutStatus;
  payment_method: "stripe" | "paypal" | "wire_transfer" | null;
  payout_email: string;
  reference: string | null;
  failure_reason: string | null;
  period_start: string | null;
  period_end: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface RazorpayTopUpOrder {
  order_id: string;
  amount_paise: number;
  currency: "INR";
  key_id: string;
  advertiser_name: string;
  billing_email: string;
}

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
  status: AdUnitStatus;
  rejection_reason: string | null;
  settings: Record<string, unknown> | null;
  created_at: string;
}

export interface PendingApprovals {
  publishers: Publisher[];
  advertisers: Advertiser[];
  ad_units: AdUnit[];
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
