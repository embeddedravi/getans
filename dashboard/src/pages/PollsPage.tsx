import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { Campaign, Creative, PollResults } from "../types";

type PollRow = { campaign: Pick<Campaign, "id" | "name">; creative: Creative };

export function PollsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [rows, setRows] = useState<PollRow[]>([]);
  const [campaignId, setCampaignId] = useState("");
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState(["", "", "", ""]);
  const [clickUrl, setClickUrl] = useState("");
  const [results, setResults] = useState<PollResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [campaignList, pollList] = await Promise.all([
        api.listCampaigns() as Promise<Campaign[]>,
        api.listPollCreatives(),
      ]);
      setCampaigns(campaignList);
      setRows(pollList);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load poll ads.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    api.me().then((user) => setIsAdmin((user as { role?: string }).role === "admin")).catch(() => setIsAdmin(false));
  }, []);

  async function createPoll(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      await api.createCreative({
        campaign_id: Number(campaignId), name: name.trim() || null,
        click_url: clickUrl, format: "poll", width: 300, height: 250,
        poll_question: question.trim(), poll_options: options.map((option) => option.trim()),
      });
      setName(""); setQuestion(""); setOptions(["", "", "", ""]); setClickUrl("");
      setNotice("Poll ad created and submitted for review.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create poll ad.");
    } finally { setBusy(false); }
  }

  async function changeActive(creative: Creative) {
    setError("");
    try { await api.updateCreative(creative.id, { is_active: !creative.is_active }); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update poll ad."); }
  }

  async function removePoll(creative: Creative) {
    if (!window.confirm(`Delete “${creative.name || `Poll #${creative.id}`}”?`)) return;
    setError("");
    try { await api.deleteCreative(creative.id); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not delete poll ad."); }
  }

  async function viewResults(creative: Creative) {
    setError("");
    try { setResults(await api.getPollResults(creative.id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load results."); }
  }

  async function reviewPoll(creative: Creative, status: "approved" | "rejected") {
    const reason = status === "rejected" ? window.prompt("Reason for rejection?")?.trim() : undefined;
    if (status === "rejected" && !reason) return;
    setError("");
    try { await api.reviewCreative(creative.id, status, reason); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not review poll ad."); }
  }

  return <Layout title="Poll ads">
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">Create poll ads and manage their serving status and results.</p>
        <Link to="/campaigns" className="btn btn-ghost btn-sm">Manage campaigns</Link>
      </div>
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      {notice && <div role="status" className="alert alert-success py-2 text-sm">{notice}</div>}

      <form onSubmit={createPoll} className="grid gap-3 rounded-lg border border-base-300 bg-base-200 p-4 sm:grid-cols-2 sm:p-5">
        <div className="sm:col-span-2"><h2 className="font-display text-lg font-semibold">Create poll ad</h2><p className="mt-1 text-xs opacity-70">Poll ads use 300 × 250 dimensions by default and need approval before serving.</p></div>
        <label className="block sm:col-span-2"><span className="mb-1 block text-xs font-medium">Campaign</span>
          <select required value={campaignId} onChange={(event) => setCampaignId(event.target.value)} className="select select-bordered select-sm w-full bg-base-100">
            <option value="">Choose a campaign</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}
          </select>
        </label>
        <label className="block sm:col-span-2"><span className="mb-1 block text-xs font-medium">Name (optional)</span>
          <input value={name} onChange={(event) => setName(event.target.value)} maxLength={200} className="input input-bordered input-sm w-full bg-base-100" />
        </label>
        <label className="block sm:col-span-2"><span className="mb-1 block text-xs font-medium">Question</span>
          <input required value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={500} className="input input-bordered input-sm w-full bg-base-100" />
        </label>
        {options.map((option, index) => <label key={index} className="block"><span className="mb-1 block text-xs font-medium">Option {index + 1}</span>
          <input required value={option} onChange={(event) => setOptions((current) => current.map((value, i) => i === index ? event.target.value : value))} className="input input-bordered input-sm w-full bg-base-100" />
        </label>)}
        <label className="block sm:col-span-2"><span className="mb-1 block text-xs font-medium">Click-through URL</span>
          <input required type="url" value={clickUrl} onChange={(event) => setClickUrl(event.target.value)} className="input input-bordered input-sm w-full bg-base-100" placeholder="https://example.com" />
        </label>
        <div className="flex justify-end sm:col-span-2"><button className="btn btn-primary btn-sm" disabled={busy || campaigns.length === 0}>{busy ? "Creating…" : "Create poll ad"}</button></div>
      </form>

      <section className="space-y-3">
        <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold">Poll ads</h2><span className="text-xs opacity-70">{rows.length} total</span></div>
        <div className="overflow-x-auto rounded border border-base-300 bg-base-200"><table className="table">
          <thead><tr className="text-xs"><th>Poll</th><th>Campaign</th><th>Review</th><th>Serving</th><th>Actions</th>{isAdmin && <th>Moderation</th>}</tr></thead>
          <tbody>{loading ? <tr><td colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-sm">Loading poll ads…</td></tr>
            : rows.length === 0 ? <tr><td colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-sm">No poll ads found.</td></tr>
              : rows.map(({ campaign, creative }) => <tr key={creative.id}>
                <td><div className="font-medium">{creative.name || `Poll #${creative.id}`}</div><div className="max-w-sm truncate text-xs opacity-70">{creative.custom_attributes?.poll_question || "Poll"}</div></td>
                <td>{campaign.name}</td>
                <td><span className={`badge badge-sm ${creative.review_status === "approved" ? "badge-success" : creative.review_status === "rejected" ? "badge-error" : "badge-warning"}`}>{creative.review_status}</span></td>
                <td><span className={`badge badge-sm ${creative.is_active ? "badge-success" : "badge-ghost"}`}>{creative.is_active ? "Active" : "Paused"}</span></td>
                <td><div className="flex flex-wrap gap-1"><button className="btn btn-ghost btn-xs" onClick={() => void viewResults(creative)}>Results</button>
                  <button className="btn btn-ghost btn-xs" onClick={() => void changeActive(creative)}>{creative.is_active ? "Pause" : "Activate"}</button>
                  <button className="btn btn-ghost btn-xs text-error" onClick={() => void removePoll(creative)}>Delete</button>
                </div></td>
                {isAdmin && <td><div className="flex flex-wrap gap-1">
                  {creative.review_status !== "approved" && <button className="btn btn-success btn-xs" onClick={() => void reviewPoll(creative, "approved")}>Approve</button>}
                  {creative.review_status !== "rejected" && <button className="btn btn-warning btn-xs" onClick={() => void reviewPoll(creative, "rejected")}>Reject</button>}
                </div></td>}
              </tr>)}</tbody>
        </table></div>
      </section>
    </div>
    {results && <div className="modal modal-open" role="dialog" aria-modal="true" aria-label="Poll results">
      <div className="modal-box max-w-md"><h2 className="font-display text-lg font-semibold">Poll results</h2><p className="mt-1 text-sm">{results.question}</p><p className="mt-1 text-xs opacity-70">{results.total_votes} total votes</p>
        <div className="mt-4 space-y-3">{results.options.map((option, index) => <div key={option}><div className="mb-1 flex justify-between gap-3 text-sm"><span>{option}</span><span>{results.counts[index]} · {results.percentages[index]}%</span></div><progress className="progress progress-primary w-full" value={results.percentages[index]} max="100" /></div>)}</div>
        <div className="modal-action"><button className="btn btn-sm" onClick={() => setResults(null)}>Close</button></div>
      </div><button className="modal-backdrop" aria-label="Close poll results" onClick={() => setResults(null)} />
    </div>}
  </Layout>;
}
