import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { PendingApprovals } from "../types";

type Tab = "publishers" | "advertisers" | "ad_units";

export function ApprovalsPage() {
  const [admin, setAdmin] = useState<boolean | null>(null);
  const [items, setItems] = useState<PendingApprovals>({ publishers: [], advertisers: [], ad_units: [] });
  const [tab, setTab] = useState<Tab>("publishers");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

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
  const rows = items[tab] as Array<{ id: number; name?: string; slot_name?: string; site_url?: string; billing_email?: string; payout_email?: string; industry?: string | null; width?: number; height?: number; publisher_id?: number; created_at: string }>;

  return <Layout title="Pending approvals">
    <div className="space-y-5">
      <div><h2 className="text-lg font-semibold">Review new accounts and ad units</h2><p className="text-sm text-neutral-content">Approved items become eligible for the platform.</p></div>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div role="tablist" className="tabs tabs-bordered">
        {tabs.map((item) => <button key={item.id} role="tab" aria-selected={tab === item.id} onClick={() => setTab(item.id)} className={`tab ${tab === item.id ? "tab-active" : ""}`}>{item.label}<span className="badge badge-sm ml-2">{item.count}</span></button>)}
      </div>
      {rows.length === 0 ? <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm text-neutral-content">Nothing is waiting for review.</div> : <div className="space-y-3">
        {rows.map((row) => <article key={row.id} className="rounded border border-base-300 bg-base-200 p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><h3 className="font-medium">{row.name || row.slot_name}</h3>
              {tab === "publishers" && <p className="text-sm text-neutral-content">{row.site_url} · {row.payout_email}</p>}
              {tab === "advertisers" && <p className="text-sm text-neutral-content">{row.billing_email}{row.industry ? ` · ${row.industry}` : ""}</p>}
              {tab === "ad_units" && <p className="text-sm text-neutral-content">Publisher #{row.publisher_id} · {row.width} × {row.height}</p>}
              <p className="text-xs text-neutral-content mt-1">Submitted {new Date(row.created_at).toLocaleDateString()}</p>
            </div>
            <form onSubmit={(event) => review(tab, row.id, "approve", event)}><button disabled={busy === `${tab}-${row.id}`} className="btn btn-success btn-sm">Approve</button></form>
          </div>
          <form onSubmit={(event) => review(tab, row.id, "reject", event)} className="mt-3 flex flex-wrap gap-2">
            <input name="reason" required maxLength={500} placeholder="Reason required to reject" aria-label="Rejection reason" className="input input-bordered input-sm flex-1 min-w-56" />
            <button disabled={busy === `${tab}-${row.id}`} className="btn btn-error btn-outline btn-sm">Reject</button>
          </form>
        </article>)}
      </div>}
    </div>
  </Layout>;
}
