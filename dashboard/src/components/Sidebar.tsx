import { NavLink, useNavigate } from "react-router-dom";

const links = [
  { to: "/", label: "Analytics", end: true },
  { to: "/campaigns", label: "Campaigns" },
  { to: "/publishers", label: "Publishers & slots" },
];

export function Sidebar() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  return (
    <aside className="w-60 shrink-0 border-r border-base-300 bg-base-200 flex flex-col">
      <div className="px-5 py-5 border-b border-base-300">
        <span className="font-display text-lg font-semibold tracking-tight">
          Ad Platform
        </span>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
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
