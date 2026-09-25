import { io, Socket } from "socket.io-client";
import type { MetricUpdate } from "../types";

let socket: Socket | null = null;

export function getDashboardSocket(): Socket {
  if (!socket) {
    socket = io("/dashboard", {
      transports: ["websocket"],
      autoConnect: true,
    });
  }
  return socket;
}

export function subscribeToMetrics(callback: (update: MetricUpdate) => void): () => void {
  const s = getDashboardSocket();
  s.on("metric_update", callback);
  return () => s.off("metric_update", callback);
}
