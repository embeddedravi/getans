import { useEffect, useState } from "react";
import { getDashboardSocket } from "../lib/socket";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
  const [connected, setConnected] = useState(false);

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
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-base-300 px-3 sm:h-16 sm:px-6">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <label
          htmlFor="dashboard-drawer-toggle"
          className="btn btn-ghost btn-square btn-sm lg:hidden"
          aria-label="Open navigation"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </label>
        <h1 className="truncate font-display text-lg font-semibold sm:text-xl">{title}</h1>
      </div>

      <div className="flex shrink-0 items-center gap-2 text-xs sm:text-sm">
        <span
          className={`h-2 w-2 rounded-full ${
            connected ? "bg-warning live-dot" : "bg-neutral-content/40"
          }`}
        />
        <span className="tabular text-neutral-content">
          {connected ? "Live" : "Disconnected"}
        </span>
      </div>
    </header>
  );
}
