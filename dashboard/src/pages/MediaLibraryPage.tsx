import { ChangeEvent, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { MediaAsset } from "../types";

const ACCEPT = "image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm";

export function MediaLibraryPage() {
    const [items, setItems] = useState<MediaAsset[]>([]);
    const [error, setError] = useState("");
    const [uploading, setUploading] = useState(false);

    const refresh = () => api.listMedia().then(setItems).catch((e) => setError(e.message));
    useEffect(() => { void refresh(); }, []);

    async function onPick(e: ChangeEvent<HTMLInputElement>) {
        const files = Array.from(e.target.files ?? []);
        e.target.value = "";
        setError("");
        setUploading(true);
        for (const file of files) {
            try {
                await api.uploadMedia(file);
            } catch (err) {
                setError(`${file.name}: ${err instanceof Error ? err.message : "Upload failed"}`);
            }
        }
        setUploading(false);
        void refresh();
    }

    async function remove(m: MediaAsset) {
        if (!window.confirm(`Delete “${m.original_filename}”?`)) return;
        try { await api.deleteMedia(m.id); void refresh(); }
        catch (err) { setError(err instanceof Error ? err.message : "Delete failed"); }
    }

    return (
        <Layout title="Media library">
            <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm">PNG, JPEG, GIF, WebP up to 5 MB · MP4, WebM up to 50 MB (30 s).</p>
                    <label className={`btn btn-primary btn-sm ${uploading ? "btn-disabled" : ""}`}>
                        {uploading ? "Uploading…" : "Upload files"}
                        <input type="file" multiple accept={ACCEPT} className="hidden" onChange={onPick} />
                    </label>
                </div>
                {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}

                {items.length === 0 ? (
                    <div className="rounded border border-base-300 bg-base-200 p-8 text-center text-sm">
                        No media yet. Upload an image or video to create your first ad.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        {items.map((m) => (
                            <div key={m.id} className="rounded border border-base-300 bg-base-200 p-3">
                                <div className="flex h-36 items-center justify-center overflow-hidden rounded bg-base-100">
                                    {m.kind === "video"
                                        ? <video src={m.url} muted controls preload="metadata" className="max-h-36 max-w-full" />
                                        : <img src={m.url} alt={m.original_filename} className="max-h-36 max-w-full object-contain" />}
                                </div>
                                <p className="mt-2 truncate text-sm font-medium">{m.original_filename}</p>
                                <p className="tabular text-xs">
                                    {m.width}×{m.height} · {(m.size_bytes / 1024 / 1024).toFixed(2)} MB
                                    {m.duration_seconds != null && ` · ${Number(m.duration_seconds).toFixed(0)}s`}
                                </p>
                                <button onClick={() => void remove(m)} className="btn btn-ghost btn-xs mt-2 text-error">Delete</button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Layout>
    );
}