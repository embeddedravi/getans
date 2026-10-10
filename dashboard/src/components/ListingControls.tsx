import { useEffect, useMemo, useState } from "react";

export type ListingFilter = { value: string; label: string };

export function useListingControls<T>(
  items: T[],
  searchText: (item: T) => string,
  filterValue?: (item: T) => string,
  filters: ListingFilter[] = [],
  pageSize = 10,
) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => items.filter((item) => {
    const matchesQuery = searchText(item).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
    return matchesQuery && (filter === "all" || !filterValue || filterValue(item) === filter);
  }), [items, searchText, filterValue, filter, query]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  useEffect(() => setPage((current) => Math.min(current, pageCount)), [pageCount]);
  useEffect(() => setPage(1), [query, filter]);
  const pageItems = filtered.slice((page - 1) * pageSize, page * pageSize);
  const controls = <div className="mb-3 flex flex-wrap items-center gap-2" aria-label="List controls">
    <input className="input input-bordered input-sm w-full max-w-xs" type="search" placeholder="Search…" aria-label="Search listing" value={query} onChange={(event) => setQuery(event.target.value)} />
    {filters.length > 0 && <select className="select select-bordered select-sm" aria-label="Filter listing" value={filter} onChange={(event) => setFilter(event.target.value)}>
      <option value="all">All statuses</option>{filters.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
    </select>}
    <span className="ml-auto text-xs">{filtered.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, filtered.length)} of {filtered.length}</span>
    <div className="join">
      <button className="btn btn-sm join-item" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>‹</button>
      <button className="btn btn-sm join-item" aria-label="Page number" disabled>{page} / {pageCount}</button>
      <button className="btn btn-sm join-item" aria-label="Next page" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>›</button>
    </div>
  </div>;
  return { pageItems, filtered, controls };
}
