import { FormEvent, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";

export function PublishersPage() {
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [selected, setSelected] = useState<Publisher | null>(null);
  const [adUnits, setAdUnits] = useState<AdUnit[]>([]);
  const [showCreatePublisher, setShowCreatePublisher] = useState(false);
  const [showCreateAdUnit, setShowCreateAdUnit] = useState(false);

  function refreshPublishers() {
    api.listPublishers().then((data) => setPublishers(data as Publisher[]));
  }

  useEffect(refreshPublishers, []);

  useEffect(() => {
    if (selected) {
      api.listAdUnits(selected.id).then((data) => setAdUnits(data as AdUnit[]));
    } else {
      setAdUnits([]);
    }
  }, [selected]);

  return (
    <Layout title="Publishers & ad slots">
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <div className="border border-base-300 bg-base-200 rounded">
          <div className="flex justify-between items-center px-4 py-3 border-b border-base-300">
            <span className="text-sm font-medium">Publishers</span>
            <button
              className="btn btn-ghost btn-xs"
              onClick={() => setShowCreatePublisher(true)}
            >
              + Add
            </button>
          </div>
          <ul>
            {publishers.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => setSelected(p)}
                  className={`w-full text-left px-4 py-3 text-sm border-b border-base-300 last:border-0 transition-colors ${
                    selected?.id === p.id
                      ? "bg-base-300"
                      : "hover:bg-base-300/50"
                  }`}
                >
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-neutral-content">{p.site_url}</div>
                </button>
              </li>
            ))}
            {publishers.length === 0 && (
              <li className="px-4 py-6 text-sm text-neutral-content text-center">
                No publishers yet.
              </li>
            )}
          </ul>
        </div>

        <div className="border border-base-300 bg-base-200 rounded p-5">
          {!selected ? (
            <p className="text-sm text-neutral-content">
              Select a publisher to view their ad slots and API key.
            </p>
          ) : (
            <>
              <div className="flex justify-between items-start mb-5">
                <div>
                  <h2 className="font-display text-lg font-semibold">{selected.name}</h2>
                  <p className="text-xs text-neutral-content mt-1">
                    API key:{" "}
                    <span className="tabular bg-base-300 px-1.5 py-0.5 rounded">
                      {selected.api_key}
                    </span>
                  </p>
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setShowCreateAdUnit(true)}
                >
                  New ad slot
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr className="text-xs text-neutral-content border-b border-base-300">
                    <th>Slot name</th>
                    <th>Dimensions</th>
                    <th>Ad unit ID</th>
                  </tr>
                </thead>
                <tbody>
                  {adUnits.map((unit) => (
                    <tr key={unit.id} className="border-b border-base-300 last:border-0">
                      <td>{unit.slot_name}</td>
                      <td className="tabular">
                        {unit.width}×{unit.height}
                      </td>
                      <td className="tabular text-neutral-content">{unit.id}</td>
                    </tr>
                  ))}
                  {adUnits.length === 0 && (
                    <tr>
                      <td colSpan={3} className="text-center text-sm text-neutral-content py-6">
                        No ad slots yet for this publisher.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>

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
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createPublisher({ name, site_url: siteUrl });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create publisher");
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-base-200 border border-base-300 rounded p-6 w-full max-w-sm">
        <h2 className="font-display text-lg font-semibold mb-4">Add publisher</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="block text-xs text-neutral-content mb-1">Name</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
          <label className="block">
            <span className="block text-xs text-neutral-content mb-1">Site URL</span>
            <input
              required
              value={siteUrl}
              onChange={(e) => setSiteUrl(e.target.value)}
              className="input input-bordered input-sm w-full bg-base-100"
              placeholder="https://example.com"
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
            <button type="submit" className="btn btn-primary btn-sm">
              Add publisher
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
  const [width, setWidth] = useState("300");
  const [height, setHeight] = useState("250");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createAdUnit(publisherId, {
        publisher_id: publisherId,
        slot_name: slotName,
        width: Number(width),
        height: Number(height),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create ad slot");
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-base-200 border border-base-300 rounded p-6 w-full max-w-sm">
        <h2 className="font-display text-lg font-semibold mb-4">New ad slot</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="block text-xs text-neutral-content mb-1">Slot name</span>
            <input
              required
              value={slotName}
              onChange={(e) => setSlotName(e.target.value)}
              placeholder="sidebar-300x250"
              className="input input-bordered input-sm w-full bg-base-100"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="block text-xs text-neutral-content mb-1">Width</span>
              <input
                type="number"
                value={width}
                onChange={(e) => setWidth(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
              />
            </label>
            <label className="block">
              <span className="block text-xs text-neutral-content mb-1">Height</span>
              <input
                type="number"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                className="input input-bordered input-sm w-full bg-base-100"
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
            <button type="submit" className="btn btn-primary btn-sm">
              Create slot
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
