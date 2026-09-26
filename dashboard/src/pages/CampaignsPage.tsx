import { FormEvent, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { BiddingStrategy, Campaign, CampaignStatus } from "../types";

const STATUS_BADGE: Record<CampaignStatus, string> = {
  draft: "badge-ghost",
  scheduled: "badge-info",
  active: "badge-success",
  paused: "badge-warning",
  completed: "badge-ghost",
  exhausted: "badge-error",
  archived: "badge-ghost",
};

const BIDDING_LABEL: Record<BiddingStrategy, string> = {
  cpm: "CPM",
  cpc: "CPC",
  cpa: "CPA",
};

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
              <th>Bidding</th>
              <th>Budget</th>
              <th>Window</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center text-sm text-neutral-content py-6">
                  Loading...
                </td>
              </tr>
            ) : campaigns.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-sm text-neutral-content py-6">
                  No campaigns yet. Create one to start serving ads.
                </td>
              </tr>
            ) : (
              campaigns.map((c) => (
                <tr key={c.id} className="border-b border-base-300 last:border-0">
                  <td className="font-medium">
                    {c.name}
                    <button
                      onClick={() => toggleActive(c)}
                      className={`badge ${c.is_active ? "badge-success" : "badge-ghost"} ml-2 cursor-pointer`}
                      title="Toggle active/paused"
                    >
                      {c.is_active ? "On" : "Off"}
                    </button>
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[c.status]}`}>{c.status}</span>
                  </td>
                  <td className="tabular">{c.priority}</td>
                  <td className="tabular text-xs">
                    {BIDDING_LABEL[c.bidding_strategy]} · ${Number(c.bid_amount).toFixed(4)}
                  </td>
                  <td className="tabular text-xs">
                    <div>
                      {c.daily_cap != null ? `$${Number(c.daily_cap).toFixed(2)}/day` : "No daily cap"}
                    </div>
                    <div className="text-neutral-content">
                      {c.total_budget != null
                        ? `$${Number(c.spent_amount).toFixed(2)} / $${Number(c.total_budget).toFixed(2)} total`
                        : `$${Number(c.spent_amount).toFixed(2)} spent`}
                    </div>
                  </td>
                  <td className="tabular text-xs text-neutral-content">
                    {new Date(c.start_date).toLocaleDateString()} –{" "}
                    {c.end_date ? new Date(c.end_date).toLocaleDateString() : "Ongoing"}
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
  const [biddingStrategy, setBiddingStrategy] = useState<BiddingStrategy>("cpm");
  const [bidAmount, setBidAmount] = useState("1.00");
  const [dailyCap, setDailyCap] = useState("");
  const [totalBudget, setTotalBudget] = useState("");
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
        bidding_strategy: biddingStrategy,
        bid_amount: Number(bidAmount),
        daily_cap: dailyCap ? Number(dailyCap) : null,
        total_budget: totalBudget ? Number(totalBudget) : null,
        start_date: new Date(startDate).toISOString(),
        // end_date is optional on the backend now -- omit entirely when left blank
        // rather than sending an invalid/empty date.
        ...(endDate ? { end_date: new Date(endDate).toISOString() } : {}),
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
              minLength={2}
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
            <Field label="Priority (1-100)">
              <input
                type="number"
                min={1}
                max={100}
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
            <Field label="Bidding strategy">
              <select
                value={biddingStrategy}
                onChange={(e) => setBiddingStrategy(e.target.value as BiddingStrategy)}
                className="select select-bordered select-sm w-full bg-base-100"
              >
                <option value="cpm">CPM</option>
                <option value="cpc">CPC</option>
                <option value="cpa">CPA</option>
              </select>
            </Field>
          </div>

          <Field label="Bid amount ($)">
            <input
              type="number"
              step="0.0001"
              min="0.0001"
              required
              value={bidAmount}
              onChange={(e) => setBidAmount(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Daily cap ($, optional)">
              <input
                type="number"
                min="0"
                step="0.01"
                value={dailyCap}
                onChange={(e) => setDailyCap(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </Field>
            <Field label="Total budget ($, optional)">
              <input
                type="number"
                min="0"
                step="0.01"
                value={totalBudget}
                onChange={(e) => setTotalBudget(e.target.value)}
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
            <Field label="End date (optional)">
              <input
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
