import { useCallback, useEffect, useRef, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import { subscribeToLiveEvents } from "../lib/socket";
import type { LiveEvent } from "../types";

const MAX_ROWS = 200;
type Filter = "all" | "impression" | "click";

function merge(incoming: LiveEvent[], existing: LiveEvent[]): LiveEvent[] {
  const seen = new Set<number>();
  return [...incoming, ...existing]
    .filter((e) => (seen.has(e.id) ? false : (seen.add(e.id), true)))
    .sort((a, b) => b.id - a.id)
    .slice(0, MAX_ROWS);
}

export function LiveEventsPage() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");
  const pausedRef = useRef(false);
  pausedRef.current = paused;

  const load = useCallback(async () => {
    try {
      const recent = await api.listRecentEvents(100);
      setEvents((prev) => merge(recent, prev));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load events");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    return subscribeToLiveEvents((event) => {
      if (pausedRef.current) return;
      setEvents((prev) => merge([event], prev));
    });
  }, []);

  function togglePause() {
    // Events that arrive while paused are skipped; catch up from the DB on resume.
    if (paused) void load();
    setPaused(!paused);
  }

  const visible = filter === "all" ? events : events.filter((e) => e.type === filter);

  return (
    <Layout title="Live events">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div role="tablist" className="tabs tabs-bordered">
            {(["all", "impression", "click"] as Filter[]).map((f) => (
              <button key={f} role="tab" aria-selected={filter === f}
                onClick={() => setFilter(f)} className={`tab ${filter === f ? "tab-active" : ""}`}>
                {f === "all" ? "All" : f === "impression" ? "Impressions" : "Clicks"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs  tabular">{visible.length} shown</span>
            <button className="btn btn-ghost btn-xs" onClick={() => setEvents([])}>Clear</button>
            <button className={`btn btn-xs ${paused ? "btn-success" : "btn-warning"}`} onClick={togglePause}>
              {paused ? "Resume" : "Pause"}
            </button>
          </div>
        </div>

        {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
        {paused && <p className="text-xs text-warning">Paused. The feed is not updating.</p>}

        <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
          <table className="table">
            <thead>
              <tr className="text-xs ">
                <th>Time</th><th>Type</th><th>Campaign</th><th>Ad slot</th>
                <th>Creative</th><th>Country</th><th className="text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((e) => (
                <tr key={e.id} className="border-b border-base-300 last:border-0">
                  <td className="tabular text-xs">{new Date(e.timestamp).toLocaleTimeString()}</td>
                  <td>
                    <span className={`badge badge-sm ${e.type === "click" ? "badge-info" : e.type === "conversion" ? "badge-success" : "badge-warning"}`}>
                      {e.type.replace("_", " ")}
                    </span>
                  </td>
                  <td>{e.campaign_name ?? `#${e.campaign_id}`}</td>
                  <td>{e.slot_name ?? `#${e.ad_unit_id}`}</td>
                  <td className="tabular ">#{e.creative_id}</td>
                  <td>{e.country_code ?? "—"}</td>
                  <td className="tabular text-right">₹{e.cost.toFixed(4)}</td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr><td colSpan={7} className="py-8 text-center text-sm ">
                  No events yet. They'll appear here as ads are served.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}