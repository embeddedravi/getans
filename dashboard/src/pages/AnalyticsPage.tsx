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
import type { CampaignStats } from "../types";

export function AnalyticsPage() {
  const [stats, setStats] = useState<CampaignStats[]>([]);
  const [liveImpressions, setLiveImpressions] = useState(0);
  const [liveClicks, setLiveClicks] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const end = new Date();
    const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);

    api
      .campaignStats(start.toISOString(), end.toISOString())
      .then((data) => setStats(data as CampaignStats[]))
      .catch(() => setStats([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return subscribeToMetrics((update) => {
      if (update.type === "impression") setLiveImpressions((n) => n + 1);
      if (update.type === "click") setLiveClicks((n) => n + 1);
    });
  }, []);

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
    <Layout title="Analytics">
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
    </Layout>
  );
}

function StatPanel({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="border border-base-300 bg-base-200 rounded p-5">
      <p className="text-xs text-neutral-content mb-2">{label}</p>
      <p className={`tabular text-3xl font-medium ${accent}`}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}
