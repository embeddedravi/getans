import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";

type SlotRow = AdUnit & { publisher_name: string };

export function AdminSlotsPage() {
  const [slots, setSlots] = useState<SlotRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const publishers = await api.listPublishers() as Publisher[];
        const groups = await Promise.all(publishers.map(async (publisher) => {
          const units = await api.listAdUnits(publisher.id) as AdUnit[];
          return units.map((unit) => ({ ...unit, publisher_name: publisher.name }));
        }));
        if (!cancelled) { setSlots(groups.flat()); setError(""); }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load ad slots");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  return <Layout title="Manage ad slots">
    <div className="space-y-4">
      <p className="text-sm text-neutral-content">Ad inventory across all publisher accounts.</p>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr><th>Slot</th><th>Publisher</th><th>Format</th><th>Dimensions</th><th>Floor CPM</th><th>Status</th><th>Slot ID</th></tr></thead>
          <tbody>
            {slots.map((slot) => <tr key={slot.id}>
              <td className="font-medium">{slot.slot_name}</td><td>{slot.publisher_name}</td><td>{slot.format_type}</td>
              <td className="tabular">{slot.width} × {slot.height}</td><td className="tabular">₹{Number(slot.reserve_price).toFixed(4)}</td>
              <td><span className={`badge badge-xs ${slot.status === "approved" ? "badge-success" : slot.status === "rejected" ? "badge-error" : "badge-warning"}`}>{slot.status.replaceAll("_", " ")}</span></td><td className="tabular">{slot.id}</td>
            </tr>)}
            {!loading && slots.length === 0 && <tr><td colSpan={7} className="py-8 text-center text-sm text-neutral-content">No ad slots found.</td></tr>}
            {loading && <tr><td colSpan={7} className="py-8 text-center text-sm text-neutral-content">Loading ad slots…</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>;
}
