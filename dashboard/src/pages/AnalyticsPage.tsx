import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import { subscribeToMetrics } from "../lib/socket";
import type { CampaignStats, Campaign, PendingApprovals, Publisher } from "../types";
import { Link } from "react-router-dom";

type Role = "admin" | "staff" | "publisher" | "advertiser";

export function AnalyticsPage() {
  const [stats, setStats] = useState<CampaignStats[]>([]);
  const [liveImpressions, setLiveImpressions] = useState(0);
  const [liveClicks, setLiveClicks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState<Role | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [approvalCount, setApprovalCount] = useState(0);

  useEffect(() => {
    const end = new Date();
    const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);

    api.me().then(async (user) => {
      const accountRole = (user as { role?: Role }).role;
      setRole(accountRole || null);
      if (accountRole === "publisher") {
        const data = await api.listPublishers();
        setPublishers(data as Publisher[]);
      } else if (accountRole === "staff") {
        const pending = await api.listPendingApprovals();
        setApprovalCount(pending.publishers.length + pending.advertisers.length + pending.ad_units.length);
      } else {
        const jobs: Promise<unknown>[] = [api.campaignStats(start.toISOString(), end.toISOString())];
        if (accountRole === "advertiser") jobs.push(api.listCampaigns());
        if (accountRole === "admin") jobs.push(api.listPendingApprovals());
        const [statsData, roleData] = await Promise.all(jobs);
        setStats(statsData as CampaignStats[]);
        if (accountRole === "advertiser") setCampaigns(roleData as Campaign[]);
        if (accountRole === "admin") {
          const pending = roleData as PendingApprovals;
          setApprovalCount(pending.publishers.length + pending.advertisers.length + pending.ad_units.length);
        }
      }
    }).catch(() => {
      setStats([]);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (role === null || role === "staff") return;
    return subscribeToMetrics((update) => {
      if (update.type === "impression") setLiveImpressions((n) => n + 1);
      if (update.type === "click") setLiveClicks((n) => n + 1);
    });
  }, [role]);

  const totals = useMemo(
    () =>
      stats.reduce(
        (acc, s) => ({
          impressions: acc.impressions + s.impressions,
          clicks: acc.clicks + s.clicks,
        }),
        { impressions: 0, clicks: 0 }
      ),
    [stats]
  );

  return (
    <Layout title={role === "admin" ? "Platform overview" : role === "staff" ? "Operations overview" : role === "publisher" ? "Earnings overview" : "Performance overview"}>
      <section className="mb-6 rounded border border-base-300 bg-base-200 p-5 md:p-6">
        <p className="text-xs font-medium uppercase tracking-widest text-primary">
          {role === "admin" || role === "staff" ? "Platform operations" : role === "publisher" ? "Publisher workspace" : "Advertiser workspace"}
        </p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-semibold">
              {role === "admin" ? "Platform overview" : role === "staff" ? "Review queue overview" : role === "publisher" ? "Your inventory & earnings" : "Your campaign performance"}
            </h2>
            <p className="mt-1 text-sm text-neutral-content">
              {role === "admin" ? "Monitor delivery and keep new accounts moving." : role === "staff" ? "Review new accounts and ad units waiting for approval." : role === "publisher" ? "Manage your sites and ad slots, then track your unpaid earnings." : "Track delivery and manage the campaigns you run on the network."}
            </p>
          </div>
          {role === "admin" || role === "staff" ? <Link className="btn btn-primary btn-sm" to="/approvals">{role === "staff" ? "Open review queue" : "Review approvals"}{approvalCount ? ` · ${approvalCount}` : ""}</Link> : role === "publisher" ? <Link className="btn btn-primary btn-sm" to="/publishers">Manage sites & slots</Link> : <Link className="btn btn-primary btn-sm" to="/campaigns">Manage campaigns</Link>}
        </div>
      </section>

      {role === "publisher" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatPanel label="Your sites" value={publishers.length} accent="text-primary" />
          <StatPanel label="Unpaid earnings" value={publishers.reduce((total, publisher) => total + Number(publisher.unpaid_earnings || 0), 0)} accent="text-success" prefix="₹" decimals />
          <div className="sm:col-span-2 rounded border border-base-300 bg-base-200 p-5">
            <h2 className="font-display text-base font-semibold">Get your inventory ready</h2>
            <p className="mt-2 text-sm text-neutral-content">Add your site and create ad slots to make your inventory available for review.</p>
            <Link className="btn btn-outline btn-sm mt-4" to="/publishers">Open sites & slots</Link>
          </div>
        </div>
      ) : role === "staff" ? (
        <div className="grid grid-cols-1 gap-4 mb-6">
          <StatPanel label="Items awaiting review" value={approvalCount} accent="text-warning" />
          <div className="rounded border border-base-300 bg-base-200 p-5">
            <h2 className="font-display text-base font-semibold">Keep the network ready</h2>
            <p className="mt-2 text-sm text-neutral-content">Review publisher and advertiser accounts, along with new ad units.</p>
            <Link className="btn btn-outline btn-sm mt-4" to="/approvals">Open review queue</Link>
          </div>
        </div>
      ) : role === "advertiser" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-6">
          <StatPanel label="Your campaigns" value={campaigns.length} accent="text-primary" />
          <StatPanel label="Active campaigns" value={campaigns.filter((campaign) => campaign.is_active).length} accent="text-success" />
          <StatPanel label="7-day impressions" value={totals.impressions} accent="text-base-content" />
        </div>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatPanel
          label="Impressions this session"
          value={liveImpressions}
          accent="text-warning"
        />
        <StatPanel label="Clicks this session" value={liveClicks} accent="text-secondary" />
        <StatPanel
          label="7-day impressions"
          value={totals.impressions}
          accent="text-base-content"
        />
      </div>
      )}

      {role !== "publisher" && role !== "staff" && <>
      <div className="border border-base-300 bg-base-200 rounded p-5">
        <h2 className="font-display text-base font-semibold mb-4">
          Impressions by campaign, last 7 days
        </h2>

        {loading ? (
          <p className="text-sm text-neutral-content">Loading...</p>
        ) : stats.length === 0 ? (
          <p className="text-sm text-neutral-content">
            No event data yet for this period. Once ads start serving, campaign
            performance will show up here.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={stats}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2E3742" />
              <XAxis
                dataKey="campaign_name"
                stroke="#8B94A3"
                tick={{ fontSize: 12, fontFamily: "IBM Plex Mono" }}
              />
              <YAxis stroke="#8B94A3" tick={{ fontSize: 12, fontFamily: "IBM Plex Mono" }} />
              <Tooltip
                contentStyle={{
                  background: "#1B212A",
                  border: "1px solid #2E3742",
                  fontFamily: "IBM Plex Mono",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="impressions" fill="#F2A93B" radius={[2, 2, 0, 0]} />
              <Bar dataKey="clicks" fill="#5B8DEF" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      </>}
    </Layout>
  );
}

function StatPanel({
  label,
  value,
  accent,
  prefix,
  decimals,
}: {
  label: string;
  value: number;
  accent: string;
  prefix?: string;
  decimals?: boolean;
}) {
  return (
    <div className="border border-base-300 bg-base-200 rounded p-5">
      <p className="text-xs text-neutral-content mb-2">{label}</p>
      <p className={`tabular text-3xl font-medium ${accent}`}>
        {prefix}{value.toLocaleString(undefined, decimals ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : undefined)}
      </p>
    </div>
  );
}
