import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { AdvertiserWallet } from "../components/AdvertiserWallet";
import { Layout } from "../components/Layout";
import { useListingControls } from "../components/ListingControls";
import { api } from "../lib/api";
import type { AdvertiserTopUp, AdvertiserWallet as Wallet } from "../types";

function formatINR(amount: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(amount);
}

export function AdvertiserWalletPage() {
  const [role, setRole] = useState<string | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [transactions, setTransactions] = useState<AdvertiserTopUp[]>([]);
  const [error, setError] = useState("");
  const listing = useListingControls(
    transactions,
    (transaction) => `${transaction.id} ${transaction.amount} ${transaction.status} ${transaction.order_id} ${transaction.payment_id || ""}`,
    (transaction) => transaction.status,
    [{ value: "paid", label: "Paid" }, { value: "created", label: "Created" }],
  );

  const refreshHistory = useCallback(async () => {
    try {
      setTransactions(await api.advertiserTopUpHistory());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load transaction history");
    }
  }, []);

  useEffect(() => {
    api.me().then(async (user) => {
      const accountRole = (user as { role?: string }).role || "";
      setRole(accountRole);
      if (accountRole === "advertiser") {
        const currentWallet = await api.advertiserWallet();
        setWallet(currentWallet);
        await refreshHistory();
      }
    }).catch(() => setRole(""));
  }, [refreshHistory]);

  if (role === null) return <Layout title="Wallet"><p className="text-sm">Loading wallet…</p></Layout>;
  if (role !== "advertiser") return <Navigate to="/" replace />;

  return <Layout title="Wallet">
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-widest text-primary">Advertiser account</p>
        <h2 className="mt-2 font-display text-2xl font-semibold">Wallet</h2>
        <p className="mt-1 text-sm">Manage your available funds and review wallet top-ups.</p>
      </section>

      {wallet ? <AdvertiserWallet
        balance={Number(wallet.balance)}
        creditLimit={Number(wallet.credit_limit)}
        onBalanceChange={setWallet}
        onPaymentSuccess={() => void refreshHistory()}
      /> : <p className="text-sm">Loading wallet balance…</p>}

      <section className="space-y-3">
        <div>
          <h2 className="font-display text-lg font-semibold">Transaction history</h2>
          <p className="text-sm">Wallet top-ups and their payment status.</p>
        </div>
        {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
        {transactions.length > 0 && listing.controls}
        {transactions.length === 0 ? (
          <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm">No wallet transactions yet.</div>
        ) : (
          <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
            <table className="table">
              <thead><tr><th>Transaction</th><th>Amount</th><th>Status</th><th>Order ID</th><th>Payment ID</th><th>Date</th></tr></thead>
              <tbody>{listing.pageItems.map((transaction) => <tr key={transaction.id}>
                <td className="font-mono text-xs">#{transaction.id}</td>
                <td className="font-medium">{formatINR(Number(transaction.amount))}</td>
                <td><span className={`badge ${transaction.status === "paid" ? "badge-success" : "badge-warning"}`}>{transaction.status}</span></td>
                <td className="font-mono text-xs">{transaction.order_id}</td>
                <td className="font-mono text-xs">{transaction.payment_id || "—"}</td>
                <td>{new Date(transaction.paid_at || transaction.created_at).toLocaleDateString()}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  </Layout>;
}
