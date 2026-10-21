import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { CaptchaChallenge } from "../components/CaptchaChallenge";

export function LoginPage() {
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [captchaChallenge, setCaptchaChallenge] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [captchaVersion, setCaptchaVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    localStorage.getItem("dashboard-theme") === "dark" ? "dark" : "light",
  );
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dashboard-theme", theme);
  }, [theme]);

  const needsVerification = error?.toLowerCase().includes("not verified") ?? false;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.login(mobile, password, captchaChallenge, captchaAnswer);
      localStorage.setItem("access_token", access_token);
      navigate("/home");
    } catch (err) {
      setCaptchaChallenge("");
      setCaptchaAnswer("");
      setCaptchaVersion((version) => version + 1);
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative h-screen flex items-center justify-center bg-base-100">
      <button
        type="button"
        className="btn btn-ghost btn-square btn-sm absolute right-4 top-4"
        aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
        title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
        onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      >
        {theme === "light" ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        )}
      </button>
      <div className="w-full max-w-sm border border-base-300 bg-base-200 rounded p-8">
        <Link to="/" className="font-display text-2xl font-semibold mb-1 inline-block hover:text-primary">GetANS</Link>
        <p className="text-sm  mb-6">Sign in to manage campaigns</p>

        <form onSubmit={handleSubmit} className="space-y-4">
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

          <div>
            <label className="block text-sm mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input input-bordered w-full bg-base-100"
            />
            <div className="text-right mt-1">
              <Link to="/forgot-password" className="text-xs link text-primary">
                Forgot password?
              </Link>
            </div>
          </div>

          <CaptchaChallenge key={captchaVersion} onChallenge={setCaptchaChallenge} onAnswer={setCaptchaAnswer} />

          {error && (
            <div role="alert" className="alert alert-error py-2 text-sm">
              <span>{error}</span>
            </div>
          )}

          <button type="submit" disabled={loading} className="btn btn-primary w-full">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-sm  mt-5">
          {needsVerification ? "Your number isn't verified yet. " : "First time signing in? "}
          <Link to="/verify" className="link text-primary">
            Verify your mobile number
          </Link>
        </p>
        <p className="text-sm  mt-5">
          Don't have an account?{" "}
          <Link to="/signup" className="link text-primary">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
