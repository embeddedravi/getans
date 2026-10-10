import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";

export function PublisherHelpPage() {
  const [publisher, setPublisher] = useState<Publisher | null>(null);
  const [adUnits, setAdUnits] = useState<AdUnit[]>([]);
  const [isPublisher, setIsPublisher] = useState<boolean | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.me().then(async (user) => {
      if ((user as { role?: string }).role !== "publisher") {
        setIsPublisher(false);
        return;
      }
      setIsPublisher(true);
      const rows = await api.listPublishers() as Publisher[];
      const account = rows[0] ?? null;
      setPublisher(account);
      if (account) setAdUnits(await api.listAdUnits(account.id) as AdUnit[]);
    }).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Could not load publisher details");
      setIsPublisher(true);
    });
  }, []);

  if (isPublisher === null) return <Layout title="Integration help"><p>Loading…</p></Layout>;
  if (!isPublisher) return <Navigate to="/" replace />;

  const apiBase = `${window.location.origin}/api`;
  const publisherKey = publisher?.api_key ?? "YOUR_PUBLISHER_KEY";

  return <Layout title="Integration help">
    <div className="mx-auto max-w-5xl space-y-6">
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <section className="rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Connect your ad slots</h2>
        <p className="mt-2 text-sm">Use Socket.IO for real-time ad requests, or call the REST GET endpoint. Your publisher account and ad unit must be active and approved before ads can serve.</p>
        <p className="mt-4 text-xs font-medium">Publisher API key</p>
        <code className="mt-1 block break-all rounded bg-base-300 p-2 text-xs">{publisherKey}</code>
      </section>

      <section className="rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Your ad units</h2>
        {adUnits.length ? <div className="mt-3 overflow-x-auto"><table className="table table-sm">
          <thead><tr><th>Slot</th><th>Ad unit ID</th><th>Size</th><th>Status</th></tr></thead>
          <tbody>{adUnits.map((unit) => <tr key={unit.id}><td>{unit.slot_name}</td><td className="font-mono">{unit.id}</td><td>{unit.width}×{unit.height}</td><td>{unit.status.replace(/_/g, " ")}</td></tr>)}</tbody>
        </table></div> : <p className="mt-2 text-sm">No ad units yet. Create one from My sites &amp; ad slots.</p>}
      </section>

      <section className="space-y-3 rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Option 1: Socket.IO</h2>
        <p className="text-sm">Connect to <code>/delivery</code>, emit <code>request_ad</code>, then listen for <code>serve_ad</code> or <code>no_fill</code>. The publisher loader in <code>publisher-snippet/src/loader.js</code> implements rendering, impression/click tracking, and ad reporting.</p>
        <pre className="overflow-x-auto rounded bg-base-300 p-4 text-xs"><code>{`const socket = io("${window.location.origin}/delivery", { transports: ["websocket"] });
socket.emit("request_ad", {
  ad_unit_id: YOUR_AD_UNIT_ID,
  api_key: "${publisherKey}",
  context: { country: "IN", device_type: "mobile", page_keywords: ["travel"] }
});
socket.on("serve_ad", ad => {
  // Render ad.asset_url linked to ad.click_url at ad.width × ad.height.
  // Then emit "impression" with ad_unit_id, ad.creative_id, visitor_id, event_id.
});
socket.on("no_fill", ({ reason }) => console.log("No ad", reason));`}</code></pre>
        <p className="text-xs">Emit <code>click</code> with the same fields as <code>impression</code> when a visitor clicks the creative. Use a stable random visitor ID and a unique event ID for each event.</p>
      </section>

      <section className="space-y-3 rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Option 2: REST GET</h2>
        <p className="text-sm">Send the key in the <code>X-Publisher-Key</code> header, not in the URL. A match returns an <code>ad</code>; a no-fill returns <code>ad: null</code> and a reason.</p>
        <pre className="overflow-x-auto rounded bg-base-300 p-4 text-xs"><code>{`const response = await fetch("${apiBase}/delivery/ad/YOUR_AD_UNIT_ID?country=IN&device_type=mobile", {
  headers: { "X-Publisher-Key": "${publisherKey}" }
});
const result = await response.json();
if (result.ad) {
  // Render result.ad.asset_url linked to result.ad.click_url.
  // result.ad includes campaign_id, creative_id, width, height and format.
} else {
  console.log("No ad available", result.reason);
}`}</code></pre>
        <p className="text-sm">Track impressions and clicks using <code>POST {apiBase}/delivery/events/impression</code> or <code>/delivery/events/click</code> with the publisher-key header and JSON fields <code>ad_unit_id</code>, <code>creative_id</code>, <code>event_id</code>, and optional <code>visitor_id</code>.</p>
      </section>
    </div>
  </Layout>;
}
