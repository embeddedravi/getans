import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Payout, PayoutStatus } from "../types";

const filters: { value: "all" | PayoutStatus; label: string }[] = [
  { value: "all", label: "All payments" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "paid", label: "Approved" },
  { value: "cancelled", label: "Canceled" },
  { value: "failed", label: "Failed" },
];

const statusStyle: Record<PayoutStatus, string> = {
  pending: "badge-warning",
  processing: "badge-info",
  paid: "badge-success",
  cancelled: "badge-ghost",
  failed: "badge-error",
};

export function PaymentsPage() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [payments, setPayments] = useState<Payout[]>([]);
  const [filter, setFilter] = useState<"all" | PayoutStatus>("all");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setPayments(await api.listPayouts(filter === "all" ? undefined : filter));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load payments");
    }
  }, [filter]);

  useEffect(() => {
    api.me()
      .then((user) => setIsAdmin((user as { role?: string }).role === "admin"))
      .catch(() => setIsAdmin(false));
  }, []);
  useEffect(() => { if (isAdmin) void refresh(); }, [isAdmin, refresh]);

  if (isAdmin === null) return <Layout title="Payments"><p>Loading…</p></Layout>;
  if (!isAdmin) return <Navigate to="/" replace />;

  async function setStatus(payment: Payout, status: PayoutStatus) {
    setBusyId(payment.id);
    setError("");
    try {
      await api.updatePayout(payment.id, { status });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update payment");
    } finally {
      setBusyId(null);
    }
  }

  return <Layout title="Payments">
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Publisher payments</h2>
        <p className="text-sm text-neutral-content">Review payout requests and record their status.</p>
      </div>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div role="tablist" aria-label="Filter payments" className="tabs tabs-bordered flex-wrap">
        {filters.map((item) => <button key={item.value} role="tab" aria-selected={filter === item.value}
          onClick={() => setFilter(item.value)} className={`tab ${filter === item.value ? "tab-active" : ""}`}>
          {item.label}
        </button>)}
      </div>
      {payments.length === 0 ? <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm text-neutral-content">
        No payments found.
      </div> : <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr><th>Payment</th><th>Publisher</th><th>Amount</th><th>Method</th><th>Status</th><th>Submitted</th><th>Actions</th></tr></thead>
          <tbody>{payments.map((payment) => {
            const open = payment.status === "pending" || payment.status === "processing";
            const busy = busyId === payment.id;
            return <tr key={payment.id}>
              <td className="font-mono text-xs">#{payment.id}</td>
              <td><div>Publisher #{payment.publisher_id}</div><div className="text-xs text-neutral-content">{payment.payout_email}</div></td>
              <td className="font-medium">₹{Number(payment.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
              <td>{payment.payment_method?.replaceAll("_", " ") || "—"}</td>
              <td><span className={`badge ${statusStyle[payment.status]}`}>{payment.status}</span></td>
              <td>{new Date(payment.created_at).toLocaleDateString()}</td>
              <td><div className="flex gap-2">
                {open && <>
                  <button className="btn btn-success btn-xs" disabled={busy} onClick={() => void setStatus(payment, "paid")}>Approve</button>
                  {payment.status === "pending" && <button className="btn btn-outline btn-info btn-xs" disabled={busy} onClick={() => void setStatus(payment, "processing")}>Processing</button>}
                  <button className="btn btn-error btn-outline btn-xs" disabled={busy} onClick={() => void setStatus(payment, "cancelled")}>Cancel</button>
                </>}
                {!open && payment.reference && <span className="text-xs text-neutral-content">Ref: {payment.reference}</span>}
              </div></td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
    </div>
  </Layout>;
}
