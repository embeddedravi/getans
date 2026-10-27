import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdFormatType, AdUnit, Publisher } from "../types";
import { useListingControls } from "../components/ListingControls";

const AD_FORMATS: AdFormatType[] = ["display", "banner", "native", "video", "interstitial", "poll"];

export function PublishersPage({ view = "sites" }: { view?: "sites" | "adslots" }) {
  const [searchParams] = useSearchParams();
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [selected, setSelected] = useState<Publisher | null>(null);
  const [adUnits, setAdUnits] = useState<AdUnit[]>([]);
  const [showCreatePublisher, setShowCreatePublisher] = useState(false);
  const [showCreateAdUnit, setShowCreateAdUnit] = useState(false);
  const publisherListing = useListingControls(publishers, (publisher) => `${publisher.name} ${publisher.site_url} ${publisher.status} ${publisher.domain || ""} ${publisher.category || ""}`,
    (publisher) => publisher.status, ["pending_approval", "active", "suspended", "rejected"].map((value) => ({ value, label: value.replace(/_/g, " ") })));
  const adUnitListing = useListingControls(adUnits, (unit) => `${unit.slot_name} ${unit.format_type} ${unit.status}`,
    (unit) => unit.status, ["pending_review", "approved", "rejected"].map((value) => ({ value, label: value.replace(/_/g, " ") })));

  function refreshPublishers() {
    api.listPublishers().then((data) => {
      setPublishers(data as Publisher[]);
    });
  }

  useEffect(() => {
    refreshPublishers();
  }, []);

  useEffect(() => {
    if (view !== "adslots" || !publishers.length) return;
    const requestedId = Number(searchParams.get("site") || searchParams.get("selected"));
    const requestedPublisher = requestedId ? publishers.find((publisher) => publisher.id === requestedId) : null;
    setSelected((current) => requestedPublisher || current && publishers.find((publisher) => publisher.id === current.id) || publishers[0] || null);
  }, [view, publishers, searchParams]);

  useEffect(() => {
    if (selected && view === "adslots") {
      api.listAdUnits(selected.id).then((data) => setAdUnits(data as AdUnit[])).catch(() => setAdUnits([]));
    } else {
      setAdUnits([]);
    }
  }, [selected, view]);

  return (
    <Layout title={view === "sites" ? "My sites" : "Ad slots"}>
      {view === "sites" ? (
        <section className="rounded border border-base-300 bg-base-200">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 px-4 py-3">
            <div><h2 className="font-medium">My sites</h2><p className="mt-0.5 text-xs">{publishers.length} {publishers.length === 1 ? "site" : "sites"}</p></div>
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreatePublisher(true)}>Add site</button>
          </header>
          <div className="p-4">{publisherListing.controls}</div>
          <div className="overflow-x-auto">
            <table className="table table-zebra">
              <thead><tr><th>Site</th><th>Website</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {publisherListing.pageItems.map((publisher) => <tr key={publisher.id}>
                  <td className="font-medium">{publisher.name}</td>
                  <td><a className="link link-hover" href={publisher.site_url} target="_blank" rel="noreferrer">{publisher.site_url}</a></td>
                  <td><span className={`badge badge-sm ${publisher.status === "active" ? "badge-success" : publisher.status === "rejected" ? "badge-error" : publisher.status === "suspended" ? "badge-ghost" : "badge-warning"}`}>{publisher.status.replace("_", " ")}</span></td>
                  <td><Link className="link link-primary link-hover" to={`/adslots?site=${publisher.id}`}>Ad slots</Link></td>
                </tr>)}
                {!publisherListing.filtered.length && <tr><td colSpan={4} className="py-10 text-center"><p className="font-medium">{publishers.length ? "No sites match these filters" : "No sites added yet"}</p><p className="mt-1 text-sm">{publishers.length ? "Try a different search or status." : "Add a site to get started."}</p>{!publishers.length && <button className="btn btn-primary btn-xs mt-3" onClick={() => setShowCreatePublisher(true)}>Add site</button>}</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="rounded border border-base-300 bg-base-200">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 px-4 py-3">
            <label className="flex items-center gap-3 text-sm font-medium">Site
              <select aria-label="Select site for ad slots" className="select select-bordered select-sm max-w-xs" value={selected?.id ?? ""} onChange={(event) => setSelected(publishers.find((publisher) => publisher.id === Number(event.target.value)) || null)}>
                {publishers.map((publisher) => <option key={publisher.id} value={publisher.id}>{publisher.name}</option>)}
              </select>
            </label>
            <button className="btn btn-primary btn-sm" disabled={!selected} onClick={() => setShowCreateAdUnit(true)}>Add ad slot</button>
          </header>
          {selected ? <>
            <div className="p-4">{adUnitListing.controls}</div>
            <div className="overflow-x-auto">
              <table className="table table-zebra">
                <thead><tr><th>Slot name</th><th>Format</th><th>Dimensions</th><th>Reserve</th><th>Status</th><th>Ad unit ID</th></tr></thead>
                <tbody>
                  {adUnitListing.pageItems.map((unit) => <tr key={unit.id}>
                    <td className="font-medium">{unit.slot_name}</td><td><span className="badge badge-outline badge-sm">{unit.format_type}</span></td><td className="tabular">{unit.width} × {unit.height} px</td>
                    <td className="tabular">{Number(unit.reserve_price) > 0 ? `₹${Number(unit.reserve_price).toFixed(4)}` : "—"}</td>
                    <td><span className={`badge badge-xs ${unit.status === "approved" ? "badge-success" : unit.status === "rejected" ? "badge-error" : "badge-warning"}`}>{unit.status.replace("_", " ")}</span></td><td className="tabular">#{unit.id}</td>
                  </tr>)}
                  {!adUnitListing.filtered.length && <tr><td colSpan={6} className="py-10 text-center"><p className="font-medium">{adUnits.length ? "No slots match these filters" : "No ad slots yet"}</p><p className="mt-1 text-sm">{adUnits.length ? "Try a different search or status." : "Add an ad slot to get started."}</p>{!adUnits.length && <button className="btn btn-primary btn-xs mt-3" onClick={() => setShowCreateAdUnit(true)}>Add ad slot</button>}</td></tr>}
                </tbody>
              </table>
            </div>
          </> : <p className="p-10 text-center text-sm">{publishers.length ? "Select a site to see its ad slots." : "Add a site before creating ad slots."}</p>}
        </section>
      )}

      {showCreatePublisher && (
        <CreatePublisherModal
          onClose={() => setShowCreatePublisher(false)}
          onCreated={() => {
            setShowCreatePublisher(false);
            refreshPublishers();
          }}
        />
      )}

      {showCreateAdUnit && selected && (
        <CreateAdUnitModal
          publisherId={selected.id}
          onClose={() => setShowCreateAdUnit(false)}
          onCreated={() => {
            setShowCreateAdUnit(false);
            api.listAdUnits(selected.id).then((data) => setAdUnits(data as AdUnit[]));
          }}
        />
      )}
    </Layout>
  );
}

function CreatePublisherModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [siteUrl, setSiteUrl] = useState("");
  const [payoutEmail, setPayoutEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!window.confirm(`Create publisher “${name}”?`)) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.createPublisher({
        name,
        site_url: siteUrl,
        payout_email: payoutEmail,
        domain: domain || null,
        category: category || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create publisher");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 p-3 sm:p-4">
      <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded border border-base-300 bg-base-200 p-4 sm:p-6">
        <h2 className="font-display text-lg font-semibold mb-4">Add publisher</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="block text-xs  mb-1">Name</span>
            <input
              required
              minLength={2}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
          <label className="block">
            <span className="block text-xs  mb-1">Site URL</span>
            <input
              required
              type="url"
              value={siteUrl}
              onChange={(e) => setSiteUrl(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
              placeholder="https://example.com"
            />
          </label>
          <label className="block">
            <span className="block text-xs  mb-1">Payout email</span>
            <input
              required
              type="email"
              value={payoutEmail}
              onChange={(e) => setPayoutEmail(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
              placeholder="payouts@publisher.example"
            />
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="block text-xs  mb-1">Domain (optional)</span>
              <input
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
                placeholder="example.com"
              />
            </label>
            <label className="block">
              <span className="block text-xs  mb-1">Category (optional)</span>
              <input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
                placeholder="News"
              />
            </label>
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
              {submitting ? "Adding..." : "Add publisher"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CreateAdUnitModal({
  publisherId,
  onClose,
  onCreated,
}: {
  publisherId: number;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [slotName, setSlotName] = useState("");
  const [formatType, setFormatType] = useState<AdFormatType>("display");
  const [width, setWidth] = useState("300");
  const [height, setHeight] = useState("250");
  const [reservePrice, setReservePrice] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!window.confirm(`Create ad slot “${slotName}”?`)) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.createAdUnit(publisherId, {
        publisher_id: publisherId,
        slot_name: slotName,
        format_type: formatType,
        width: Number(width),
        height: Number(height),
        reserve_price: Number(reservePrice) || 0,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create ad slot");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 p-3 sm:p-4">
      <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded border border-base-300 bg-base-200 p-4 sm:p-6">
        <h2 className="font-display text-lg font-semibold mb-4">New ad slot</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="block text-xs  mb-1">Slot name</span>
            <input
              required
              value={slotName}
              onChange={(e) => setSlotName(e.target.value)}
              placeholder="sidebar-300x250"
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
          <label className="block">
            <span className="block text-xs  mb-1">Format</span>
            <select
              value={formatType}
              onChange={(e) => setFormatType(e.target.value as AdFormatType)}
              className="select select-bordered select-sm w-full bg-base-100"
            >
              {AD_FORMATS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="block text-xs  mb-1">Width</span>
              <input
                type="number"
                min={1}
                value={width}
                onChange={(e) => setWidth(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </label>
            <label className="block">
              <span className="block text-xs  mb-1">Height</span>
              <input
                type="number"
                min={1}
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="block text-xs  mb-1">
              Reserve price (CPM floor, ₹, optional)
            </span>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={reservePrice}
              onChange={(e) => setReservePrice(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
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
              {submitting ? "Creating..." : "Create slot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
