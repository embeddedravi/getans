import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";

type Profile = { first_name?: string | null; last_name?: string | null; email?: string | null; mobile?: string | null; role?: string };

const roleNames: Record<string, string> = {
  admin: "Platform admin", staff: "Platform staff", publisher: "Publisher", advertiser: "Advertiser",
};

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.me().then((data) => {
      const user = data as Profile;
      setProfile(user);
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
      setEmail(user.email || "");
    }).catch((err: unknown) => setError(err instanceof Error ? err.message : "Could not load profile")).finally(() => setLoading(false));
  }, []);

  const run = async (event: FormEvent, action: () => Promise<void>) => {
    event.preventDefault(); setError(""); setMessage(""); setSaving(true);
    try { await action(); } catch (err) { setError(err instanceof Error ? err.message : "Request failed"); }
    finally { setSaving(false); }
  };

  const displayName = [profile?.first_name, profile?.last_name].filter(Boolean).join(" ") || "Your profile";
  const initials = [profile?.first_name, profile?.last_name].filter(Boolean).map((part) => part?.[0]).join("").toUpperCase() || "U";

  return <Layout title="Profile & account">
    <div className="mx-auto max-w-5xl space-y-6 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-base-300 bg-base-200 px-5 py-6 sm:px-8 sm:py-8">
        <div className="pointer-events-none absolute -right-10 -top-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary/15 font-display text-2xl font-semibold text-primary">{initials}</div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-[.18em] text-primary">Account settings</p>
            <h2 className="mt-1 truncate font-display text-2xl font-semibold tracking-tight sm:text-3xl">{displayName}</h2>
            <p className="mt-1 text-sm text-base-content/60">Update your personal information and keep your account secure.</p>
          </div>
          {profile?.role && <span className="badge badge-outline self-start sm:self-center">{roleNames[profile.role] || profile.role}</span>}
        </div>
      </section>

      {error && <div role="alert" className="alert alert-error"><span>{error}</span></div>}
      {message && <div role="status" className="alert alert-success"><span>{message}</span></div>}

      {loading ? <div className="grid gap-5 lg:grid-cols-2"><div className="skeleton h-72 rounded-2xl" /><div className="skeleton h-72 rounded-2xl" /></div> : <>
        <div className="grid items-start gap-5 lg:grid-cols-2">
          <section className="card h-full border border-base-300 bg-base-100 shadow-sm">
            <div className="card-body gap-5 p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-lg text-primary" aria-hidden="true">◎</span>
                <div><h3 className="font-display text-lg font-semibold">Personal details</h3><p className="text-sm text-base-content/60">Your name appears across your workspace.</p></div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl bg-base-200/70 p-3"><p className="text-xs font-medium uppercase tracking-wide text-base-content/50">Mobile</p><p className="mt-1 truncate text-sm font-medium">{profile?.mobile || "Not set"}</p></div>
                <div className="rounded-xl bg-base-200/70 p-3"><p className="text-xs font-medium uppercase tracking-wide text-base-content/50">Account role</p><p className="mt-1 truncate text-sm font-medium">{profile?.role ? roleNames[profile.role] || profile.role : "User"}</p></div>
              </div>
              <form className="space-y-4" onSubmit={(event) => run(event, async () => {
                const updated = await api.updateProfile({ first_name: firstName.trim() || null, last_name: lastName.trim() || null, email: email.trim() || null });
                setProfile(updated as Profile); setProfileSaved(true); setMessage("Your profile has been updated.");
              })}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="form-control gap-1"><span className="label-text text-xs font-medium">First name</span><input className="input input-bordered w-full focus:input-primary" maxLength={100} value={firstName} onChange={(e) => { setFirstName(e.target.value); setProfileSaved(false); }} /></label>
                  <label className="form-control gap-1"><span className="label-text text-xs font-medium">Last name</span><input className="input input-bordered w-full focus:input-primary" maxLength={100} value={lastName} onChange={(e) => { setLastName(e.target.value); setProfileSaved(false); }} /></label>
                </div>
                <label className="form-control gap-1"><span className="label-text text-xs font-medium">Email address</span><input className="input input-bordered w-full focus:input-primary" type="email" autoComplete="email" maxLength={191} value={email} onChange={(e) => { setEmail(e.target.value); setProfileSaved(false); }} /><span className="label-text-alt text-base-content/50">Used for account contact. If you remove it, keep a mobile number on your account.</span></label>
                <div className="flex justify-end border-t border-base-300 pt-4"><button className={`btn btn-sm min-w-28 ${profileSaved ? "btn-success" : "btn-primary"}`} type="submit" disabled={saving}>{saving ? <span className="loading loading-spinner loading-xs" /> : profileSaved ? "✓ Saved" : "Save changes"}</button></div>
              </form>
            </div>
          </section>

          <section className="card h-full border border-base-300 bg-base-100 shadow-sm">
            <div className="card-body gap-5 p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-lg text-secondary" aria-hidden="true">⌑</span>
                <div><h3 className="font-display text-lg font-semibold">Password & security</h3><p className="text-sm text-base-content/60">Choose a password you don’t use elsewhere.</p></div>
              </div>
              <form className="space-y-4" onSubmit={(event) => run(event, async () => {
                const result = await api.changePassword(currentPassword, newPassword);
                setCurrentPassword(""); setNewPassword(""); setMessage(result.message);
              })}>
                <label className="form-control gap-1"><span className="label-text text-xs font-medium">Current password</span><input className="input input-bordered w-full focus:input-primary" type="password" autoComplete="current-password" required value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /></label>
                <label className="form-control gap-1"><span className="label-text text-xs font-medium">New password</span><input className="input input-bordered w-full focus:input-primary" type="password" autoComplete="new-password" minLength={8} maxLength={72} required value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /><span className="label-text-alt text-base-content/50">At least 8 characters</span></label>
                <div className="flex justify-end border-t border-base-300 pt-4"><button className="btn btn-primary btn-sm min-w-32" type="submit" disabled={saving}>{saving ? <span className="loading loading-spinner loading-xs" /> : "Update password"}</button></div>
              </form>
            </div>
          </section>
        </div>

        <section className="rounded-2xl border border-error/30 bg-error/[.03] p-5 sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-error/10 text-lg text-error" aria-hidden="true">!</div>
            <div className="min-w-0 flex-1">
              <h3 className="font-display text-lg font-semibold text-error">Delete account</h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-base-content/65">This permanently removes your sign in account. Your publisher or advertiser workspace and its records will remain.</p>
              <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => run(event, async () => {
                if (!window.confirm("Permanently delete your account? You will be signed out.")) return;
                await api.deleteAccount(deletePassword);
                localStorage.removeItem("access_token"); navigate("/login", { replace: true });
              })}>
                <label className="form-control w-full max-w-sm gap-1"><span className="label-text text-xs font-medium">Confirm with your password</span><input className="input input-bordered w-full" type="password" autoComplete="current-password" required value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} /></label>
                <button className="btn btn-error btn-outline" type="submit" disabled={saving}>{saving ? <span className="loading loading-spinner loading-xs" /> : "Delete my account"}</button>
              </form>
            </div>
          </div>
        </section>
      </>}
    </div>
  </Layout>;
}
