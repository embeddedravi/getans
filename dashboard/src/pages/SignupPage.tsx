import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

type Role = "advertiser" | "publisher";

export function SignupPage() {
    const [role, setRole] = useState<Role>("advertiser");
    const [organization, setOrganization] = useState("");
    const [mobile, setMobile] = useState("");
    const [password, setPassword] = useState("");
    const [email, setEmail] = useState("");
    const [siteUrl, setSiteUrl] = useState("");
    const [payoutEmail, setPayoutEmail] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const navigate = useNavigate();

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError(null);
        setBusy(true);
        try {
            await api.signup({
                role,
                organization_name: organization,
                mobile,
                password,
                email: email || null,
                ...(role === "publisher"
                    ? { site_url: siteUrl, payout_email: payoutEmail }
                    : { billing_email: email || null }),
            });
            navigate("/verify");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not create account");
        } finally {
            setBusy(false);
        }
    }

    const input = "input input-bordered w-full bg-base-100";
    return (
        <div className="min-h-screen flex items-center justify-center bg-base-100 p-4">
            <div className="w-full max-w-sm border border-base-300 bg-base-200 rounded p-8">
                <h1 className="font-display text-2xl font-semibold mb-1">Create an account</h1>
                <p className="text-sm text-neutral-content mb-6">Advertise or monetise your site.</p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm mb-1" htmlFor="role">I am a</label>
                        <select id="role" value={role} onChange={(e) => setRole(e.target.value as Role)}
                            className="select select-bordered w-full bg-base-100">
                            <option value="advertiser">Advertiser</option>
                            <option value="publisher">Publisher</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm mb-1" htmlFor="org">
                            {role === "publisher" ? "Site / company name" : "Company name"}
                        </label>
                        <input id="org" required minLength={2} value={organization}
                            onChange={(e) => setOrganization(e.target.value)} className={input} />
                    </div>
                    <div>
                        <label className="block text-sm mb-1" htmlFor="mobile">Mobile number</label>
                        <input id="mobile" type="tel" inputMode="numeric" required maxLength={17}
                            placeholder="98765 43210" value={mobile}
                            onChange={(e) => setMobile(e.target.value)} className={input} />
                    </div>
                    <div>
                        <label className="block text-sm mb-1" htmlFor="email">
                            {role === "advertiser" ? "Billing email" : "Email (optional)"}
                        </label>
                        <input id="email" type="email" required={role === "advertiser"} value={email}
                            onChange={(e) => setEmail(e.target.value)} className={input} />
                    </div>
                    {role === "publisher" && (
                        <>
                            <div>
                                <label className="block text-sm mb-1" htmlFor="site">Site URL</label>
                                <input id="site" type="url" required placeholder="https://example.com"
                                    value={siteUrl} onChange={(e) => setSiteUrl(e.target.value)} className={input} />
                            </div>
                            <div>
                                <label className="block text-sm mb-1" htmlFor="payout">Payout email</label>
                                <input id="payout" type="email" required value={payoutEmail}
                                    onChange={(e) => setPayoutEmail(e.target.value)} className={input} />
                            </div>
                        </>
                    )}
                    <div>
                        <label className="block text-sm mb-1" htmlFor="password">Password</label>
                        <input id="password" type="password" required minLength={8} maxLength={72}
                            value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
                    </div>

                    {error && (
                        <div role="alert" className="alert alert-error py-2 text-sm"><span>{error}</span></div>
                    )}
                    <button type="submit" disabled={busy} className="btn btn-primary w-full">
                        {busy ? "Creating..." : "Create account"}
                    </button>
                </form>

                <p className="text-sm text-neutral-content mt-5">
                    Already registered? <Link to="/login" className="link text-primary">Sign in</Link>
                </p>
            </div>
        </div>
    );
}