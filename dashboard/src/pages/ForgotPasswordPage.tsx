import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export function ForgotPasswordPage() {
  const [step, setStep] = useState<"request" | "verify">("request");
  const [mobile, setMobile] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleRequestOtp(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.requestOtp(mobile);
      setSuccess(res.message || "OTP sent successfully.");
      setStep("verify");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await api.resetPassword({ mobile, code, password });
      setSuccess("Password reset successfully. Redirecting to login...");
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-screen flex items-center justify-center bg-base-100">
      <div className="w-full max-w-sm border border-base-300 bg-base-200 rounded p-8">
        <h1 className="font-display text-2xl font-semibold mb-1">Reset Password</h1>
        <p className="text-sm text-neutral-content mb-6">
          {step === "request"
            ? "Enter your mobile number to receive an OTP."
            : "Enter the OTP sent to your mobile and your new password."}
        </p>

        {step === "request" ? (
          <form onSubmit={handleRequestOtp} className="space-y-4">
            <div>
              <label className="block text-sm mb-1" htmlFor="mobile">
                Mobile number
              </label>
              <input
                id="mobile"
                type="tel"
                inputMode="numeric"
                required
                maxLength={17}
                placeholder="98765 43210"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                className="input input-bordered w-full bg-base-100"
              />
            </div>
            {error && (
              <div role="alert" className="alert alert-error py-2 text-sm">
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div role="alert" className="alert alert-success py-2 text-sm">
                <span>{success}</span>
              </div>
            )}
            <button type="submit" disabled={loading} className="btn btn-primary w-full">
              {loading ? "Sending..." : "Send OTP"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <label className="block text-sm mb-1" htmlFor="code">
                6-digit Code
              </label>
              <input
                id="code"
                type="text"
                inputMode="numeric"
                required
                maxLength={6}
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="input input-bordered w-full bg-base-100 text-center tracking-widest text-lg font-mono"
              />
            </div>
            <div>
              <label className="block text-sm mb-1" htmlFor="password">
                New Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input input-bordered w-full bg-base-100"
              />
            </div>
            {error && (
              <div role="alert" className="alert alert-error py-2 text-sm">
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div role="alert" className="alert alert-success py-2 text-sm">
                <span>{success}</span>
              </div>
            )}
            <button type="submit" disabled={loading} className="btn btn-primary w-full">
              {loading ? "Resetting..." : "Reset Password"}
            </button>
          </form>
        )}

        <div className="mt-5 text-sm text-center">
          <Link to="/login" className="link text-neutral-content hover:text-primary">
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
