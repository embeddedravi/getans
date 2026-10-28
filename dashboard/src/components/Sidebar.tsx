import { Link, NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Role = "admin" | "staff" | "publisher" | "advertiser";

const navIcons: Record<string, string> = {
  Home: "M3 10.5 12 3l9 7.5M5 9v11h14V9m-9 11v-6h4v6",
  Analytics: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  Campaigns: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10",
  "My campaigns": "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10",
  Creatives: "M4 5h16v14H4zM8 9h8m-8 4h8m-8 4h5",
  "Poll ads": "M12 3a9 9 0 100 18 9 9 0 000-18zm-3 6h.01M15 9h.01M8.5 14a4 4 0 007 0",
  Advertisers: "M17 20h5V4H2v16h5m10 0v-3a4 4 0 00-8 0v3m8 0H9m4-10a3 3 0 110-6 3 3 0 010 6z",
  Publishers: "M3 10h18M5 10V21h14V10M4 21h16M9 21v-6h6v6M3 10l2-7h14l2 7M8 10V3m8 7V3",
  "My sites": "M3 10h18M5 10V21h14V10M4 21h16M9 21v-6h6v6M3 10l2-7h14l2 7M8 10V3m8 7V3",
  "Ad slots": "M4 6h16M4 12h16M4 18h16",
  "Live events": "M13 10V3L4 14h7v7l9-11h-7z",
  Approvals: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  "Review queue": "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  Users: "M16 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2m12-13a4 4 0 11-8 0 4 4 0 018 0zm4 13v-2a4 4 0 00-3-3.87m-1-11.13a4 4 0 010 7.75",
  Payouts: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  "Earnings & payouts": "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  Support: "M8 10h.01M16 10h.01M9 16c.9.7 1.9 1 3 1s2.1-.3 3-1m6-4a9 9 0 11-18 0 9 9 0 0118 0z",
  "Support queue": "M8 10h.01M16 10h.01M9 16c.9.7 1.9 1 3 1s2.1-.3 3-1m6-4a9 9 0 11-18 0 9 9 0 0118 0z",
  "Media library": "M4 16l4-4a3 3 0 014 0l4 4m-2-2l1-1a3 3 0 014 0l2 2M4 6h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1z",
  "Publisher inventory": "M4 6h16M4 12h16M4 18h16",
  Wallet: "M3 10h18M7 15h1m4 0h1m-9 4h16a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  "Integration help": "M12 18h.01M8.2 10a4 4 0 117.6 1.3c-.9 1-1.8 1.5-1.8 2.7v.5M12 22a10 10 0 110-20 10 10 0 010 20z",
};

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
    { to: "/poll", label: "Poll ads" },
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
    { to: "/poll", label: "Poll ads" },
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
              `flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-sm transition-colors ${isActive
                ? "border-primary bg-primary/10 font-semibold text-primary"
                : "border-transparent opacity-75 hover:bg-base-300/60 hover:opacity-100"
              }`
            }
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d={navIcons[link.label] ?? navIcons.Support} />
            </svg>
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
