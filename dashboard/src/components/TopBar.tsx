import { useEffect, useState } from "react";
import { getDashboardSocket } from "../lib/socket";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
  const [connected, setConnected] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    localStorage.getItem("dashboard-theme") === "dark" ? "dark" : "light",
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dashboard-theme", theme);
  }, [theme]);

  useEffect(() => {
    const socket = getDashboardSocket();
    setConnected(socket.connected);

    const onConnect = () => setConnected(true);
    const onDisconnect = () => setConnected(false);

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-base-300/80 bg-base-100/90 px-3 backdrop-blur-xl sm:px-6">
      <div className="flex min-w-0 items-center gap-2 sm:gap-4">
        <label
          htmlFor="dashboard-drawer-toggle"
          className="btn btn-ghost btn-square btn-sm rounded-xl lg:hidden"
          aria-label="Open navigation"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </label>
        <span className="hidden h-8 w-px bg-base-300 sm:block" aria-hidden="true" />
        <div className="min-w-0">
          <h1 className="truncate font-display text-base font-semibold tracking-tight sm:text-xl">{title}</h1>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div className="flex items-center gap-2 rounded-full border border-base-300 bg-base-200/70 px-2.5 py-1.5 text-[11px] sm:px-3 sm:text-xs" role="status" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-success live-dot" : "bg-base-content/30"}`} />
          <span className="hidden sm:inline">{connected ? "Live" : "Disconnected"}</span>
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-square btn-sm rounded-xl"
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
      </div>
    </header>
  );
}
