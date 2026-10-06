import { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Advertiser } from "../types";

const statusStyle: Record<Advertiser["status"], string> = {
  pending_verification: "badge-warning",
  active: "badge-success",
  suspended: "badge-error",
  rejected: "badge-ghost",
  archived: "badge-ghost",
};

export function AdminAdvertisersPage() {
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const refresh = useCallback(async () => {
    try {
      setAdvertisers(await api.listAdminAdvertisers());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load advertisers");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function review(advertiser: Advertiser, status: "active" | "suspended" | "rejected") {
    let reason: string | undefined;
    if (status === "rejected") {
      reason = window.prompt("Enter a reason for rejecting this advertiser:")?.trim();
      if (!reason) return;
    }
    const action = status === "active" ? (advertiser.status === "pending_verification" ? "Approve" : "Activate") : status === "suspended" ? "Suspend" : "Reject";
    if (!window.confirm(`${action} advertiser “${advertiser.name}”?`)) return;
    setBusy(advertiser.id);
    try {
      await api.reviewAdvertiser(advertiser.id, status, reason);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update advertiser");
    } finally {
      setBusy(null);
    }
  }

  return <Layout title="Manage advertisers">
    <div className="space-y-4">
      <p className="text-sm text-neutral-content">Review advertiser accounts and check their billing details and balances.</p>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr><th>Advertiser</th><th>Billing email</th><th>Status</th><th>Balance</th><th>Credit limit</th><th>Actions</th></tr></thead>
          <tbody>
            {advertisers.map((advertiser) => <tr key={advertiser.id}>
              <td><div className="font-medium">{advertiser.name}</div><div className="text-xs text-neutral-content">#{advertiser.id}{advertiser.industry ? ` · ${advertiser.industry}` : ""}</div></td>
              <td>{advertiser.billing_email}</td>
              <td><span className={`badge badge-sm ${statusStyle[advertiser.status]}`}>{advertiser.status.replace(/_/g, " ")}</span>{advertiser.rejection_reason && <div className="text-xs text-error mt-1">{advertiser.rejection_reason}</div>}</td>
              <td className="tabular">₹{Number(advertiser.balance).toFixed(2)}</td>
              <td className="tabular">₹{Number(advertiser.credit_limit).toFixed(2)}</td>
              <td><div className="flex gap-2">
                {advertiser.status === "pending_verification" && <>
                  <button disabled={busy === advertiser.id} className="btn btn-success btn-xs" onClick={() => void review(advertiser, "active")}>Approve</button>
                  <button disabled={busy === advertiser.id} className="btn btn-error btn-outline btn-xs" onClick={() => void review(advertiser, "rejected")}>Reject</button>
                </>}
                {advertiser.status === "active" && <button disabled={busy === advertiser.id} className="btn btn-warning btn-xs" onClick={() => void review(advertiser, "suspended")}>Suspend</button>}
                {(advertiser.status === "suspended" || advertiser.status === "rejected") && <button disabled={busy === advertiser.id} className="btn btn-success btn-xs" onClick={() => void review(advertiser, "active")}>Activate</button>}
              </div></td>
            </tr>)}
            {advertisers.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-sm text-neutral-content">No advertisers found.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>;
}
