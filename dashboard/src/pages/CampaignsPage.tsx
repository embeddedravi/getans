import { FormEvent, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Campaign } from "../types";

export function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  function refresh() {
    setLoading(true);
    api
      .listCampaigns()
      .then((data) => setCampaigns(data as Campaign[]))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function toggleActive(campaign: Campaign) {
    await api.updateCampaign(campaign.id, { is_active: !campaign.is_active });
    refresh();
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this campaign? This cannot be undone.")) return;
    await api.deleteCampaign(id);
    refresh();
  }

  return (
    <Layout title="Campaigns">
      <div className="flex justify-between items-center mb-5">
        <p className="text-sm text-neutral-content">
          {campaigns.length} campaign{campaigns.length === 1 ? "" : "s"}
        </p>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          New campaign
        </button>
      </div>

      <div className="border border-base-300 bg-base-200 rounded overflow-hidden">
        <table className="table">
          <thead>
            <tr className="text-xs text-neutral-content border-b border-base-300">
              <th>Name</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Daily cap</th>
              <th>Window</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center text-sm text-neutral-content py-6">
                  Loading...
                </td>
              </tr>
            ) : campaigns.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center text-sm text-neutral-content py-6">
                  No campaigns yet. Create one to start serving ads.
                </td>
              </tr>
            ) : (
              campaigns.map((c) => (
                <tr key={c.id} className="border-b border-base-300 last:border-0">
                  <td className="font-medium">{c.name}</td>
                  <td>
                    <button
                      onClick={() => toggleActive(c)}
                      className={`badge ${c.is_active ? "badge-success" : "badge-ghost"} cursor-pointer`}
                    >
                      {c.is_active ? "Active" : "Paused"}
                    </button>
                  </td>
                  <td className="tabular">{c.priority}</td>
                  <td className="tabular">
                    {c.daily_cap != null ? `$${c.daily_cap.toFixed(2)}` : "No cap"}
                  </td>
                  <td className="tabular text-xs text-neutral-content">
                    {new Date(c.start_date).toLocaleDateString()} –{" "}
                    {new Date(c.end_date).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="btn btn-ghost btn-xs text-error"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateCampaignModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            refresh();
          }}
        />
      )}
    </Layout>
  );
}

function CreateCampaignModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [advertiserId, setAdvertiserId] = useState("");
  const [priority, setPriority] = useState("1");
  const [dailyCap, setDailyCap] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.createCampaign({
        advertiser_id: Number(advertiserId),
        name,
        priority: Number(priority),
        daily_cap: dailyCap ? Number(dailyCap) : null,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-base-200 border border-base-300 rounded p-6 w-full max-w-md">
        <h2 className="font-display text-lg font-semibold mb-4">New campaign</h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          <Field label="Campaign name">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </Field>

          <Field label="Advertiser ID">
            <input
              required
              type="number"
              value={advertiserId}
              onChange={(e) => setAdvertiserId(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Priority">
              <input
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
            <Field label="Daily cap ($, optional)">
              <input
                type="number"
                value={dailyCap}
                onChange={(e) => setDailyCap(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date">
              <input
                required
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
            <Field label="End date">
              <input
                required
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
          </div>

          {error && (
            <div role="alert" className="alert alert-error py-2 text-sm">
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn btn-ghost btn-sm">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn btn-primary btn-sm">
              {submitting ? "Creating..." : "Create campaign"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-neutral-content mb-1">{label}</span>
      {children}
    </label>
  );
}
