import { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";

type SlotRow = AdUnit & { publisher_name: string };

export function AdminSlotsPage() {
  const [slots, setSlots] = useState<SlotRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  const loadSlots = useCallback(async () => {
    setLoading(true);
    try {
      const publishers = await api.listPublishers() as Publisher[];
      const groups = await Promise.all(publishers.map(async (publisher) => {
        const units = await api.listAdUnits(publisher.id) as AdUnit[];
        return units.map((unit) => ({ ...unit, publisher_name: publisher.name }));
      }));
      setSlots(groups.flat());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load ad slots");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadSlots(); }, [loadSlots]);

  async function review(slot: SlotRow, status: "approved" | "rejected") {
    let reason: string | undefined;
    if (status === "rejected") {
      reason = window.prompt("Enter a reason for rejecting this ad slot:")?.trim();
      if (!reason) return;
    }
    const action = status === "approved" ? (slot.status === "rejected" ? "Reapprove" : "Approve") : "Reject";
    if (!window.confirm(`${action} ad slot “${slot.slot_name}”?`)) return;
    setBusy(slot.id);
    try {
      await api.reviewAdUnit(slot.id, status, reason);
      await loadSlots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update ad slot");
    } finally {
      setBusy(null);
    }
  }

  async function toggleActive(slot: SlotRow) {
    const nextActive = !slot.is_active;
    if (!window.confirm(`${nextActive ? "Activate" : "Deactivate"} ad slot “${slot.slot_name}”?`)) return;
    setBusy(slot.id);
    try {
      await api.setAdUnitActive(slot.id, nextActive);
      await loadSlots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update ad slot");
    } finally {
      setBusy(null);
    }
  }

  return <Layout title="Manage ad slots">
    <div className="space-y-4">
      <p className="text-sm text-neutral-content">Ad inventory across all publisher accounts.</p>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
        <table className="table">
          <thead><tr><th>Slot</th><th>Publisher</th><th>Format</th><th>Dimensions</th><th>Floor CPM</th><th>Status</th><th>Slot ID</th><th>Actions</th></tr></thead>
          <tbody>
            {slots.map((slot) => <tr key={slot.id}>
              <td className="font-medium">{slot.slot_name}</td>
              <td>{slot.publisher_name}</td>
              <td>{slot.format_type}</td>
              <td className="tabular">{slot.width} × {slot.height}</td>
              <td className="tabular">₹{Number(slot.reserve_price).toFixed(4)}</td>
              <td><span className={`badge badge-xs ${slot.status === "approved" ? "badge-success" : slot.status === "rejected" ? "badge-error" : "badge-warning"}`}>{slot.status.replaceAll("_", " ")}</span></td>
              <td className="tabular">{slot.id}</td>
              <td><div className="flex gap-2">
                {slot.status === "pending_review" && <>
                  <button disabled={busy === slot.id} className="btn btn-success btn-xs" onClick={() => void review(slot, "approved")}>Approve</button>
                  <button disabled={busy === slot.id} className="btn btn-error btn-outline btn-xs" onClick={() => void review(slot, "rejected")}>Reject</button>
                </>}
                {slot.status === "rejected" && <button disabled={busy === slot.id} className="btn btn-success btn-xs" onClick={() => void review(slot, "approved")}>Reapprove</button>}
                {slot.status === "approved" && <button disabled={busy === slot.id} className={`btn btn-xs ${slot.is_active ? "btn-warning" : "btn-success"}`} onClick={() => void toggleActive(slot)}>{slot.is_active ? "Deactivate" : "Activate"}</button>}
              </div></td>
            </tr>)}
            {!loading && slots.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-sm text-neutral-content">No ad slots found.</td></tr>}
            {loading && <tr><td colSpan={8} className="py-8 text-center text-sm text-neutral-content">Loading ad slots…</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>;
}
