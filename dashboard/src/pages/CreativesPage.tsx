import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { useListingControls } from "../components/ListingControls";
import { api } from "../lib/api";
import type { Campaign, Creative } from "../types";

type CreativeRow = { creative: Creative; campaign: Campaign };

export function CreativesPage() {
  const [rows, setRows] = useState<CreativeRow[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaignsPath, setCampaignsPath] = useState("/campaigns");
  const [isAdmin, setIsAdmin] = useState(false);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const listing = useListingControls(rows, ({ creative, campaign }) =>
    `${creative.name ?? ""} ${creative.id} ${campaign.name} ${creative.review_status} ${creative.width} ${creative.height}`,
    ({ creative }) => creative.review_status,
    ["pending", "approved", "rejected"].map((value) => ({ value, label: value })), 100);

  useEffect(() => {
    api.me().then((user) => {
      if ((user as { role?: string }).role === "admin") {
        setIsAdmin(true);
        setCampaignsPath("/manage-campaign");
      }
    }).catch(() => { });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    api.listCreativesPage(page, 50, controller.signal)
      .then((response) => {
        if (cancelled) return;
        setRows(response.items);
        setTotal(response.total);
        setPages(response.pages);
      })
      .catch((cause) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load creatives.");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; controller.abort(); };
  }, [page]);

  async function reviewCreative(creative: Creative, status: "approved" | "rejected") {
    const reason = status === "rejected" ? window.prompt("Reason for rejection?")?.trim() : undefined;
    if (status === "rejected" && !reason) return;
    setReviewingId(creative.id);
    setError(null);
    try {
      await api.reviewCreative(creative.id, status, reason);
      setRows((current) => current.map((row) => row.creative.id === creative.id
        ? { ...row, creative: { ...row.creative, review_status: status, rejection_reason: reason ?? null } }
        : row));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not review creative.");
    } finally {
      setReviewingId(null);
    }
  }

  return (
    <Layout title="Creatives">
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm">{total} creative{total === 1 ? "" : "s"}</p>
        <Link className="btn btn-primary btn-sm" to={campaignsPath}>Manage campaigns</Link>
      </div>
      {error && <div role="alert" className="alert alert-error mb-3 py-2 text-sm">{error}</div>}
      {listing.controls}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr className="text-xs"><th>Preview</th><th>Creative</th><th>Campaign</th><th>Size</th><th>Review</th>{isAdmin && <th>Actions</th>}</tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-sm">Loading creatives…</td></tr>
              : listing.filtered.length === 0 ? <tr><td colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-sm">No creatives found.</td></tr>
                : listing.pageItems.map(({ creative, campaign }) => (
                  <tr key={creative.id} className="border-b border-base-300 last:border-0">
                    <td><img src={creative.asset_url} alt={creative.name ?? `Creative ${creative.id}`} className="max-h-14 max-w-24 rounded bg-base-100 object-contain" /></td>
                    <td className="font-medium">{creative.name || `Creative #${creative.id}`}</td>
                    <td><Link className="link" to={`${campaignsPath}?id=${campaign.id}`}>{campaign.name}</Link></td>
                    <td className="tabular text-sm">{creative.width}×{creative.height}</td>
                    <td><span className={`badge badge-sm ${creative.review_status === "approved" ? "badge-success" : creative.review_status === "rejected" ? "badge-error" : "badge-warning"}`}>{creative.review_status}</span></td>
                    {isAdmin && <td><div className="flex gap-1">
                      {creative.review_status !== "approved" && <button className="btn btn-success btn-xs" disabled={reviewingId === creative.id} onClick={() => void reviewCreative(creative, "approved")}>Approve</button>}
                      {creative.review_status !== "rejected" && <button className="btn btn-error btn-outline btn-xs" disabled={reviewingId === creative.id} onClick={() => void reviewCreative(creative, "rejected")}>Reject</button>}
                    </div></td>}
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && <div className="mt-3 flex items-center justify-center gap-3" aria-label="Creative pages">
        <button className="btn btn-sm" aria-label="Previous creatives page" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>‹ Previous</button>
        <span className="text-sm">Page {page} of {pages}</span>
        <button className="btn btn-sm" aria-label="Next creatives page" disabled={page >= pages || loading} onClick={() => setPage((value) => value + 1)}>Next ›</button>
      </div>}
    </Layout>
  );
}
