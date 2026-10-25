import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
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
        <p className="mt-2 text-sm">Add an ad slot, wait for account and slot approval, then embed the loader on the matching page of your site. Ads serve when an approved advertiser creative exactly matches the slot dimensions.</p>
        <p className="mt-4 text-xs font-medium">Publisher API key</p>
        <code className="mt-1 block break-all rounded bg-base-300 p-2 text-xs">{publisherKey}</code>
      </section>

      <section className="rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Your ad units</h2>
        {adUnits.length ? <div className="mt-3 overflow-x-auto"><table className="table table-sm">
          <thead><tr><th>Slot</th><th>Ad unit ID</th><th>Format</th><th>Creative size</th><th>Status</th></tr></thead>
          <tbody>{adUnits.map((unit) => <tr key={unit.id}><td>{unit.slot_name}</td><td className="font-mono">{unit.id}</td><td>{unit.format_type}</td><td>{unit.width}×{unit.height} px</td><td>{unit.status.replace(/_/g, " ")}{!unit.is_active ? " · inactive" : ""}</td></tr>)}</tbody>
        </table></div> : <p className="mt-2 text-sm">No ad units yet. Create one from <Link className="link link-primary" to="/adslots">Ad slots</Link>.</p>}
      </section>

      <section className="space-y-3 rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Quick start: embed the publisher loader</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm">
          <li>Create a slot under <Link className="link link-primary" to="/adslots">Ad slots</Link>. Wait until your publisher account is active and the slot is approved and active.</li>
          <li>Host <code>publisher-snippet/src/loader.js</code> on your site or CDN. The backend does not host this file.</li>
          <li>Put a slot element where the ad should appear and use its ad unit ID from the table above.</li>
          <li>Load Socket.IO before the loader. It requests and renders ads and sends impression, click, viewable impression, and report events.</li>
        </ol>
        <pre className="overflow-x-auto rounded bg-base-300 p-4 text-xs"><code>{`<div data-ad-unit-id="YOUR_AD_UNIT_ID"></div>
<script src="https://cdn.socket.io/4.8.1/socket.io.min.js"></script>
<script src="https://your-cdn.example.com/loader.js"
        data-api-key="${publisherKey}"
        data-server="${window.location.origin}"></script>`}</code></pre>
        <p className="text-xs">Replace the sample loader URL and ad unit ID. The key is visible in browser source, so use it only on your registered site and do not reuse or share it elsewhere. Socket.IO requests check the origin against your registered site.</p>
        <p className="text-xs">Advertisers need an approved creative with the exact width and height shown above before it can serve.</p>
      </section>

      <section className="space-y-3 rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Custom integration: Socket.IO</h2>
        <p className="text-sm">Use this if you are building your own integration instead of embedding the loader. Connect to <code>/delivery</code>, emit <code>request_ad</code>, then listen for <code>serve_ad</code> or <code>no_fill</code>.</p>
        <pre className="overflow-x-auto rounded bg-base-300 p-4 text-xs"><code>{`const socket = io("${window.location.origin}/delivery", { transports: ["websocket"] });
socket.emit("request_ad", {
  ad_unit_id: YOUR_AD_UNIT_ID,
  api_key: "${publisherKey}",
  context: { country: "IN", device_type: "mobile", page_keywords: ["travel"] }
});
socket.on("serve_ad", ad => {
  // Render ad.asset_url linked to ad.click_url at ad.width × ad.height.
  const eventData = () => ({ ad_unit_id: YOUR_AD_UNIT_ID, creative_id: ad.creative_id,
    visitor_id: ad.visitor_id, serve_token: ad.serve_token, event_id: crypto.randomUUID() });
  socket.emit("impression", eventData());
  // On click: socket.emit("click", eventData());
});
socket.on("no_fill", ({ reason }) => console.log("No ad", reason));`}</code></pre>
        <p className="text-xs">Use the returned <code>visitor_id</code> and <code>serve_token</code> on impression and click events. Tokens expire after five minutes; use a unique event ID for each event.</p>
      </section>

      <section className="space-y-3 rounded border border-base-300 bg-base-200 p-5">
        <h2 className="text-lg font-semibold">Custom integration: REST</h2>
        <p className="text-sm">Send the key in the <code>X-Publisher-Key</code> header, not in the URL. A match returns an <code>ad</code>; a no-fill returns <code>ad: null</code> and a reason.</p>
        <pre className="overflow-x-auto rounded bg-base-300 p-4 text-xs"><code>{`const response = await fetch("${apiBase}/delivery/ad/YOUR_AD_UNIT_ID?country=IN&device_type=mobile", {
  headers: { "X-Publisher-Key": "${publisherKey}" }
});
const result = await response.json();
if (result.ad) {
  // Render result.ad.asset_url linked to result.ad.click_url.
  // result.ad includes campaign_id, creative_id, width, height, format,
  // visitor_id and serve_token. Send both tracking fields with each event.
} else {
  console.log("No ad available", result.reason);
}`}</code></pre>
        <p className="text-sm">Track impressions and clicks using <code>POST {apiBase}/delivery/events/impression</code> or <code>/delivery/events/click</code> with the publisher-key header and JSON fields <code>ad_unit_id</code>, <code>creative_id</code>, <code>event_id</code>, plus the returned <code>visitor_id</code> and short lived <code>serve_token</code>. Tokens expire after five minutes.</p>
      </section>
    </div>
  </Layout>;
}
