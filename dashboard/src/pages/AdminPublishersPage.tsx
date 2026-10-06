import { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Publisher } from "../types";

const statusStyle: Record<Publisher["status"], string> = {
  pending_approval: "badge-warning",
  active: "badge-success",
  suspended: "badge-error",
  rejected: "badge-ghost",
};

export function AdminPublishersPage() {
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setPublishers(await api.listPublishers() as Publisher[]);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load publishers");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function setStatus(publisher: Publisher, status: "active" | "suspended" | "rejected") {
    let rejectionReason: string | undefined;
    if (status === "rejected") {
      rejectionReason = window.prompt("Enter a reason for rejecting this publisher:")?.trim();
      if (!rejectionReason) return;
    }

    const action = status === "active"
      ? publisher.status === "pending_approval" ? "Approve" : "Activate"
      : status === "suspended" ? "Suspend" : "Reject";
    if (!window.confirm(`${action} publisher “${publisher.name}”?`)) return;

    setBusy(publisher.id);
    try {
      await api.reviewPublisher(publisher.id, status, rejectionReason);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update publisher");
    } finally {
      setBusy(null);
    }
  }

  return <Layout title="Manage publishers">
    <div className="space-y-4">
      <p className="text-sm text-neutral-content">Review publisher accounts and manage their status, payout details, and inventory settings.</p>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr><th>Publisher</th><th>Payout email</th><th>Revenue share</th><th>Unpaid earnings</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {publishers.map((publisher) => <tr key={publisher.id}>
              <td>
                <div className="font-medium">{publisher.name}</div>
                <a className="text-xs link link-hover text-neutral-content" href={publisher.site_url} target="_blank" rel="noreferrer">{publisher.site_url}</a>
                <div className="text-xs text-neutral-content">#{publisher.id}{publisher.domain ? ` · ${publisher.domain}` : ""}</div>
              </td>
              <td>{publisher.payout_email}</td>
              <td className="tabular">{Number(publisher.revenue_share_percentage).toFixed(2)}%</td>
              <td className="tabular">₹{Number(publisher.unpaid_earnings).toFixed(2)}</td>
              <td>
                <span className={`badge badge-sm ${statusStyle[publisher.status]}`}>{publisher.status.replace(/_/g, " ")}</span>
                {publisher.rejection_reason && <div className="mt-1 text-xs text-error">{publisher.rejection_reason}</div>}
              </td>
              <td><div className="flex flex-wrap gap-2">
                {publisher.status === "pending_approval" && <>
                  <button disabled={busy === publisher.id} className="btn btn-success btn-xs" onClick={() => void setStatus(publisher, "active")}>Approve</button>
                  <button disabled={busy === publisher.id} className="btn btn-error btn-outline btn-xs" onClick={() => void setStatus(publisher, "rejected")}>Reject</button>
                </>}
                {publisher.status === "active" && <button disabled={busy === publisher.id} className="btn btn-warning btn-xs" onClick={() => void setStatus(publisher, "suspended")}>Suspend</button>}
                {(publisher.status === "suspended" || publisher.status === "rejected") && <button disabled={busy === publisher.id} className="btn btn-success btn-xs" onClick={() => void setStatus(publisher, "active")}>Activate</button>}
              </div></td>
            </tr>)}
            {publishers.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-sm text-neutral-content">No publishers found.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>;
}
