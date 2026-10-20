import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Campaign, CampaignStats, PendingApprovals, Publisher, UserRole } from "../types";

type Snapshot = { role: UserRole; name: string; campaigns: Campaign[]; publishers: Publisher[]; stats: CampaignStats[]; approvals: number; balance: number | null };

const roleCopy: Record<UserRole, { eyebrow: string; title: string; description: string }> = {
  admin: { eyebrow: "Network control room", title: "A clearer view of your ad network.", description: "Keep campaigns moving, review new accounts, and follow delivery from one place." },
  staff: { eyebrow: "Operations desk", title: "Your review queue, at a glance.", description: "Stay on top of account and inventory reviews that keep the network healthy." },
  advertiser: { eyebrow: "Advertiser workspace", title: "Make every campaign count.", description: "Check your campaign activity, manage your creative, and keep your balance ready." },
  publisher: { eyebrow: "Publisher workspace", title: "Build inventory that earns.", description: "Bring your sites and ad slots online, then keep an eye on your network earnings." },
};

const since = (days: number) => new Date(Date.now() - days * 86400000).toISOString();

export function HomePage() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const user = await api.me() as { role?: UserRole; first_name?: string | null; last_name?: string | null; email?: string | null; mobile?: string | null };
        const role = user.role || "advertiser";
        const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email || user.mobile || "there";
        const results = await Promise.allSettled([
          role === "admin" || role === "advertiser" ? api.campaignStats(since(7), new Date().toISOString()) : Promise.resolve([]),
          role === "admin" || role === "advertiser" ? api.listCampaigns() : Promise.resolve([]),
          role === "publisher" ? api.listPublishers() : Promise.resolve([]),
          role === "admin" || role === "staff" ? api.listPendingApprovals() : Promise.resolve(null),
          role === "advertiser" ? api.advertiserWallet() : Promise.resolve(null),
        ]);
        const value = <T,>(index: number, fallback: T): T => results[index].status === "fulfilled" ? results[index].value as T : fallback;
        const pending = value<PendingApprovals | null>(3, null);
        if (live) setData({
          role, name,
          stats: value<CampaignStats[]>(0, []), campaigns: value<Campaign[]>(1, []),
          publishers: value<Publisher[]>(2, []),
          approvals: pending ? pending.publishers.length + pending.advertisers.length + pending.ad_units.length : 0,
          balance: value<{ balance: number } | null>(4, null)?.balance ?? null,
        });
      } catch {
        if (live) setData({ role: "advertiser", name: "there", campaigns: [], publishers: [], stats: [], approvals: 0, balance: null });
      } finally { if (live) setLoading(false); }
    })();
    return () => { live = false; };
  }, []);

  const totals = useMemo(() => (data?.stats || []).reduce((sum, row) => ({ impressions: sum.impressions + row.impressions, clicks: sum.clicks + row.clicks }), { impressions: 0, clicks: 0 }), [data]);
  const role = data?.role || "advertiser";
  const copy = roleCopy[role];
  const actions: Record<UserRole, { label: string; note: string; to: string; icon: string }[]> = {
    admin: [{ label: "Review approvals", note: "Move new accounts and inventory forward", to: "/approvals", icon: "✓" }, { label: "Manage campaigns", note: "See delivery across the network", to: "/manage-campaign", icon: "↗" }, { label: "Live events", note: "Watch incoming ad activity", to: "/live-events", icon: "◉" }],
    staff: [{ label: "Open review queue", note: "Review accounts and ad units", to: "/approvals", icon: "✓" }],
    advertiser: [{ label: "Create a campaign", note: "Set up your next campaign", to: "/campaigns", icon: "+" }, { label: "Add funds", note: "Keep your wallet ready for delivery", to: "/wallet", icon: "₹" }, { label: "Upload creative", note: "Organize assets for your campaigns", to: "/media", icon: "▧" }],
    publisher: [{ label: "Add your site", note: "Register inventory for review", to: "/publishers", icon: "+" }, { label: "Create an ad slot", note: "Prepare placements on your site", to: "/adslots", icon: "▤" }, { label: "View earnings", note: "Track earnings and payout status", to: "/earnings", icon: "₹" }],
  };
  const metrics = role === "admin" ? [["Campaigns", data?.campaigns.length ?? 0], ["Awaiting review", data?.approvals ?? 0], ["7-day impressions", totals.impressions]]
    : role === "staff" ? [["Items awaiting review", data?.approvals ?? 0], ["Review types", 3], ["Queue status", data ? "Ready" : "…"]]
      : role === "publisher" ? [["Your sites", data?.publishers.length ?? 0], ["Active sites", data?.publishers.filter(p => p.is_active).length ?? 0], ["Unpaid earnings", `₹${(data?.publishers.reduce((sum, p) => sum + Number(p.unpaid_earnings || 0), 0) ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`]]
        : [["Your campaigns", data?.campaigns.length ?? 0], ["Currently active", data?.campaigns.filter(c => c.is_active).length ?? 0], ["Wallet balance", data?.balance == null ? "—" : `₹${data.balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`]];

  return <Layout title="Home">
    <div className="mx-auto max-w-7xl space-y-6">
      <section className="relative overflow-hidden rounded-2xl border border-base-300 bg-base-200 p-6 sm:p-9">
        <div className="pointer-events-none absolute -right-12 -top-20 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.4fr_.6fr] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">{copy.eyebrow}</p>
            <h2 className="mt-4 max-w-2xl font-display text-3xl font-semibold tracking-tight sm:text-5xl">{copy.title}</h2>
            <p className="mt-4 max-w-xl text-sm leading-6 text-base-content/70 sm:text-base">{copy.description}</p>
            <p className="mt-6 text-sm text-base-content/60">Welcome back, <span className="font-medium text-base-content">{data?.name || "…"}</span></p>
          </div>
          <div className="rounded-xl border border-base-300 bg-base-100/80 p-5">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-base-content/60"><span className="h-2 w-2 animate-pulse rounded-full bg-success" /> Your workspace</div>
            <p className="mt-3 font-display text-xl font-semibold">{role === "admin" ? "Network overview" : role === "staff" ? "Review operations" : role === "publisher" ? "Publisher center" : "Campaign center"}</p>
            <p className="mt-2 text-sm text-base-content/60">{loading ? "Loading your latest activity…" : "Your workspace is up to date."}</p>
            <Link className="btn btn-primary btn-sm mt-5" to={role === "admin" || role === "staff" ? "/approvals" : role === "publisher" ? "/publishers" : "/analytics"}>{role === "admin" || role === "staff" ? "Open review queue" : role === "publisher" ? "Manage inventory" : "View analytics"}<span aria-hidden="true">→</span></Link>
          </div>
        </div>
      </section>

      <section aria-label="Workspace summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map(([label, value], index) => <div key={String(label)} className="rounded-xl border border-base-300 bg-base-200 p-5">
          <p className="text-sm text-base-content/60">{label}</p><p className={`mt-3 font-display text-3xl font-semibold tabular-nums ${index === 1 && role === "admin" && Number(value) > 0 ? "text-warning" : ""}`}>{loading ? "—" : value}</p>
          <p className="mt-2 text-xs text-base-content/50">{role === "advertiser" && label === "Wallet balance" ? "Available balance" : role === "publisher" && label === "Unpaid earnings" ? "Accumulated on your account" : role === "admin" && label === "7-day impressions" ? `${totals.clicks.toLocaleString()} clicks in the last 7 days` : "Current workspace"}</p>
        </div>)}
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[.16em] text-primary">Get things done</p><h2 className="mt-1 font-display text-xl font-semibold">Quick actions</h2></div>{role !== "staff" && <Link to="/analytics" className="link link-hover text-sm">Explore analytics →</Link>}</div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{actions[role].map(action => <Link to={action.to} key={action.label} className="group flex items-start gap-4 rounded-xl border border-base-300 bg-base-200 p-5 transition hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-lg">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-display text-xl font-semibold text-primary">{action.icon}</span><span className="min-w-0 flex-1"><span className="block font-semibold group-hover:text-primary">{action.label}</span><span className="mt-1 block text-sm leading-5 text-base-content/60">{action.note}</span></span><span aria-hidden="true" className="text-base-content/40 transition group-hover:translate-x-1 group-hover:text-primary">→</span>
        </Link>)}</div>
      </section>
    </div>
  </Layout>;
}
