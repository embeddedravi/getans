export interface Publisher {
  id: number;
  name: string;
  site_url: string;
  api_key: string;
  is_active: boolean;
}

export interface AdUnit {
  id: number;
  publisher_id: number;
  slot_name: string;
  width: number;
  height: number;
}

export interface TargetingRules {
  countries?: string[];
  device_types?: string[];
  keywords?: string[];
}

export interface Campaign {
  id: number;
  advertiser_id: number;
  name: string;
  is_active: boolean;
  priority: number;
  daily_cap: number | null;
  start_date: string;
  end_date: string;
  targeting_rules: TargetingRules | null;
}

export interface Creative {
  id: number;
  campaign_id: number;
  asset_url: string;
  click_url: string;
  format: string;
  width: number;
  height: number;
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
