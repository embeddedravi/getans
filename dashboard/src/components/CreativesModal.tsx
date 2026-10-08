import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Campaign, Creative, ReviewStatus } from "../types";

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

    const [name, setName] = useState("");
    const [assetUrl, setAssetUrl] = useState("");
    const [clickUrl, setClickUrl] = useState("");
    const [width, setWidth] = useState("300");
    const [height, setHeight] = useState("250");

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
                                creatives.map((c) => (
                                    <tr key={c.id} className="border-b border-base-300 last:border-0 align-top">
                                        <td>
                                            <img src={c.asset_url} alt={c.name ?? "creative"} className="max-h-16 max-w-[96px] object-contain bg-base-100 rounded" />
                                        </td>
                                        <td className="text-xs">
                                            <div className="font-medium text-sm">{c.name || `Creative #${c.id}`}</div>
                                            <div className="tabular ">{c.width}×{c.height}</div>
                                            <a href={c.click_url} target="_blank" rel="noopener noreferrer" className="link  truncate block max-w-[200px]">
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
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

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
            </div>
        </div>
    );
}
