(() => {
  const pageSize = 10;

  function setup(container) {
    if (container.dataset.listingReady === "true") return;
    container.dataset.listingReady = "true";
    const isBody = container.tagName === "TBODY";
    let page = 1;
    let query = "";
    let selectedStatus = "all";

    const controls = document.createElement("div");
    controls.className = "mb-3 flex flex-wrap items-center gap-2";
    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Search…";
    search.setAttribute("aria-label", "Search listing");
    search.className = "input input-bordered input-sm w-full max-w-xs";
    const status = document.createElement("select");
    status.setAttribute("aria-label", "Filter listing by status");
    status.className = "select select-bordered select-sm";
    const count = document.createElement("span");
    count.className = "ml-auto text-xs";
    const pager = document.createElement("div");
    pager.className = "join";
    const previous = document.createElement("button");
    previous.type = "button";
    previous.className = "btn btn-sm join-item";
    previous.textContent = "‹";
    previous.setAttribute("aria-label", "Previous page");
    const pageLabel = document.createElement("button");
    pageLabel.type = "button";
    pageLabel.className = "btn btn-sm join-item";
    pageLabel.disabled = true;
    const next = document.createElement("button");
    next.type = "button";
    next.className = "btn btn-sm join-item";
    next.textContent = "›";
    next.setAttribute("aria-label", "Next page");
    pager.append(previous, pageLabel, next);
    controls.append(search, status, count, pager);
    const anchor = isBody
      ? container.closest(".overflow-x-auto") || container.closest("table")
      : container;
    anchor.parentElement.insertBefore(controls, anchor);

    function items() {
      if (isBody) return [...container.children].filter((row) => row.tagName === "TR" && !row.querySelector("td[colspan]"));
      return [...container.querySelectorAll(":scope > [data-listing-item]")];
    }

    function badgeText(row) {
      if (isBody) {
        const headers = [...container.closest("table").querySelectorAll("thead th")];
        const statusIndex = headers.findIndex((header) => /status/i.test(header.textContent));
        const cell = statusIndex >= 0 ? row.cells[statusIndex] : null;
        if (cell) return cell.querySelector(".badge")?.textContent?.trim() || "";
      }
      return row.querySelector(".badge")?.textContent?.trim() || "";
    }

    function render() {
      const rows = items();
      const statuses = [...new Set(rows.map(badgeText).filter(Boolean))].sort();
      const currentStatus = status.value;
      status.replaceChildren(new Option("All statuses", "all"), ...statuses.map((value) => new Option(value, value)));
      status.value = statuses.includes(currentStatus) ? currentStatus : "all";
      selectedStatus = status.value;
      const filtered = rows.filter((row) => {
        const matchesText = row.textContent.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
        const badge = badgeText(row);
        return matchesText && (selectedStatus === "all" || badge === selectedStatus);
      });
      const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
      page = Math.min(page, pages);
      const visible = new Set(filtered.slice((page - 1) * pageSize, page * pageSize));
      rows.forEach((row) => { row.hidden = !visible.has(row); });
      count.textContent = `${filtered.length ? (page - 1) * pageSize + 1 : 0}–${Math.min(page * pageSize, filtered.length)} of ${filtered.length}`;
      pageLabel.textContent = `${page} / ${pages}`;
      previous.disabled = page <= 1;
      next.disabled = page >= pages;
      status.hidden = statuses.length === 0;
    }

    search.addEventListener("input", () => { query = search.value; page = 1; render(); });
    status.addEventListener("change", () => { selectedStatus = status.value; page = 1; render(); });
    previous.addEventListener("click", () => { page -= 1; render(); });
    next.addEventListener("click", () => { page += 1; render(); });
    render();
    if (isBody) new MutationObserver(render).observe(container, { childList: true });
  }

  document.querySelectorAll("table.table tbody[data-listing], [data-listing]:not(tbody)").forEach(setup);
})();
