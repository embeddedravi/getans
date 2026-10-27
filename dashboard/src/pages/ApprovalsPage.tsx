import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { PendingApprovals } from "../types";
import { useListingControls } from "../components/ListingControls";

type Tab = "publishers" | "advertisers" | "ad_units";

export function ApprovalsPage() {
  const [admin, setAdmin] = useState<boolean | null>(null);
  const [items, setItems] = useState<PendingApprovals>({ publishers: [], advertisers: [], ad_units: [] });
  const [tab, setTab] = useState<Tab>("publishers");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const rows = items[tab] as Array<{ id: number; name?: string; slot_name?: string; site_url?: string; billing_email?: string; payout_email?: string; industry?: string | null; width?: number; height?: number; publisher_id?: number; created_at: string }>;
  const listing = useListingControls(rows, (row) => `${row.name || row.slot_name || ""} ${row.site_url || ""} ${row.billing_email || ""} ${row.payout_email || ""} ${row.industry || ""} ${row.publisher_id || ""}`);

  async function refresh() {
    try {
      setItems(await api.listPendingApprovals());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load approvals");
    }
  }

  useEffect(() => {
    api.me().then((user) => setAdmin(["admin", "staff"].includes((user as { role?: string }).role || ""))).catch(() => setAdmin(false));
  }, []);
  useEffect(() => { if (admin) void refresh(); }, [admin]);

  if (admin === null) return <Layout title="Approvals"><p>Loading…</p></Layout>;
  if (!admin) return <Navigate to="/" replace />;

  async function review(kind: Tab, id: number, decision: "approve" | "reject", event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const reason = String(form.get("reason") || "").trim();
    if (decision === "reject" && !reason) {
      setError("Enter a reason before rejecting this item.");
      return;
    }
    const key = `${kind}-${id}`;
    setBusy(key);
    setError("");
    try {
      const status = decision === "approve" ? (kind === "ad_units" ? "approved" : "active") : "rejected";
      if (kind === "publishers") await api.reviewPublisher(id, status as "active" | "rejected", reason || undefined);
      else if (kind === "advertisers") await api.reviewAdvertiser(id, status as "active" | "rejected", reason || undefined);
      else await api.reviewAdUnit(id, status as "approved" | "rejected", reason || undefined);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setBusy(null);
    }
  }

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "publishers", label: "Publishers", count: items.publishers.length },
    { id: "advertisers", label: "Advertisers", count: items.advertisers.length },
    { id: "ad_units", label: "Ad units", count: items.ad_units.length },
  ];
  const totalPending = tabs.reduce((total, item) => total + item.count, 0);
  return <Layout title="Pending approvals">
    <div className="space-y-6">
      <section className="overflow-hidden rounded-xl border border-base-300 bg-gradient-to-br from-base-200 via-base-200 to-primary/10 p-5 sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Review queue</p><h2 className="mt-2 font-display text-2xl font-semibold">Pending approvals</h2><p className="mt-1 max-w-xl text-sm opacity-70">Review new accounts and ad units. Approved items become eligible for the platform.</p></div>
          <div className="min-w-28 rounded-xl border border-base-300 bg-base-100/80 px-5 py-3 text-center"><div className="text-3xl font-semibold tabular-nums">{totalPending}</div><div className="mt-1 text-xs opacity-70">awaiting review</div></div>
        </div>
        <div role="tablist" className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {tabs.map((item) => <button key={item.id} role="tab" aria-selected={tab === item.id} onClick={() => setTab(item.id)} className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${tab === item.id ? "border-primary bg-primary/10" : "border-base-300 bg-base-100/60 hover:bg-base-100"}`}><span className="text-sm font-medium">{item.label}</span><span className={`badge badge-sm ${item.count ? "badge-primary" : "badge-ghost"}`}>{item.count}</span></button>)}
        </div>
      </section>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="flex flex-wrap items-end justify-between gap-3"><div><h3 className="font-display text-lg font-semibold">{tabs.find((item) => item.id === tab)?.label}</h3><p className="text-xs opacity-60">{items[tab].length} item{items[tab].length === 1 ? "" : "s"} in this queue</p></div>{listing.controls}</div>
      {listing.filtered.length === 0 ? <div className="rounded-xl border border-dashed border-base-300 bg-base-200/60 p-10 text-center"><div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-success/10 text-xl text-success">✓</div><h3 className="font-semibold">All caught up</h3><p className="mt-1 text-sm opacity-70">Nothing is waiting for review in {tabs.find((item) => item.id === tab)?.label.toLowerCase()}.</p></div> : <div className="grid gap-3 lg:grid-cols-2">
        {listing.pageItems.map((row) => <article key={row.id} className="rounded-xl border border-base-300 bg-base-200 p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full bg-warning"/><h3 className="truncate font-semibold">{row.name || row.slot_name}</h3><span className="badge badge-warning badge-xs">Pending</span></div>
              {tab === "publishers" && <div className="mt-3 space-y-1 text-sm"><p className="break-all">{row.site_url}</p><p className="opacity-70">Payout email: {row.payout_email}</p></div>}
              {tab === "advertisers" && <div className="mt-3 space-y-1 text-sm"><p className="break-all">{row.billing_email}</p>{row.industry && <p className="opacity-70">Industry: {row.industry}</p>}</div>}
              {tab === "ad_units" && <div className="mt-3 flex flex-wrap gap-2 text-xs"><span className="badge badge-outline">Publisher #{row.publisher_id}</span><span className="badge badge-outline">{row.width} × {row.height}</span></div>}
              <p className="mt-3 text-xs opacity-60">Submitted {new Date(row.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-base-300 pt-4">
            <form onSubmit={(event) => review(tab, row.id, "reject", event)} className="flex min-w-0 flex-1 flex-wrap gap-2">
              <input name="reason" required maxLength={500} placeholder="Reason required to reject" aria-label="Rejection reason" className="input input-bordered input-sm min-w-40 flex-1 bg-base-100" />
              <button disabled={busy === `${tab}-${row.id}`} className="btn btn-error btn-outline btn-sm">Reject</button>
            </form>
            <form onSubmit={(event) => review(tab, row.id, "approve", event)}><button disabled={busy === `${tab}-${row.id}`} className="btn btn-success btn-sm">{busy === `${tab}-${row.id}` ? "Saving…" : "Approve"}</button></form>
          </div>
        </article>)}
      </div>}
    </div>
  </Layout>;
}
