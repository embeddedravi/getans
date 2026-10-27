import { Link, NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Role = "admin" | "staff" | "publisher" | "advertiser";

const roleLabels: Record<Role, string> = {
  admin: "Admin",
  staff: "Staff",
  publisher: "Publisher",
  advertiser: "Advertiser",
};

const roleLinks: Record<Role, { to: string; label: string; end?: boolean }[]> = {
  admin: [
    { to: "/home", label: "Home", end: true },
    { to: "/analytics", label: "Analytics" },
    { to: "/manage-campaign", label: "Campaigns" },
    { to: "/creatives", label: "Creatives" },
    { to: "/manage-advertiser", label: "Advertisers" },
    { to: "/manage-publisher", label: "Publishers" },
    { to: "/manage-slots", label: "Ad slots" },
    { to: "/live-events", label: "Live events" },
    { to: "/approvals", label: "Approvals" },
    { to: "/manage-users", label: "Users" },
    { to: "/payouts", label: "Payouts" },
    { to: "/support", label: "Support" },
  ],
  staff: [
    { to: "/home", label: "Home", end: true },
    { to: "/approvals", label: "Review queue" },
    { to: "/support", label: "Support queue" },
  ],
  publisher: [
    { to: "/home", label: "Home", end: true },
    { to: "/analytics", label: "Analytics" },
    { to: "/publishers", label: "My sites", end: true },
    { to: "/adslots", label: "Ad slots", end: true },
    { to: "/my-live-events", label: "Live events" },
    { to: "/earnings", label: "Earnings & payouts" },
    { to: "/help", label: "Integration help" },
    { to: "/support", label: "Support" },
  ],
  advertiser: [
    { to: "/home", label: "Home", end: true },
    { to: "/analytics", label: "Analytics" },
    { to: "/campaigns", label: "My campaigns" },
    { to: "/creatives", label: "Creatives" },
    { to: "/media", label: "Media library" },
    { to: "/publisher-inventory", label: "Publisher inventory" },
    { to: "/wallet", label: "Wallet" },
    { to: "/my-live-events", label: "Live events" },
    { to: "/support", label: "Support" },
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
    <aside className="flex min-h-full w-72 max-w-[85vw] shrink-0 flex-col border-r border-base-300 bg-base-200/95 lg:w-64">
      <div className="flex items-center gap-3 border-b border-base-300 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-content shadow-sm" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" /></svg>
        </span>
        <div className="min-w-0">
          <Link to="/" className="font-display text-lg font-semibold tracking-tight transition hover:text-primary" aria-label="GetANS public home">
            GetANS
          </Link>
          <p className="text-xs opacity-60">Ad platform</p>
        </div>
        {role && <span className="ml-auto rounded-full bg-base-300 px-2 py-1 text-[10px] font-medium leading-none">{roleLabels[role]}</span>}
      </div>

      <nav aria-label="Main navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
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
              `block rounded-lg border-l-2 px-3 py-2.5 text-sm transition-colors ${isActive
                ? "border-primary bg-primary/10 font-semibold text-primary"
                : "border-transparent opacity-75 hover:bg-base-300/60 hover:opacity-100"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-base-300 p-3">
        <div className="rounded-xl border border-base-300 bg-base-100 p-3 shadow-sm">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary ring-1 ring-primary/10">
            {displayName.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-base-content">{displayName}</p>
              <p className="mt-0.5 truncate text-xs opacity-60">{role ? roleLabels[role] : "Account"}</p>
              {(user?.email || user?.mobile) && <p className="mt-1 truncate text-[11px] opacity-55">{user.email || user.mobile}</p>}
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 border-t border-base-300 pt-3">
            <NavLink to="/profile" className={({ isActive }) => `btn btn-ghost btn-sm min-w-0 gap-2 ${isActive ? "bg-primary/10 text-primary" : ""}`}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM4 21a8 8 0 0116 0" />
              </svg>
              <span className="truncate">Profile</span>
            </NavLink>
            <button onClick={handleLogout} className="btn btn-ghost btn-sm min-w-0 gap-2 hover:bg-error/10 hover:text-error">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span className="truncate">Sign out</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
