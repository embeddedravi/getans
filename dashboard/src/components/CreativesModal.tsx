import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Campaign, Creative, MediaAsset, PollResults, ReviewStatus } from "../types";

const REVIEW_BADGE: Record<ReviewStatus, string> = {
    pending: "badge-warning",
    approved: "badge-success",
    rejected: "badge-error",
};

export function CreativesModal({
    campaign,
    isAdmin,
    onClose,
}: {
    campaign: Campaign;
    isAdmin: boolean;
    onClose: () => void;
}) {
    const [creatives, setCreatives] = useState<Creative[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Image creative form state
    const [name, setName] = useState("");
    const [assetUrl, setAssetUrl] = useState("");
    const [clickUrl, setClickUrl] = useState("");
    const [width, setWidth] = useState("300");
    const [height, setHeight] = useState("250");

    // Media library form state
    const [media, setMedia] = useState<MediaAsset[]>([]);
    const [mediaId, setMediaId] = useState("");
    const [mediaClickUrl, setMediaClickUrl] = useState("");

    // Poll ad form state
    const [createMode, setCreateMode] = useState<"image" | "media" | "poll">("image");
    const [pollName, setPollName] = useState("");
    const [pollQuestion, setPollQuestion] = useState("");
    const [pollOpt1, setPollOpt1] = useState("");
    const [pollOpt2, setPollOpt2] = useState("");
    const [pollOpt3, setPollOpt3] = useState("");
    const [pollOpt4, setPollOpt4] = useState("");
    const [pollClickUrl, setPollClickUrl] = useState("");
    const [pollWidth, setPollWidth] = useState("300");
    const [pollHeight, setPollHeight] = useState("250");
    const [pollAssetUrl, setPollAssetUrl] = useState("");
    const [selectedResults, setSelectedResults] = useState<PollResults | null>(null);
    const [loadingResults, setLoadingResults] = useState(false);

    useEffect(() => { api.listMedia().then(setMedia).catch(() => { }); }, []);

    function refresh() {
        setLoading(true);
        api
            .listCreativesForCampaign(campaign.id)
            .then((d) => setCreatives(d as Creative[]))
            .catch((e) => setError(e.message))
            .finally(() => setLoading(false));
    }
    useEffect(refresh, [campaign.id]);

    async function run(fn: () => Promise<unknown>) {
        setError(null);
        try {
            await fn();
            refresh();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Action failed");
        }
    }

    async function handleCreateFromMedia(e: FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        await run(async () => {
            await api.createCreative({
                campaign_id: campaign.id,
                media_id: Number(mediaId),
                click_url: mediaClickUrl,
            });
            setMediaId(""); setMediaClickUrl("");
        });
        setSubmitting(false);
    }

    async function handleCreate(e: FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        await run(async () => {
            await api.createCreative({
                campaign_id: campaign.id,
                name: name || null,
                asset_url: assetUrl,
                click_url: clickUrl,
                width: Number(width),
                height: Number(height),
                format: "image",
            });
            setName("");
            setAssetUrl("");
            setClickUrl("");
        });
        setSubmitting(false);
    }

    async function handleCreatePoll(e: FormEvent) {
        e.preventDefault();
        if (!pollQuestion.trim()) {
            setError("Poll question is required.");
            return;
        }
        if (!pollOpt1.trim() || !pollOpt2.trim() || !pollOpt3.trim() || !pollOpt4.trim()) {
            setError("All 4 poll options are required.");
            return;
        }
        setSubmitting(true);
        await run(async () => {
            await api.createCreative({
                campaign_id: campaign.id,
                name: pollName || null,
                format: "poll",
                poll_question: pollQuestion.trim(),
                poll_options: [pollOpt1.trim(), pollOpt2.trim(), pollOpt3.trim(), pollOpt4.trim()],
                click_url: pollClickUrl,
                width: Number(pollWidth) || 300,
                height: Number(pollHeight) || 250,
                asset_url: pollAssetUrl.trim() || undefined,
            });
            setPollName("");
            setPollQuestion("");
            setPollOpt1("");
            setPollOpt2("");
            setPollOpt3("");
            setPollOpt4("");
            setPollClickUrl("");
            setPollAssetUrl("");
        });
        setSubmitting(false);
    }

    async function viewPollResults(c: Creative) {
        setLoadingResults(true);
        try {
            const res = await api.getPollResults(c.id);
            setSelectedResults(res);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to load poll results");
        } finally {
            setLoadingResults(false);
        }
    }

    function reject(c: Creative) {
        const reason = prompt("Reason for rejection?");
        if (reason) run(() => api.reviewCreative(c.id, "rejected", reason));
    }

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded border border-base-300 bg-base-200 p-4 sm:p-6">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h2 className="font-display text-lg font-semibold">Creatives</h2>
                        <p className="text-xs ">{campaign.name}</p>
                    </div>
                    <button onClick={onClose} className="btn btn-ghost btn-sm">Close</button>
                </div>

                {error && (
                    <div role="alert" className="alert alert-error py-2 text-sm mb-3">
                        <span>{error}</span>
                    </div>
                )}

                <div className="mb-5 overflow-x-auto rounded border border-base-300">
                    <table className="table">
                        <thead>
                            <tr className="text-xs  border-b border-base-300">
                                <th>Preview</th>
                                <th>Details</th>
                                <th>Review</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan={4} className="text-center text-sm  py-6">Loading...</td></tr>
                            ) : creatives.length === 0 ? (
                                <tr><td colSpan={4} className="text-center text-sm  py-6">
                                    No creatives yet. This campaign can't serve until it has an approved one.
                                </td></tr>
                            ) : (
                                creatives.map((c) => {
                                    const isPoll = c.format === "poll";
                                    const pollAttrs = c.custom_attributes || {};
                                    return (
                                        <tr key={c.id} className="border-b border-base-300 last:border-0 align-top">
                                            <td>
                                                {isPoll ? (
                                                    <div className="h-16 w-24 bg-indigo-950/40 border border-indigo-500/30 rounded p-1 flex flex-col justify-between text-left overflow-hidden">
                                                        <div className="flex items-center justify-between">
                                                            <span className="badge badge-primary badge-xs text-[9px] font-bold">POLL</span>
                                                            <span className="text-[9px] opacity-60">4 opts</span>
                                                        </div>
                                                        <div className="text-[10px] font-medium text-white truncate">
                                                            {pollAttrs.poll_question || "Poll"}
                                                        </div>
                                                        <button
                                                            type="button"
                                                            onClick={() => viewPollResults(c)}
                                                            className="btn btn-xs btn-outline btn-primary text-[9px] h-5 min-h-0 py-0"
                                                        >
                                                            Results
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <img src={c.asset_url} alt={c.name ?? "creative"} className="max-h-16 max-w-[96px] object-contain bg-base-100 rounded" />
                                                )}
                                            </td>
                                            <td className="text-xs">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="font-medium text-sm">{c.name || `Creative #${c.id}`}</span>
                                                    {isPoll && <span className="badge badge-xs badge-secondary">Poll Ad</span>}
                                                </div>
                                                <div className="tabular ">{c.width}×{c.height}</div>
                                                {isPoll && pollAttrs.poll_question && (
                                                    <div className="mt-1 text-xs opacity-80">
                                                        <div className="font-semibold text-primary">Q: {pollAttrs.poll_question}</div>
                                                        {Array.isArray(pollAttrs.poll_options) && (
                                                            <div className="text-[11px] opacity-70 mt-0.5">
                                                                {pollAttrs.poll_options.map((opt: string, i: number) => (
                                                                    <span key={i} className="mr-2 inline-block">• {opt}</span>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                                <a href={c.click_url} target="_blank" rel="noopener noreferrer" className="link truncate block max-w-[200px] mt-0.5">
                                                    {c.click_url}
                                                </a>
                                            </td>
                                            <td>
                                                <span className={`badge badge-sm ${REVIEW_BADGE[c.review_status]}`}>{c.review_status}</span>
                                                {c.rejection_reason && (
                                                    <div className="text-xs text-error mt-1 max-w-[160px]">{c.rejection_reason}</div>
                                                )}
                                                <button
                                                    onClick={() => run(() => api.updateCreative(c.id, { is_active: !c.is_active }))}
                                                    className={`badge badge-sm ml-1 cursor-pointer ${c.is_active ? "badge-success" : "badge-ghost"}`}
                                                    title="Toggle active"
                                                >
                                                    {c.is_active ? "On" : "Off"}
                                                </button>
                                            </td>
                                            <td className="text-right whitespace-nowrap">
                                                {isAdmin && c.review_status !== "approved" && (
                                                    <button className="btn btn-ghost btn-xs text-success" onClick={() => run(() => api.reviewCreative(c.id, "approved"))}>
                                                        Approve
                                                    </button>
                                                )}
                                                {isAdmin && c.review_status !== "rejected" && (
                                                    <button className="btn btn-ghost btn-xs text-warning" onClick={() => reject(c)}>
                                                        Reject
                                                    </button>
                                                )}
                                                <button
                                                    className="btn btn-ghost btn-xs text-error"
                                                    onClick={() => {
                                                        if (confirm("Delete this creative?")) run(() => api.deleteCreative(c.id));
                                                    }}
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Poll Results Modal */}
                {selectedResults && (
                    <div className="mb-5 p-4 rounded-lg bg-base-300 border border-primary/30">
                        <div className="flex justify-between items-center mb-2">
                            <h4 className="font-semibold text-sm flex items-center gap-2">
                                <span className="badge badge-primary badge-xs">POLL STATS</span>
                                {selectedResults.question}
                            </h4>
                            <button
                                onClick={() => setSelectedResults(null)}
                                className="btn btn-ghost btn-xs"
                            >
                                ✕ Close
                            </button>
                        </div>
                        <p className="text-xs opacity-70 mb-3">Total votes: {selectedResults.total_votes}</p>
                        <div className="space-y-2">
                            {selectedResults.options.map((opt, i) => {
                                const pct = selectedResults.percentages[i] || 0;
                                const cnt = selectedResults.counts[i] || 0;
                                return (
                                    <div key={i} className="text-xs">
                                        <div className="flex justify-between mb-1">
                                            <span><strong>{String.fromCharCode(65 + i)}.</strong> {opt}</span>
                                            <span>{cnt} votes ({pct}%)</span>
                                        </div>
                                        <div className="w-full bg-base-100 rounded-full h-2.5 overflow-hidden">
                                            <div
                                                className="bg-indigo-500 h-2.5 rounded-full transition-all duration-500"
                                                style={{ width: `${pct}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Mode Switcher Tabs */}
                <div className="flex gap-2 border-b border-base-300 pb-2 mb-4">
                    <button
                        type="button"
                        onClick={() => setCreateMode("image")}
                        className={`btn btn-sm ${createMode === "image" ? "btn-primary" : "btn-ghost"}`}
                    >
                        Image Creative
                    </button>
                    <button
                        type="button"
                        onClick={() => setCreateMode("media")}
                        className={`btn btn-sm ${createMode === "media" ? "btn-primary" : "btn-ghost"}`}
                    >
                        Media Library
                    </button>
                    <button
                        type="button"
                        onClick={() => setCreateMode("poll")}
                        className={`btn btn-sm ${createMode === "poll" ? "btn-secondary" : "btn-ghost"} flex items-center gap-1.5`}
                    >
                        <span>🗳️ Poll Ad</span>
                        <span className="badge badge-xs badge-neutral">1Q + 4 Options</span>
                    </button>
                </div>

                {/* Poll Ad Creation Form */}
                {createMode === "poll" && (
                    <form onSubmit={handleCreatePoll} className="space-y-4 mb-6 p-4 rounded-lg border border-secondary/30 bg-base-100">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-sm font-semibold text-secondary flex items-center gap-2">
                                    Create Interactive Poll Ad
                                </h3>
                                <p className="text-xs opacity-70">
                                    Engage visitors with 1 question and 4 interactive choices. Tracks live votes and click-throughs.
                                </p>
                            </div>
                            <span className="badge badge-secondary badge-sm">Interactive Format</span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-3">
                                <div>
                                    <label className="block text-xs font-medium mb-1">Creative Name (optional)</label>
                                    <input
                                        value={pollName}
                                        onChange={(e) => setPollName(e.target.value)}
                                        placeholder="e.g. Mobile OS Preference Poll"
                                        className="input input-bordered input-sm w-full bg-base-200"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-medium mb-1">
                                        Poll Question <span className="text-error">*</span>
                                    </label>
                                    <input
                                        required
                                        value={pollQuestion}
                                        onChange={(e) => setPollQuestion(e.target.value)}
                                        placeholder="e.g. Which programming language do you use most?"
                                        className="input input-bordered input-sm w-full bg-base-200"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="block text-xs font-medium">
                                        4 Options <span className="text-error">*</span>
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="flex items-center gap-1.5">
                                            <span className="badge badge-sm badge-neutral">A</span>
                                            <input
                                                required
                                                value={pollOpt1}
                                                onChange={(e) => setPollOpt1(e.target.value)}
                                                placeholder="Option 1"
                                                className="input input-bordered input-sm w-full bg-base-200"
                                            />
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <span className="badge badge-sm badge-neutral">B</span>
                                            <input
                                                required
                                                value={pollOpt2}
                                                onChange={(e) => setPollOpt2(e.target.value)}
                                                placeholder="Option 2"
                                                className="input input-bordered input-sm w-full bg-base-200"
                                            />
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <span className="badge badge-sm badge-neutral">C</span>
                                            <input
                                                required
                                                value={pollOpt3}
                                                onChange={(e) => setPollOpt3(e.target.value)}
                                                placeholder="Option 3"
                                                className="input input-bordered input-sm w-full bg-base-200"
                                            />
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <span className="badge badge-sm badge-neutral">D</span>
                                            <input
                                                required
                                                value={pollOpt4}
                                                onChange={(e) => setPollOpt4(e.target.value)}
                                                placeholder="Option 4"
                                                className="input input-bordered input-sm w-full bg-base-200"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-medium mb-1">
                                        Click-through URL <span className="text-error">*</span>
                                    </label>
                                    <input
                                        required
                                        type="url"
                                        value={pollClickUrl}
                                        onChange={(e) => setPollClickUrl(e.target.value)}
                                        placeholder="https://yourbrand.example.com"
                                        className="input input-bordered input-sm w-full bg-base-200"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Width (px)</label>
                                        <input
                                            required
                                            type="number"
                                            min={100}
                                            value={pollWidth}
                                            onChange={(e) => setPollWidth(e.target.value)}
                                            placeholder="300"
                                            className="input input-bordered input-sm w-full bg-base-200"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Height (px)</label>
                                        <input
                                            required
                                            type="number"
                                            min={100}
                                            value={pollHeight}
                                            onChange={(e) => setPollHeight(e.target.value)}
                                            placeholder="250"
                                            className="input input-bordered input-sm w-full bg-base-200"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-medium mb-1">Header / Logo URL (optional)</label>
                                    <input
                                        type="url"
                                        value={pollAssetUrl}
                                        onChange={(e) => setPollAssetUrl(e.target.value)}
                                        placeholder="https://yourbrand.example.com/logo.png"
                                        className="input input-bordered input-sm w-full bg-base-200"
                                    />
                                </div>
                            </div>

                            {/* Live Interactive Preview */}
                            <div>
                                <label className="block text-xs font-medium mb-1 opacity-70">Live Ad Preview</label>
                                <div
                                    className="p-3 rounded-lg border border-base-300 shadow-md flex flex-col justify-between"
                                    style={{
                                        background: "linear-gradient(145deg, #18181b 0%, #09090b 100%)",
                                        color: "#f4f4f5",
                                        minHeight: "230px",
                                    }}
                                >
                                    <div>
                                        <div className="flex justify-between items-center mb-2 text-[10px]">
                                            <span className="bg-indigo-600 text-white font-bold px-1.5 py-0.5 rounded-full">POLL</span>
                                            <span className="text-zinc-400">Sponsored ↗</span>
                                        </div>
                                        <h4 className="font-semibold text-xs leading-snug mb-3 text-white">
                                            {pollQuestion || "Your question will appear here..."}
                                        </h4>
                                        <div className="space-y-1.5">
                                            {[pollOpt1, pollOpt2, pollOpt3, pollOpt4].map((opt, i) => (
                                                <div
                                                    key={i}
                                                    className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-zinc-800/60 border border-zinc-700/50 text-[11px] text-zinc-200"
                                                >
                                                    <span className="w-4 h-4 rounded-full bg-zinc-700 flex items-center justify-center text-[9px] font-bold">
                                                        {String.fromCharCode(65 + i)}
                                                    </span>
                                                    <span className="truncate">{opt || `Option ${i + 1}`}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="flex justify-between items-center text-[10px] text-zinc-500 mt-2 pt-1 border-t border-zinc-800">
                                        <span>0 votes</span>
                                        <span className="text-indigo-400 font-medium">Learn More →</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end pt-2 border-t border-base-300">
                            <button
                                type="submit"
                                disabled={submitting}
                                className="btn btn-secondary btn-sm"
                            >
                                {submitting ? "Creating Poll..." : "Create Poll Ad"}
                            </button>
                        </div>
                    </form>
                )}

                {/* Image Creative Form */}
                {createMode === "image" && (
                    <form onSubmit={handleCreate} className="space-y-3">
                        <h3 className="text-sm font-medium">Add image creative</h3>
                        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name (optional)" className="input input-bordered input-sm w-full bg-base-100" />
                        <input required type="url" value={assetUrl} onChange={(e) => setAssetUrl(e.target.value)} placeholder="Image URL" className="input input-bordered input-sm w-full bg-base-100" />
                        <input required type="url" value={clickUrl} onChange={(e) => setClickUrl(e.target.value)} placeholder="Click-through URL" className="input input-bordered input-sm w-full bg-base-100" />
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <input required type="number" min={1} value={width} onChange={(e) => setWidth(e.target.value)} placeholder="Width" className="input input-bordered input-sm bg-base-100" />
                            <input required type="number" min={1} value={height} onChange={(e) => setHeight(e.target.value)} placeholder="Height" className="input input-bordered input-sm bg-base-100" />
                        </div>
                        <p className="text-xs ">
                            Width and height must exactly match an ad slot's dimensions for this creative to be selected.
                        </p>
                        <div className="flex justify-end">
                            <button type="submit" disabled={submitting} className="btn btn-primary btn-sm">
                                {submitting ? "Adding..." : "Add creative"}
                            </button>
                        </div>
                    </form>
                )}

                {/* Media Library Form */}
                {createMode === "media" && (
                    <form onSubmit={handleCreateFromMedia} className="space-y-3 mb-6">
                        <h3 className="text-sm font-medium">Create from media library</h3>
                        <select required value={mediaId} onChange={(e) => setMediaId(e.target.value)}
                            className="select select-bordered select-sm w-full bg-base-100">
                            <option value="">Choose an image or video…</option>
                            {media.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.original_filename} ({m.kind}, {m.width}×{m.height})
                                </option>
                            ))}
                        </select>
                        <input required type="url" value={mediaClickUrl} onChange={(e) => setMediaClickUrl(e.target.value)}
                            placeholder="Click-through URL" className="input input-bordered input-sm w-full bg-base-100" />
                        <div className="flex justify-end">
                            <button type="submit" disabled={submitting} className="btn btn-primary btn-sm">Create ad</button>
                        </div>
                    </form>
                )}

            </div>
        </div>
    );
}
