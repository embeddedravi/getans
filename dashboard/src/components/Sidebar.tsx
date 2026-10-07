import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Role = "admin" | "staff" | "publisher" | "advertiser";

const roleLabels: Record<Role, string> = {
  admin: "Platform admin",
  staff: "Platform staff",
  publisher: "Publisher workspace",
  advertiser: "Advertiser workspace",
};

const roleLinks: Record<Role, { to: string; label: string; end?: boolean }[]> = {
  admin: [
    { to: "/", label: "Overview", end: true },
    { to: "/manage-advertiser", label: "Advertisers" },
    { to: "/manage-publisher", label: "Publishers" },
    { to: "/manage-campaign", label: "Campaigns" },
    { to: "/manage-slots", label: "Ad slots" },
    { to: "/live-events", label: "Live events" },
    { to: "/manage-users", label: "Users" },
    { to: "/approvals", label: "Approvals" },
    { to: "/payments", label: "Payments" },
    { to: "/payouts", label: "Payouts" },
  ],
  staff: [
    { to: "/", label: "Operations overview", end: true },
    { to: "/approvals", label: "Review queue" },
  ],
  publisher: [
    { to: "/", label: "Earnings overview", end: true },
    { to: "/publishers", label: "My sites & ad slots" },
  ],
  advertiser: [
    { to: "/", label: "Performance overview", end: true },
    { to: "/campaigns", label: "My campaigns" },
  ],
};

export function Sidebar() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role | null>(null);
  const [user, setUser] = useState<{
    first_name?: string | null;
    last_name?: string | null;
    mobile?: string | null;
    email?: string | null;
  } | null>(null);
  useEffect(() => {
    api.me().then((user) => {
      const account = user as {
        role?: Role;
        first_name?: string | null;
        last_name?: string | null;
        mobile?: string | null;
        email?: string | null;
      };
      setUser(account);
      const accountRole = account.role;
      if (accountRole && accountRole in roleLinks) setRole(accountRole);
    }).catch(() => setRole(null));
  }, []);

  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(" ")
    || user?.email
    || user?.mobile
    || "User";

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  return (
    <aside className="min-h-full w-72 max-w-[85vw] shrink-0 border-r border-base-300 bg-base-200 flex flex-col lg:w-60">
      <div className="px-5 py-5 border-b border-base-300">
        <span className="font-display text-lg font-semibold tracking-tight">
          Ad Platform
        </span>
        {role && <p className="mt-1 text-xs text-neutral-content">{roleLabels[role]}</p>}
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {(role ? roleLinks[role] : []).map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            onClick={() => {
              const drawer = document.getElementById("dashboard-drawer-toggle") as HTMLInputElement | null;
              if (drawer) drawer.checked = false;
            }}
            className={({ isActive }) =>
              `block rounded px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-base-300 text-base-content font-medium"
                  : "text-neutral-content hover:bg-base-300/60 hover:text-base-content"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-base-300 flex flex-col gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-semibold text-primary">
            {displayName.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-base-content">{displayName}</p>
            <p className="truncate text-xs text-neutral-content">{role ? roleLabels[role] : "Account"}</p>
            {user?.mobile && <p className="truncate text-xs text-neutral-content">{user.mobile}</p>}
            {user?.email && <p className="truncate text-xs text-neutral-content">{user.email}</p>}
          </div>
        </div>
        <span className="text-xs text-neutral-content">Self-hosted ad server</span>
        <button
          onClick={handleLogout}
          className="btn btn-ghost btn-xs w-full text-neutral-content hover:text-error justify-start gap-2 px-0"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign out
        </button>
      </div>
    </aside>
  );
}
