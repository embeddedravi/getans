import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

type Step = "mobile" | "code" | "done";

export function VerifyMobilePage() {
  const [step, setStep] = useState<Step>("mobile");
  const [mobile, setMobile] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Tick the resend countdown once a second.
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.requestOtp(mobile);
      setCooldown(res.resend_after);
      setCode("");
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send the code");
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.verifyOtp(mobile, code);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify the code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-screen flex items-center justify-center bg-base-100">
      <div className="w-full max-w-sm border border-base-300 bg-base-200 rounded p-8">
        <h1 className="font-display text-2xl font-semibold mb-1">Verify your mobile number</h1>

        {step === "mobile" && (
          <>
            <p className="text-sm  mb-6">
              We'll text a 6-digit code to the number on your account.
            </p>
            <form onSubmit={sendCode} className="space-y-4">
              <div>
                <label className="block text-sm mb-1" htmlFor="mobile">
                  Mobile number
                </label>
                <input
                  id="mobile"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel"
                  required
                  maxLength={17}
                  placeholder="98765 43210"
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  className="input input-bordered w-full bg-base-100"
                />
              </div>
              {error && <ErrorBox message={error} />}
              <button type="submit" disabled={busy} className="btn btn-primary w-full">
                {busy ? "Sending..." : "Send code"}
              </button>
            </form>
          </>
        )}

        {step === "code" && (
          <>
            <p className="text-sm  mb-6">
              If {mobile} has an account, a code is on its way. It expires in 5 minutes.
            </p>
            <form onSubmit={submitCode} className="space-y-4">
              <div>
                <label className="block text-sm mb-1" htmlFor="code">
                  Verification code
                </label>
                <input
                  id="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  autoFocus
                  maxLength={6}
                  pattern="\d{6}"
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  className="input input-bordered w-full bg-base-100 tabular tracking-widest text-lg"
                />
              </div>
              {error && <ErrorBox message={error} />}
              <button
                type="submit"
                disabled={busy || code.length !== 6}
                className="btn btn-primary w-full"
              >
                {busy ? "Verifying..." : "Verify number"}
              </button>
            </form>

            <div className="flex justify-between items-center mt-4 text-sm">
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setStep("mobile");
                }}
                className="link "
              >
                Use a different number
              </button>
              <button
                type="button"
                onClick={() => sendCode()}
                disabled={busy || cooldown > 0}
                className="link disabled:opacity-40 disabled:no-underline"
              >
                {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
              </button>
            </div>
          </>
        )}

        {step === "done" && (
          <>
            <p className="text-sm  mb-6">
              {mobile} is verified. You can sign in now.
            </p>
            <Link to="/login" className="btn btn-primary w-full">
              Go to sign in
            </Link>
          </>
        )}

        {step !== "done" && (
          <p className="text-sm  mt-6">
            <Link to="/login" className="link">
              Back to sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div role="alert" className="alert alert-error py-2 text-sm">
      <span>{message}</span>
    </div>
  );
}
