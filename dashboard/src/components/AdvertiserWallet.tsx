import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import type { AdvertiserWallet as Wallet, RazorpayTopUpOrder } from "../types";

interface CheckoutSuccess {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface CheckoutOptions {
  key: string;
  amount: number;
  currency: "INR";
  name: string;
  description: string;
  order_id: string;
  prefill: { email: string };
  handler: (response: CheckoutSuccess) => void | Promise<void>;
  modal: { ondismiss: () => void };
  theme: { color: string };
}

interface CheckoutInstance {
  open: () => void;
  on: (event: string, callback: (response: { error?: { description?: string } }) => void) => void;
}

declare global {
  interface Window {
    Razorpay?: new (options: CheckoutOptions) => CheckoutInstance;
  }
}

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("#razorpay-checkout-js");
    const script = existing || document.createElement("script");
    script.id = "razorpay-checkout-js";
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Razorpay Checkout"));
    if (!existing) document.body.appendChild(script);
  });
}

function formatINR(amount: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(amount);
}

export function AdvertiserWallet({
  balance,
  creditLimit,
  onBalanceChange,
}: {
  balance: number;
  creditLimit: number;
  onBalanceChange: (wallet: Wallet) => void;
}) {
  const [amount, setAmount] = useState("1000");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function startPayment(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const order: RazorpayTopUpOrder = await api.createAdvertiserTopUpOrder(Number(amount));
      await loadCheckout();
      if (!window.Razorpay) throw new Error("Razorpay Checkout is unavailable");

      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: "INR",
        name: order.advertiser_name,
        description: "Add funds to your advertiser wallet",
        order_id: order.order_id,
        prefill: { email: order.billing_email },
        handler: async (response) => {
          try {
            const wallet = await api.verifyAdvertiserTopUp(response);
            onBalanceChange(wallet);
            setMessage(`${formatINR(Number(amount))} added to your wallet.`);
          } catch (verificationError) {
            setError(verificationError instanceof Error
              ? `${verificationError.message}. If your payment was captured, your wallet will update after confirmation.`
              : "Payment confirmation is pending. Your wallet will update after verification.");
          } finally {
            setBusy(false);
          }
        },
        modal: { ondismiss: () => setBusy(false) },
        theme: { color: "#5B8DEF" },
      });
      checkout.on("payment.failed", (response) => {
        setError(response.error?.description || "Payment failed. Please try again.");
        setBusy(false);
      });
      checkout.open();
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "Could not start payment");
      setBusy(false);
    }
  }

  return (
    <section className="rounded border border-base-300 bg-base-200 p-5">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-primary">INR wallet</p>
          <h2 className="mt-2 font-display text-xl font-semibold">{formatINR(balance)}</h2>
          <p className="mt-1 text-sm text-neutral-content">Available balance · Credit limit {formatINR(creditLimit)}</p>
        </div>
        <form onSubmit={startPayment} className="flex w-full max-w-sm flex-col gap-2 sm:flex-row sm:items-end">
          <label className="flex-1">
            <span className="mb-1 block text-xs text-neutral-content">Add funds (₹)</span>
            <input
              aria-label="Top-up amount in rupees"
              type="number"
              min="1"
              max="500000"
              step="0.01"
              required
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
          <button type="submit" disabled={busy} className="btn btn-primary btn-sm">
            {busy ? "Waiting for payment…" : "Add funds"}
          </button>
        </form>
      </div>
      {message && <p role="status" className="mt-3 text-sm text-success">{message}</p>}
      {error && <p role="alert" className="mt-3 text-sm text-error">{error}</p>}
    </section>
  );
}
