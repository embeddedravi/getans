import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { useListingControls } from "../components/ListingControls";
import { api } from "../lib/api";
import type { Payout, Publisher } from "../types";

const statusStyle: Record<Payout["status"], string> = {
  pending: "badge-warning",
  processing: "badge-info",
  paid: "badge-success",
  failed: "badge-error",
  cancelled: "badge-ghost",
};

function formatINR(amount: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(amount);
}

export function PublisherEarningsPage() {
  const [role, setRole] = useState<string | null>(null);
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [error, setError] = useState("");
  const listing = useListingControls(
    payouts,
    (payout) => `${payout.id} ${payout.amount} ${payout.status} ${payout.payment_method || ""} ${payout.payout_email} ${payout.reference || ""}`,
    (payout) => payout.status,
    [
      { value: "pending", label: "Pending" },
      { value: "processing", label: "Processing" },
      { value: "paid", label: "Paid" },
      { value: "failed", label: "Failed" },
      { value: "cancelled", label: "Cancelled" },
    ],
  );

  useEffect(() => {
    api.me().then(async (user) => {
      const accountRole = (user as { role?: string }).role || "";
      setRole(accountRole);
      if (accountRole !== "publisher") return;
      const [publisherRows, payoutRows] = await Promise.all([api.listPublishers(), api.listPayouts()]);
      setPublishers(publisherRows as Publisher[]);
      setPayouts(payoutRows);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "Could not load earnings and payouts");
    });
  }, []);

  if (role === null && !error) return <Layout title="Earnings & payouts"><p className="text-sm">Loading earnings…</p></Layout>;
  if (role !== null && role !== "publisher") return <Navigate to="/" replace />;

  const unpaidEarnings = publishers.reduce((total, publisher) => total + Number(publisher.unpaid_earnings || 0), 0);
  return <Layout title="Earnings & payouts">
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-widest text-primary">Publisher account</p>
        <h2 className="mt-2 font-display text-2xl font-semibold">Earnings & payouts</h2>
        <p className="mt-1 text-sm">Review your unpaid earnings and payout history.</p>
      </section>

      <section className="rounded border border-base-300 bg-base-200 p-5">
        <p className="text-xs">Unpaid earnings</p>
        <p className="mt-2 tabular text-3xl font-medium text-success">{formatINR(unpaidEarnings)}</p>
        <p className="mt-1 text-xs">Across {publishers.length} {publishers.length === 1 ? "publisher account" : "publisher accounts"}</p>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-display text-lg font-semibold">Payout history</h2>
          <p className="text-sm">Payout status, method, and reference details.</p>
        </div>
        {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
        {payouts.length > 0 && listing.controls}
        {payouts.length === 0 ? (
          <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm">No payouts found.</div>
        ) : (
          <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
            <table className="table">
              <thead><tr><th>Payout</th><th>Amount</th><th>Method</th><th>Status</th><th>Reference</th><th>Submitted</th><th>Paid</th></tr></thead>
              <tbody>{listing.pageItems.map((payout) => <tr key={payout.id}>
                <td className="font-mono text-xs">#{payout.id}</td>
                <td className="font-medium">{formatINR(Number(payout.amount))}</td>
                <td>{payout.payment_method?.replace(/_/g, " ") || "—"}</td>
                <td><span className={`badge ${statusStyle[payout.status]}`}>{payout.status}</span></td>
                <td className="font-mono text-xs">{payout.reference || "—"}</td>
                <td>{new Date(payout.created_at).toLocaleDateString()}</td>
                <td>{payout.paid_at ? new Date(payout.paid_at).toLocaleDateString() : "—"}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  </Layout>;
}
