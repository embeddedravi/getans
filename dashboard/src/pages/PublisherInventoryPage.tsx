import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { useListingControls } from "../components/ListingControls";
import { api } from "../lib/api";
import type { AvailablePublisherAdUnit } from "../types";

export function PublisherInventoryPage() {
  const [units, setUnits] = useState<AvailablePublisherAdUnit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listAvailablePublisherAdUnits()
      .then(setUnits)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Could not load publisher inventory"))
      .finally(() => setLoading(false));
  }, []);

  const listing = useListingControls(
    units,
    (unit) => `${unit.publisher_name} ${unit.site_url} ${unit.domain || ""} ${unit.category || ""} ${unit.slot_name} ${unit.description || ""} ${unit.format_type} ${unit.width}x${unit.height}`,
  );

  return (
    <Layout title="Publisher inventory">
      <section className="rounded border border-base-300 bg-base-200">
        <header className="border-b border-base-300 px-4 py-3">
          <h2 className="font-medium">Available publisher ad slots</h2>
          <p className="mt-1 text-xs">Review each slot’s requirements when preparing a campaign creative. Dimensions must match exactly for an ad to serve.</p>
        </header>

        {error && <div role="alert" className="alert alert-error m-4 py-2 text-sm">{error}</div>}
        {loading ? <p className="p-8 text-center text-sm">Loading publisher inventory…</p> : <>
          <div className="p-4">{listing.controls}</div>
          <div className="overflow-x-auto">
            <table className="table table-zebra">
              <thead><tr><th>Publisher / site</th><th>Slot</th><th>Format</th><th>Creative size</th><th>Floor CPM</th></tr></thead>
              <tbody>
                {listing.pageItems.map((unit) => <tr key={unit.id}>
                  <td>
                    <div className="font-medium">{unit.publisher_name}</div>
                    <a className="link link-hover text-xs" href={unit.site_url} target="_blank" rel="noreferrer">{unit.domain || unit.site_url}</a>
                    {unit.category && <div className="mt-1 text-xs">{unit.category}</div>}
                  </td>
                  <td>
                    <div className="font-medium">{unit.slot_name}</div>
                    {unit.description && <div className="mt-1 max-w-xs text-xs">{unit.description}</div>}
                  </td>
                  <td><span className="badge badge-outline badge-sm">{unit.format_type}</span></td>
                  <td className="tabular font-medium">{unit.width} × {unit.height} px</td>
                  <td className="tabular">{Number(unit.reserve_price) > 0 ? `₹${Number(unit.reserve_price).toFixed(4)}` : "—"}</td>
                </tr>)}
                {!listing.filtered.length && <tr><td colSpan={5} className="py-10 text-center">
                  <p className="font-medium">{units.length ? "No slots match your search" : "No available publisher slots yet"}</p>
                  <p className="mt-1 text-sm">{units.length ? "Try a different search." : "Approved, active slots will appear here."}</p>
                </td></tr>}
              </tbody>
            </table>
          </div>
        </>}
      </section>
    </Layout>
  );
}
