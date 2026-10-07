import { io, Socket } from "socket.io-client";
import type { MetricUpdate, LiveEvent } from "../types";

let socket: Socket | null = null;

export function resetDashboardSocket(): void {
  socket?.disconnect();
  socket = null;
}

function redirectToLogin(): void {
  localStorage.removeItem("access_token");
  resetDashboardSocket();
  if (window.location.pathname !== "/login") window.location.assign("/login");
}

export function getDashboardSocket(): Socket {
  if (!socket) {
    const s = io("/dashboard", {
      transports: ["websocket"],
      autoConnect: true,
      // Function form: evaluated on each connection attempt, so a new login is picked up.
      auth: (cb) => cb({ token: localStorage.getItem("access_token") }),
    });

    // Server rejected the handshake (missing/invalid/expired token, deactivated user).
    s.on("connect_error", (err) => {
      if (err.message === "unauthorized") redirectToLogin();
    });
    // The only server-initiated disconnect is token expiry.
    s.on("disconnect", (reason) => {
      if (reason === "io server disconnect") redirectToLogin();
    });

    socket = s;
  }
  return socket;
}

export function subscribeToMetrics(callback: (update: MetricUpdate) => void): () => void {
  const s = getDashboardSocket();
  s.on("metric_update", callback);
  return () => s.off("metric_update", callback);
}

export function subscribeToLiveEvents(callback: (event: LiveEvent) => void): () => void {
  const s = getDashboardSocket();
  s.on("live_event", callback);
  return () => s.off("live_event", callback);
}