import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdvertiserTopUp } from "../types";
import { useListingControls } from "../components/ListingControls";

export function AdvertiserPaymentsPage() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [payments, setPayments] = useState<AdvertiserTopUp[]>([]);
  const listing = useListingControls(payments, (payment) => `${payment.id} ${payment.advertiser_name} ${payment.billing_email} ${payment.status} ${payment.order_id} ${payment.payment_id || ""}`,
    (payment) => payment.status, [{ value: "paid", label: "Paid" }, { value: "created", label: "Created" }]);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      setPayments(await api.listAdvertiserTopUps());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load advertiser payments");
    }
  }, []);
  useEffect(() => {
    api.me().then((user) => setIsAdmin((user as { role?: string }).role === "admin")).catch(() => setIsAdmin(false));
  }, []);
  useEffect(() => { if (isAdmin) void refresh(); }, [isAdmin, refresh]);
  if (isAdmin === null) return <Layout title="Payments"><p>Loading…</p></Layout>;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <Layout title="Payments">
    <div className="space-y-5">
      <div><h2 className="text-lg font-semibold">Advertiser payments</h2><p className="text-sm ">Review advertiser wallet top ups and their payment status.</p></div>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      {listing.controls}
      {listing.filtered.length === 0 ? <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm ">No advertiser payments found.</div> :
        <div className="overflow-x-auto rounded border border-base-300 bg-base-200"><table className="table">
          <thead><tr><th>Payment</th><th>Advertiser</th><th>Amount</th><th>Status</th><th>Order ID</th><th>Payment ID</th><th>Created</th></tr></thead>
          <tbody>{listing.pageItems.map((payment) => <tr key={payment.id}>
            <td className="font-mono text-xs">#{payment.id}</td>
            <td><div>{payment.advertiser_name}</div><div className="text-xs ">{payment.billing_email}</div></td>
            <td className="font-medium">₹{Number(payment.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
            <td><span className={"badge " + (payment.status === "paid" ? "badge-success" : "badge-warning")}>{payment.status}</span></td>
            <td className="font-mono text-xs">{payment.order_id}</td><td className="font-mono text-xs">{payment.payment_id || "—"}</td>
            <td>{new Date(payment.created_at).toLocaleDateString()}</td>
          </tr>)}</tbody>
        </table></div>}
    </div>
  </Layout>;
}
