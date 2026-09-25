import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Analytics", end: true },
  { to: "/campaigns", label: "Campaigns" },
  { to: "/publishers", label: "Publishers & slots" },
];

export function Sidebar() {
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

      <div className="px-4 py-4 border-t border-base-300 text-xs text-neutral-content">
        Self-hosted ad server
      </div>
    </aside>
  );
}
