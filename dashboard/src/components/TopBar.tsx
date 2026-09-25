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
    <header className="h-16 border-b border-base-300 flex items-center justify-between px-6">
      <h1 className="font-display text-xl font-semibold">{title}</h1>

      <div className="flex items-center gap-2 text-sm">
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
