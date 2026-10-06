import { useCallback, useEffect, useState } from "react";
import { Fragment } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";

type SlotRow = AdUnit & { publisher_name: string };
type AdUnitReport = { id: number; creative_id: number | null; reason: string; created_at: string };

export function AdminSlotsPage() {
  const [slots, setSlots] = useState<SlotRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [reportsSlot, setReportsSlot] = useState<number | null>(null);
  const [reports, setReports] = useState<AdUnitReport[]>([]);
  const [reportsLoading, setReportsLoading] = useState(false);

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

  async function toggleReports(slot: SlotRow) {
    if (reportsSlot === slot.id) {
      setReportsSlot(null);
      return;
    }
    setReportsSlot(slot.id);
    setReportsLoading(true);
    try {
      setReports(await api.listAdUnitReports(slot.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load ad reports");
      setReportsSlot(null);
    } finally {
      setReportsLoading(false);
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
            {slots.map((slot) => <Fragment key={slot.id}><tr>
              <td className="font-medium">{slot.slot_name}</td>
              <td>{slot.publisher_name}</td>
              <td>{slot.format_type}</td>
              <td className="tabular">{slot.width} × {slot.height}</td>
              <td className="tabular">₹{Number(slot.reserve_price).toFixed(4)}</td>
              <td><span className={`badge badge-xs ${slot.status === "approved" ? "badge-success" : slot.status === "rejected" ? "badge-error" : "badge-warning"}`}>{slot.status.replace(/_/g, " ")}</span></td>
              <td className="tabular">{slot.id}</td>
              <td><div className="flex gap-2">
                {slot.status === "pending_review" && <>
                  <button disabled={reportsLoading} className="btn btn-ghost btn-xs" onClick={() => void toggleReports(slot)}>Reports</button>
                  <button disabled={busy === slot.id} className="btn btn-success btn-xs" onClick={() => void review(slot, "approved")}>Approve</button>
                  <button disabled={busy === slot.id} className="btn btn-error btn-outline btn-xs" onClick={() => void review(slot, "rejected")}>Reject</button>
                </>}
                {slot.status === "rejected" && <button disabled={busy === slot.id} className="btn btn-success btn-xs" onClick={() => void review(slot, "approved")}>Reapprove</button>}
                {slot.status === "approved" && <button disabled={busy === slot.id} className={`btn btn-xs ${slot.is_active ? "btn-warning" : "btn-success"}`} onClick={() => void toggleActive(slot)}>{slot.is_active ? "Deactivate" : "Activate"}</button>}
              </div></td>
            </tr>
              {reportsSlot === slot.id && <tr><td colSpan={8} className="bg-base-100">
                {reportsLoading ? "Loading reports..." : reports.length === 0 ? "No visitor reports found." : (
                  <ul className="space-y-1 text-sm">
                    {reports.map((report) => <li key={report.id}>
                      {report.reason.replace(/_/g, " ")} — creative {report.creative_id ?? "removed"} — {new Date(report.created_at).toLocaleString()}
                    </li>)}
                  </ul>
                )}
              </td></tr>}
            </Fragment>)}
            {!loading && slots.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-sm text-neutral-content">No ad slots found.</td></tr>}
            {loading && <tr><td colSpan={8} className="py-8 text-center text-sm text-neutral-content">Loading ad slots…</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>;
}
