import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { useListingControls } from "../components/ListingControls";
import { api } from "../lib/api";
import type { Campaign, Creative } from "../types";

type CreativeRow = { creative: Creative; campaign: Campaign };

export function CreativesPage() {
  const [rows, setRows] = useState<CreativeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaignsPath, setCampaignsPath] = useState("/campaigns");
  const listing = useListingControls(rows, ({ creative, campaign }) =>
    `${creative.name ?? ""} ${creative.id} ${campaign.name} ${creative.review_status} ${creative.width} ${creative.height}`,
    ({ creative }) => creative.review_status,
    ["pending", "approved", "rejected"].map((value) => ({ value, label: value })));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.me().then((user) => {
      if (!cancelled && (user as { role?: string }).role === "admin") setCampaignsPath("/manage-campaign");
    }).catch(() => { });
    api.listCampaigns()
      .then(async (campaigns) => {
        const results = await Promise.all((campaigns as Campaign[]).map(async (campaign) => {
          const creatives = await api.listCreativesForCampaign(campaign.id) as Creative[];
          return creatives.map((creative) => ({ creative, campaign }));
        }));
        if (!cancelled) setRows(results.flat());
      })
      .catch((cause) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load creatives.");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <Layout title="Creatives">
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm">{rows.length} creative{rows.length === 1 ? "" : "s"}</p>
        <Link className="btn btn-primary btn-sm" to={campaignsPath}>Manage campaigns</Link>
      </div>
      {error && <div role="alert" className="alert alert-error mb-3 py-2 text-sm">{error}</div>}
      {listing.controls}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr className="text-xs"><th>Preview</th><th>Creative</th><th>Campaign</th><th>Size</th><th>Review</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={5} className="py-6 text-center text-sm">Loading creatives…</td></tr>
              : listing.filtered.length === 0 ? <tr><td colSpan={5} className="py-6 text-center text-sm">No creatives found.</td></tr>
                : listing.pageItems.map(({ creative, campaign }) => (
                  <tr key={creative.id} className="border-b border-base-300 last:border-0">
                    <td><img src={creative.asset_url} alt={creative.name ?? `Creative ${creative.id}`} className="max-h-14 max-w-24 rounded bg-base-100 object-contain" /></td>
                    <td className="font-medium">{creative.name || `Creative #${creative.id}`}</td>
                    <td><Link className="link" to={`${campaignsPath}?id=${campaign.id}`}>{campaign.name}</Link></td>
                    <td className="tabular text-sm">{creative.width}×{creative.height}</td>
                    <td><span className={`badge badge-sm ${creative.review_status === "approved" ? "badge-success" : creative.review_status === "rejected" ? "badge-error" : "badge-warning"}`}>{creative.review_status}</span></td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
